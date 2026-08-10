"""Context-bound service objects. Every ACTION_SPEC service_path lands here or
on an existing domain module. No Gradio import is allowed in this file.
"""
from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from . import checkpoint_manager, database as db, drive_quota
from .config import (
    CONCURRENCY_LEVELS,
    HARD_CONCURRENCY_CAP,
    LOG_PATH,
    LOGS_DIR,
    SUPPORTED_LANGUAGES,
    TEMP_DIR,
)
from .errors import (
    DriveNotReadyError,
    LocalDiskError,
    NothingSelectedError,
    QuotaRefusedError,
    TeleDriveError,
    TelegramNotReadyError,
)
from .filters import FilterSet, apply as apply_filterset
from .i18n import t, toggle as toggle_lang, set_language
from .logging_config import get_logger, tail as tail_log
from .media_scanner import DEFAULT_SCAN_MODE
from .media_scanner import MAX_SCAN_MESSAGES as SCANNER_MAX_SCAN_MESSAGES  # canonical bound
from .media_scanner import MEDIA_TYPES as SCANNER_MEDIA_TYPES
from .media_scanner import SCAN_MODES as SCANNER_SCAN_MODES
from .media_scanner import ScanRequest, fields_for_mode, scan_link
from .models import MediaItem
from .redaction import redact
from .telegram_links import InvalidLink, parse as parse_link
from .utils import human_bytes, human_duration, now_iso, safe_disk_free

_log = get_logger("teledrive.services")

MAX_SCAN_MESSAGES = SCANNER_MAX_SCAN_MESSAGES
# re-export for handlers/tests that import from services
SCAN_MODES = SCANNER_SCAN_MODES
MEDIA_TYPES = SCANNER_MEDIA_TYPES

# Every message ScanRequest.validate() can raise maps to a translated key.
# The fallback err.bad_scan_request must never silently become err.unknown.
SCAN_VALIDATION_KEYS: dict[str, str] = {
    "unsupported scan mode": "err.bad_scan_mode",
    "unsupported media type": "err.scan_media_type",
    "message mode requires a positive message id": "err.scan_message_id",
    "range mode requires start and end ids": "err.scan_range_ids",
    "invalid message range": "err.scan_range_invalid",
    "message range is too large": "err.scan_range_too_large",
    "latest mode requires a positive limit": "err.scan_limit",
}

# Link kinds that are never a scan source (parsed successfully but refused).
NON_SCANNABLE_LINK_KINDS: dict[str, str] = {
    "invite": "err.link_invite_unsupported",
}


# --------------------------------------------------------------------------
# Scanning + selection
# --------------------------------------------------------------------------

@dataclass
class ScanResult:
    total: int = 0
    total_bytes: int = 0
    scope: str = ""
    rows: list[list[Any]] = field(default_factory=list)


