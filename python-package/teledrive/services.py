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
    NothingSelectedError,
    TeleDriveError,
    TelegramNotReadyError,
)
from .filters import FilterSet, apply as apply_filterset
from .i18n import t, toggle as toggle_lang, set_language
from .logging_config import get_logger, tail as tail_log
from .media_scanner import scan_link
from .models import MediaItem
from .redaction import redact
from .telegram_links import parse as parse_link
from .utils import human_bytes, human_duration, now_iso, safe_disk_free

_log = get_logger("teledrive.services")

MAX_SCAN_MESSAGES = 1000


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
    """Owns analyze candidates, the active filter set, and the selection."""

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

    def selected_items(self) -> list[MediaItem]:
        chosen = {i.id: i for i in self.visible()}
        return [chosen[i] for i in self.selected_ids if i in chosen]

    def enqueue_selected(self) -> list[MediaItem]:
        items = self.selected_items()
        if not items:
            raise NothingSelectedError("no items selected")
        enqueued = self.ctx.queue_manager.bulk_enqueue(items)
        db.add_event("", "queue", "enqueued", {"count": len(enqueued)})
        return enqueued


class ScannerService:
    """Runs a scoped scan on the shared loop and hands results to selection."""

    def __init__(self, ctx) -> None:
        self.ctx = ctx

    def analyze(self, link: str, scope: str = "auto", limit: int = MAX_SCAN_MESSAGES) -> ScanResult:
        telegram_auth = self.ctx.telegram_auth
        if telegram_auth is None or not telegram_auth.authorized:
            raise TelegramNotReadyError("telegram is not authorized")
        parsed = parse_link((link or "").strip())
        if scope == "message" and parsed.message_id is None:
            raise TeleDriveError("link has no message id", "err.bad_link")
        if scope == "chat":
            parsed.message_id = None
        items = self.ctx.aio.run(scan_link(telegram_auth.client, parsed))
        items = items[: max(1, int(limit or MAX_SCAN_MESSAGES))]
        self.ctx.selection.set_candidates(items)
        db.add_event("", "scan", "analyzed", {"count": len(items), "scope": scope})
        return ScanResult(
            total=len(items),
            total_bytes=sum(i.size_bytes for i in items),
            scope=scope,
            rows=rows_for(items),
        )


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
    def __init__(self, ctx) -> None:
        self.ctx = ctx

    def tail(self, lines: int = 300) -> str:
        return redact(tail_log(lines=int(lines or 300)))

    def search(self, query: str, lines: int = 2000) -> str:
        text = redact(tail_log(lines=int(lines or 2000)))
        needle = (query or "").strip().lower()
        if not needle:
            return text
        return "\n".join(line for line in text.splitlines() if needle in line.lower())

    def export_file(self) -> str:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        target = LOGS_DIR / "teledrive_logs_export.txt"
        target.write_text(redact(tail_log(lines=20000)), encoding="utf-8")
        return str(target)


# --------------------------------------------------------------------------
# Settings + preferences
# --------------------------------------------------------------------------

class SettingsService:
    def __init__(self, ctx) -> None:
        self.ctx = ctx

    def set_concurrency(self, level: str | int) -> dict[str, Any]:
        config = self.ctx.config
        if isinstance(level, (int, float)) or str(level).isdigit():
            config.manual_concurrency = max(1, min(int(level), HARD_CONCURRENCY_CAP))
        else:
            if str(level) not in CONCURRENCY_LEVELS:
                raise TeleDriveError("unknown concurrency level", "err.bad_concurrency")
            config.concurrency = str(level)
            config.manual_concurrency = None
        value = config.concurrency_value()
        db.set_setting("concurrency", str(level))
        self.ctx.queue_manager.apply_concurrency(value)
        return {"level": str(level), "workers": value, "cap": HARD_CONCURRENCY_CAP}


class PreferencesService:
    def __init__(self, ctx) -> None:
        self.ctx = ctx

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
        theme = "dark" if str(theme).lower() == "dark" else "light"
        self.ctx.ui_state.extra["theme"] = theme
        db.set_setting("theme", theme)
        return theme


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
        return self.ctx.drive_client

    def persist(self) -> dict[str, Any]:
        path = checkpoint_manager.persist_local()
        file_id = None
        drive = self._drive()
        if drive is not None:
            file_id = checkpoint_manager.persist(drive)
        return {"local": str(path), "drive_file_id": file_id, "at": now_iso()}

    def restore_and_reconcile(self) -> dict[str, Any]:
        drive = self._drive()
        if drive is None:
            raise DriveNotReadyError("drive is required to restore a checkpoint")
        snapshot = checkpoint_manager.restore_from_drive(drive)
        if not snapshot:
            return {"imported": 0, "reconciled": {}, "message_key": "msg.recovery_none"}
        imported = checkpoint_manager.apply_snapshot(snapshot)
        reconciled = checkpoint_manager.reconcile_with_drive(drive)
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