class SelectionService:
    """Owns analyze candidates, the active filter set, and the selection.

    Selection is a pure in-memory stage: nothing here downloads, enqueues, or
    touches Telegram/Drive. ``enqueue_selected`` is the ONLY method that moves
    candidates into the queue, and it validates the target folder, the local
    disk reserve and (when Drive is connected) the Drive quota first
    (DOC-39 §5.3).
    """

    def __init__(self, ctx) -> None:
        self.ctx = ctx
        self._lock = threading.RLock()
        self.candidates: list[MediaItem] = []
        self.filters = FilterSet()
        self.selected_ids: set[str] = set()

    # -- population --
    def set_candidates(self, items: Iterable[MediaItem]) -> list[MediaItem]:
        with self._lock:
            self.candidates = list(items)
            self.selected_ids = set()
            return self.candidates

    # -- filters --
    def apply_filters(
        self,
        media_types: Iterable[str] | None = None,
        extensions: str = "",
        min_size_mb: float | None = None,
        max_size_mb: float | None = None,
        date_from: str = "",
        date_to: str = "",
        include: str = "",
        exclude: str = "",
    ) -> list[MediaItem]:
        def _split(value: str) -> list[str]:
            return [p.strip() for p in str(value or "").replace(";", ",").split(",") if p.strip()]

        with self._lock:
            self.filters = FilterSet(
                media_types=set(media_types or []),
                extensions={e.lower().lstrip(".") for e in _split(extensions)},
                min_size=int(min_size_mb * 1024 * 1024) if min_size_mb else None,
                max_size=int(max_size_mb * 1024 * 1024) if max_size_mb else None,
                date_from=date_from or None,
                date_to=date_to or None,
                include_substr=_split(include),
                exclude_substr=_split(exclude),
            )
            visible = self.visible()
            self.selected_ids &= {i.id for i in visible}
            return visible

    def visible(self) -> list[MediaItem]:
        return apply_filterset(self.candidates, self.filters)

    # -- selection --
    def select_all_visible(self) -> list[str]:
        with self._lock:
            self.selected_ids = {i.id for i in self.visible()}
            return sorted(self.selected_ids)

    def clear(self) -> list[str]:
        with self._lock:
            self.selected_ids = set()
            return []

    def toggle(self, item_id: str) -> bool:
        with self._lock:
            if item_id in self.selected_ids:
                self.selected_ids.discard(item_id)
                return False
            self.selected_ids.add(item_id)
            return True

    def toggle_by_index(self, row_index: int) -> bool:
        """Toggle the candidate shown at ``row_index`` of the visible table.

        Manual row selection is row-based, never filename-based: the index
        maps onto the live ``visible()`` order, so the same row toggles the
        same candidate regardless of name collisions or re-analysis.
        """
        try:
            item = self.visible()[int(row_index)]
        except (IndexError, TypeError, ValueError):
            raise TeleDriveError("unknown candidate row", "err.bad_scan_request")
        return self.toggle(item.id)

    def select_range(self, start_id, end_id) -> list[str]:
        """Select every visible candidate whose message id lies in [start, end].

        The range REPLACES the current selection (predictable from/to
        semantics). Refusals are translated and happen before any side effect:
        non-numeric ids, non-positive ids, end < start, and ranges beyond the
        declared cap (``MAX_RANGE_MESSAGES``) are all rejected locally.
        """
        try:
            start, end = int(start_id), int(end_id)
        except (TypeError, ValueError):
            raise TeleDriveError("range needs numeric ids", "err.selection_range_invalid")
        if start <= 0 or end <= 0:
            raise TeleDriveError("range needs positive ids", "err.selection_range_invalid")
        if end < start:
            raise TeleDriveError("range end precedes start", "err.selection_range_invalid")
        from .media_scanner import MAX_RANGE_MESSAGES
        if (end - start + 1) > MAX_RANGE_MESSAGES:
            raise TeleDriveError("range too large", "err.selection_range_too_large")
        with self._lock:
            picked = {
                i.id for i in self.visible()
                if start <= int(i.message_id or 0) <= end
            }
            self.selected_ids = picked
            return sorted(picked)

    def select_group_by_chat(self, chat_id) -> list[str]:
        """Select every visible candidate from one chat/group (replace mode).

        The candidates table exposes a real grouping column (chat title); the
        dropdown value is ``<chat_id>`` so this never depends on file names.
        Album-level (``grouped_id``) grouping needs a scanner contract change
        and is out of scope — chat grouping is the grouping the source
        supports today (DOC-39 §5.1 "عند دعم المصدر لذلك").
        """
        try:
            chat = int(chat_id)
        except (TypeError, ValueError):
            raise TeleDriveError("invalid group", "err.bad_scan_request")
        with self._lock:
            picked = {
                i.id for i in self.visible()
                if int(getattr(i, "chat_id", 0) or 0) == chat
            }
            self.selected_ids = picked
            return sorted(picked)

    def groups(self) -> list[tuple[str, str]]:
        """(label, chat_id) pairs derived from the visible candidates only."""
        seen: dict[int, str] = {}
        for item in self.visible():
            if item.chat_id not in seen:
                seen[item.chat_id] = item.chat_title or f"chat {item.chat_id}"
        return [(seen[cid], str(cid)) for cid in seen]

    def summary(self) -> dict[str, Any]:
        """Live count + total bytes of the current selection (never fake)."""
        items = self.selected_items()
        return {
            "count": len(items),
            "total_bytes": sum(int(i.size_bytes or 0) for i in items),
        }

    def selected_items(self) -> list[MediaItem]:
        chosen = {i.id: i for i in self.visible()}
        return [chosen[i] for i in self.selected_ids if i in chosen]

    def enqueue_selected(self) -> list[MediaItem]:
        """Enqueue ONLY the explicit selection, after the DOC-39 §5.3 gates.

        Refusals, in order, each with a translated key:
          * empty selection            -> NothingSelectedError (err.nothing_selected)
          * no valid target folder ID  -> err.no_folder
          * local disk reserve         -> LocalDiskError     (err.disk_full)
          * Drive quota (if connected) -> QuotaRefusedError  (err.drive_full)

        Nothing here starts a transfer and nothing touches Telegram; the queue
        is a local SQLite row until the user presses Start in Transfers.
        """
        items = self.selected_items()
        if not items:
            raise NothingSelectedError("no items selected")
        ctx = self.ctx
        # Target folder must exist and be persisted by ID (root only counts
        # when the node explicitly selected it — require_selected() reads the
        # persisted ID, so an unselected root never passes silently).
        folder = ctx.drive_folders.require_selected()
        total = sum(int(i.size_bytes or 0) for i in items)
        largest = max([int(i.size_bytes or 0) for i in items] or [0])
        from .storage_manager import preflight as storage_preflight
        ok_disk, free = storage_preflight(largest)
        if not ok_disk:
            raise LocalDiskError(f"local disk reserve: free={free} need={largest}")
        drive_auth = ctx.drive_auth
        if drive_auth is not None and drive_auth.connected and ctx.drive_client is not None:
            from .drive_quota import preflight_or_raise
            try:
                preflight_or_raise(ctx.drive_client, total)
            except RuntimeError as exc:
                raise QuotaRefusedError(str(exc)) from exc
        enqueued = ctx.queue_manager.bulk_enqueue(items)
        db.add_event("", "queue", "enqueued", {
            "count": len(enqueued),
            "folder_id": folder.id,
            "total_bytes": total,
        })
        return enqueued


class ScannerService:
    """Runs a scoped scan on the shared loop and hands results to selection."""

    def __init__(self, ctx) -> None:
        self.ctx = ctx

    def analyze(
        self,
        link: str,
        mode: str = DEFAULT_SCAN_MODE,
        message_id: int | None = None,
        start_id: int | None = None,
        end_id: int | None = None,
        limit: int = MAX_SCAN_MESSAGES,
        media_types: Iterable[str] | None = None,
        *args,
        **kwargs,
    ) -> ScanResult:
        # Backward-compat: callers may pass `scope` as positional second arg or kwarg.
        # Spec calls it `mode`, but old tests use "auto". Map auto->chat.
        if "scope" in kwargs and (not mode or mode in ("chat", DEFAULT_SCAN_MODE)):
            # If caller supplied scope kwarg, prefer it.
            mode = kwargs.pop("scope", mode)
        # Also support legacy positional where second arg was scope string "auto"
        # and limit passed as third positional (rare) – handled via args if needed.
        # For simplicity, if extra positional args were supplied, map them.
        if args:
            # legacy: analyze(link, scope, limit)
            if len(args) >= 1 and mode == "chat" and isinstance(args[0], str):
                # already have mode; ignore
                pass
            elif len(args) >= 1:
                # if first extra arg looks like legacy limit, capture it
                try:
                    limit = int(args[0])
                except Exception:
                    pass
        telegram_auth = self.ctx.telegram_auth
        if telegram_auth is None or not telegram_auth.authorized:
            raise TelegramNotReadyError("telegram is not authorized")
        try:
            parsed = parse_link((link or "").strip())
        except InvalidLink as exc:
            raise TeleDriveError(str(exc), "err.bad_link") from exc
        refusal_key = NON_SCANNABLE_LINK_KINDS.get(parsed.kind)
        if refusal_key is not None:
            raise TeleDriveError(
                f"link kind {parsed.kind} is not scannable", refusal_key
            )
        requested_mode = str(mode or DEFAULT_SCAN_MODE).strip().lower()
        # Legacy alias: "auto" means whole chat scan (same as "chat")
        if requested_mode == "auto":
            requested_mode = "chat"
        if requested_mode == "message" and parsed.message_id is not None and message_id is None:
            message_id = parsed.message_id
        try:
            request = ScanRequest(
                mode=requested_mode,
                message_id=message_id,
                start_id=start_id,
                end_id=end_id,
                limit=limit,
                media_types=frozenset(media_types or {"all"}),
            ).validate()
        except ValueError as exc:
            reason = str(exc)
            raise TeleDriveError(
                reason, SCAN_VALIDATION_KEYS.get(reason, "err.bad_scan_request")
            ) from exc
        items = self.ctx.aio.run(
            scan_link(telegram_auth.client, parsed, request)
        )
        self.ctx.selection.set_candidates(items)
        db.add_event("", "scan", "analyzed", {
            "count": len(items),
            "mode": request.mode,
            "media_types": sorted(request.media_types),
            "bounded": True,
        })
        return ScanResult(
            total=len(items),
            total_bytes=sum(item.size_bytes for item in items),
            scope=request.mode,
            rows=rows_for(items),
        )

    def mode_fields(self, mode: str = DEFAULT_SCAN_MODE) -> dict[str, bool]:
        """Which scan inputs the chosen mode uses. Read-only, no Telegram call."""
        try:
            return fields_for_mode(mode)
        except ValueError as exc:
            raise TeleDriveError(str(exc), "err.bad_scan_mode") from exc

    # Backward-compat alias: older callers (and some tests) still use scope/limit names.
    # Keep it delegated to the new analyze to avoid duplication.
    def analyze_legacy(self, link: str, scope: str = "auto", limit: int = MAX_SCAN_MESSAGES) -> ScanResult:  # pragma: no cover
        # Map legacy scope values to new modes: auto -> chat, message -> message, chat -> chat
        mode_map = {"auto": "chat", "message": "message", "chat": "chat"}
        mode = mode_map.get(str(scope).strip().lower(), "chat")
        return self.analyze(link, mode=mode, limit=limit)


def rows_for(items: Iterable[MediaItem]) -> list[list[Any]]:
    return [
        [
            item.id,
            item.safe_name,
            item.media_type,
            human_bytes(item.size_bytes),
            t(f"state.{item.state}"),
            f"{max(item.download_pct, item.upload_pct):.0f}%",
            item.attempts,
        ]
        for item in items
    ]


def candidate_rows_for(
    items: Iterable[MediaItem], selected_ids: Iterable[str] | None = None
) -> list[list[Any]]:
    """DOC-39 §5.2 candidate rows: select marker is part of the table value.

    Column order: تحديد · معرّف الرسالة · اسم الملف · النوع · الحجم ·
    المجموعة · التاريخ · الحالة. The marker cell (☑/☐) is derived from the
    live selection state, and row clicks toggle it through the service — it is
    state, not a decorative button.
    """
    selected = set(selected_ids or ())
    return [
        [
            "☑" if item.id in selected else "☐",
            item.message_id,
            item.safe_name,
            item.media_type,
            human_bytes(item.size_bytes),
            item.chat_title or "—",
            str(item.message_date or ""),
            t(f"state.{item.state}"),
        ]
        for item in items
    ]


# --------------------------------------------------------------------------
# Drive quota
# --------------------------------------------------------------------------

class DriveQuotaService:
    def __init__(self, ctx) -> None:
        self.ctx = ctx
        self.last: dict[str, Any] = {}

    def refresh(self) -> dict[str, Any]:
        drive_auth = self.ctx.drive_auth
        if drive_auth is None or not drive_auth.connected:
            raise DriveNotReadyError("drive is not connected")
        quota = drive_auth.storage_quota()
        report = drive_quota.evaluate(quota, 0)
        self.last = {
            "limit": quota.get("limit", 0),
            "usage": quota.get("usage", 0),
            "free": report.free,
            "ratio_used": report.ratio_used,
            "warn": report.warn,
            "label": f"{human_bytes(quota.get('usage', 0))} / {human_bytes(quota.get('limit', 0))}",
        }
        return self.last

    def preflight(self, required_bytes: int):
        quota = self.refresh()
        return drive_quota.evaluate(
            {"limit": quota["limit"], "usage": quota["usage"]}, int(required_bytes)
        )


# --------------------------------------------------------------------------
# Dashboard stats
# --------------------------------------------------------------------------

class StatsService:
    def __init__(self, ctx) -> None:
        self.ctx = ctx

    def dashboard(self) -> dict[str, Any]:
        ctx = self.ctx
        snap = ctx.progress.snapshot()
        drive_label = "—"
        if ctx.drive_auth is not None and ctx.drive_auth.connected:
            drive_label = ctx.drive_quota.last.get("label") or "—"
        current = ""
        if snap["active"]:
            active = snap["active"][0]
            pct = max(active["pct_download"], active["pct_upload"])
            current = f"{active['name']} — {active['phase']} {pct:.0f}%"
        total_bytes = snap["total_bytes"] or 0
        overall = (snap["done_bytes"] / total_bytes * 100) if total_bytes else 0.0
        telegram_ready = ctx.telegram_auth is not None and ctx.telegram_auth.authorized
        drive_ready = ctx.drive_auth is not None and ctx.drive_auth.connected
        return {
            t("dash.current"): current,
            t("dash.done"): snap["done_files"],
            t("dash.failed"): snap["failed_files"],
            t("dash.remaining"): max(
                0, snap["total_files"] - snap["done_files"] - snap["failed_files"]
            ),
            t("dash.speed"): human_bytes(snap["instant_speed"]) + "/s",
            t("dash.avg_speed"): human_bytes(snap["average_speed"]) + "/s",
            t("dash.eta"): human_duration(snap["eta_seconds"]),
            t("dash.overall_pct"): f"{overall:.1f}%",
            t("dash.telegram_status"): t("status.connected") if telegram_ready else t("status.disconnected"),
            t("dash.drive_status"): t("status.connected") if drive_ready else t("status.disconnected"),
            t("dash.drive_space"): drive_label,
            t("dash.colab_space"): human_bytes(safe_disk_free(TEMP_DIR)),
            t("dash.queue_status"): ctx.queue_manager.status_label(),
        }


# --------------------------------------------------------------------------
# Logs
# --------------------------------------------------------------------------

class LogService:
    """Tail/search/export redacted logs from disk.

    A level filter is a plain string: ALL/INFO/WARNING/ERROR/RECOVERY. We match
    the bracketed [LEVEL] token emitted by the ``logging`` formatter so filter
    behavior is independent of Python logger-inheritance edge cases.
    """

    LEVELS: tuple[str, ...] = ("ALL", "INFO", "WARNING", "ERROR", "RECOVERY")
    _LEVEL_TOKENS: dict[str, tuple[str, ...]] = {
        "ALL": (),
        "INFO": ("INFO",),
        "WARNING": ("WARNING",),
        "ERROR": ("ERROR", "CRITICAL"),
        "RECOVERY": ("RECOVERY",),
    }

    def __init__(self, ctx) -> None:
        self.ctx = ctx

    # ---------- read ----------
    def tail(self, lines: int = 300, level: str = "ALL") -> str:
        return self._filter(redact(tail_log(lines=int(lines or 300))), level)

    def search(self, query: str, lines: int = 2000, level: str = "ALL") -> str:
        text = redact(tail_log(lines=int(lines or 2000)))
        needle = (query or "").strip().lower()
        out = []
        for line in text.splitlines():
            if needle and needle not in line.lower():
                continue
            out.append(line)
        return self._filter("\n".join(out), level)

    # ---------- export ----------
    def export_file(self, level: str = "ALL") -> str:
        """Write a redacted, optionally level-filtered export to LOGS_DIR."""
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        content = self._filter(redact(tail_log(lines=50000)), level)
        target = LOGS_DIR / f"teledrive_logs_{level.lower()}.txt"
        target.write_text(content, encoding="utf-8")
        return str(target)

    # ---------- internal ----------
    def _filter(self, text: str, level: str) -> str:
        key = (level or "ALL").upper()
        tokens = self._LEVEL_TOKENS.get(key, ())
        if not tokens:
            return text
        out: list[str] = []
        for line in text.splitlines():
            # lines without a [LEVEL] tag are kept as context
            if "[" not in line:
                out.append(line)
                continue
            if any(f"[{tok}]" in line for tok in tokens):
                out.append(line)
        return "\n".join(out)


# --------------------------------------------------------------------------
# Settings + preferences
# --------------------------------------------------------------------------

class SettingsService:
    """Concurrency 1..4 (default 2) per the constitution — never 19 or 50."""

    MIN = 1
    MAX = HARD_CONCURRENCY_CAP  # 4
    DEFAULT = 2

    def __init__(self, ctx) -> None:
        self.ctx = ctx
        # Restore persisted value (if valid) on boot.
        saved = db.get_setting("concurrency")
        if saved is not None:
            try:
                self._apply(int(saved))
            except (TypeError, ValueError, TeleDriveError):
                pass

    def _apply(self, n: int) -> int:
        n = int(n)
        if n < self.MIN or n > self.MAX:
            raise TeleDriveError(
                f"concurrency out of range [{self.MIN},{self.MAX}]",
                "settings.concurrency.out_of_range",
            )
        self.ctx.config.manual_concurrency = n
        self.ctx.config.concurrency = "manual"
        value = self.ctx.config.concurrency_value()
        self.ctx.queue_manager.apply_concurrency(value)
        return value

    def set_concurrency(self, level: str | int) -> dict[str, Any]:
        # Accept numeric slider values (1..4) or named levels mapped into range.
        try:
            n = int(level)
        except (TypeError, ValueError):
            sval = str(level or "").strip().lower()
            if sval in CONCURRENCY_LEVELS:
                n = CONCURRENCY_LEVELS[sval]
            else:
                raise TeleDriveError(
                    "invalid concurrency value", "settings.concurrency.invalid"
                )
        value = self._apply(n)
        db.set_setting("concurrency", str(n))
        return {"level": n, "workers": value, "cap": self.MAX}

    def current(self) -> int:
        return self.ctx.config.concurrency_value()


class PreferencesService:
    def __init__(self, ctx) -> None:
        self.ctx = ctx
        # Restore persisted theme/language on boot (best-effort).
        saved_theme = db.get_setting("theme") or "dark"
        self.ctx.ui_state.extra["theme"] = (
            saved_theme if saved_theme in ("dark", "light") else "dark"
        )
        saved_lang = db.get_setting("language")
        if saved_lang in SUPPORTED_LANGUAGES:
            set_language(saved_lang)
            self.ctx.ui_state.language = saved_lang

    def toggle_language(self) -> str:
        language = toggle_lang()
        self.ctx.ui_state.language = language
        db.set_setting("language", language)
        return language

    def set_language(self, language: str) -> str:
        if language not in SUPPORTED_LANGUAGES:
            raise TeleDriveError("unsupported language", "err.bad_language")
        set_language(language)
        self.ctx.ui_state.language = language
        db.set_setting("language", language)
        return language

    def set_theme(self, theme: str) -> str:
        theme = theme if str(theme).lower() in ("dark", "light") else "dark"
        self.ctx.ui_state.extra["theme"] = theme
        db.set_setting("theme", theme)
        return theme

    def current_theme(self) -> str:
        return self.ctx.ui_state.extra.get("theme", "dark")


# --------------------------------------------------------------------------
# Checkpoints / recovery
# --------------------------------------------------------------------------

class CheckpointService:
    def __init__(self, ctx) -> None:
        self.ctx = ctx

    def _drive(self):
        drive_auth = self.ctx.drive_auth
        if drive_auth is None or not drive_auth.connected:
            return None
        return self.ctx.ensure_drive_client()

    def persist(self) -> dict[str, Any]:
        path = checkpoint_manager.persist_local()
        file_id = None
        drive = self._drive()
        if drive is not None:
            try:
                file_id = checkpoint_manager.persist_durable(drive)
            except Exception as exc:
                _log.warning("durable checkpoint failed, kept local: %s", exc)
        return {"local": str(path), "drive_file_id": file_id, "at": now_iso()}

    def restore_and_reconcile(self, allow_local: bool = True) -> dict[str, Any]:
        """Restore newest checkpoint and reconcile.

        No blind deletion: the local SQLite state is only appended to (duplicate
        ids are skipped), and reconcile_with_drive transitions items through
        the QueueManager (never overwrites rows).

        When no Drive is connected:
          * if ``allow_local`` is True (the recovery UI action), the newest
            *validated* local checkpoint is restored without reconcile;
          * if ``allow_local`` is False (the lazy-client regression test path
            that asserts the disconnected code path never constructs a Drive
            client), :class:`DriveNotReadyError` is raised so the UI can ask
            the user to connect Drive first.
        """
        from .checkpoint_manager import InvalidCheckpointError

        drive = self._drive()
        snapshot: dict | None = None
        if drive is not None:
            snapshot = checkpoint_manager.restore_from_drive(drive)
        elif not allow_local:
            # Caller demanded a Drive-backed restore but there is no client.
            raise DriveNotReadyError("drive is not connected; cannot restore from Drive")
        if snapshot is None:
            # Fall back to the newest local checkpoint (still validated).
            snapshot = checkpoint_manager.restore_latest_local()
        if snapshot is None:
            return {"imported": 0, "reconciled": {}, "message_key": "msg.recovery_none"}
        try:
            snapshot = checkpoint_manager.validate_snapshot(snapshot)
        except InvalidCheckpointError as exc:
            raise TeleDriveError(str(exc), "msg.recovery_corrupt") from exc
        imported = checkpoint_manager.apply_snapshot(snapshot)
        reconciled: dict[str, Any] = {}
        if drive is not None:
            reconciled = checkpoint_manager.reconcile_with_drive(
                drive, self.ctx.queue_manager
            )
        return {"imported": imported, "reconciled": reconciled, "message_key": "msg.recovery_ok"}


# --------------------------------------------------------------------------
# Colab export
# --------------------------------------------------------------------------

class ColabExportService:
    """Serves the exact seven notebook cells shipped with the package."""

    CELLS_PATH = Path(__file__).parent / "colab_cells.json"

    def __init__(self, ctx) -> None:
        self.ctx = ctx

    def cells(self) -> list[dict[str, str]]:
        data = json.loads(self.CELLS_PATH.read_text(encoding="utf-8"))
        return data["cells"]

    def cells_text(self) -> str:
        blocks = []
        for index, cell in enumerate(self.cells(), start=1):
            blocks.append(f"# ==== Cell {index}: {cell['title']} ====\n{cell['code'].rstrip()}")
        return "\n\n".join(blocks)


def dashboard_defaults() -> dict[str, Any]:
    """Empty dashboard payload. Never fabricates numbers."""
    return {k: "" for k in ("dash.current", "dash.done", "dash.failed")}


def as_dict(value: Any) -> dict:
    try:
        return asdict(value)
    except Exception:
        return dict(value or {})
