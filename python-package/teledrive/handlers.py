"""Named handlers — one per ACTION_SPEC. No lambdas, no closures, no UI logic.

Every handler resolves its declared service_path through the ApplicationContext
and returns UI-safe, localized, redacted values.
"""
from __future__ import annotations

import functools
import uuid
from typing import Any, Callable

from . import action_registry
from .errors import TeleDriveError
from .i18n import t
from .logging_config import get_logger
from .media_scanner import DEFAULT_SCAN_MODE
from .redaction import redact, safe_exception
from .services import DEFAULT_THEME, LiveUiStateService, candidate_rows_for, rows_for
from .telegram_auth import CODE_REQUESTED, PASSWORD_REQUIRED
from .ui_binder import component_update
from .ui_theme import theme_style_block
from .utils import human_bytes

# Gradio is required by the running app but must stay optional for non-UI
# tests. ``SelectData`` is only used as a type hint so Gradio's event system
# injects the clicked-cell payload into ``h_analyze_toggle_row``; the
# placeholder class keeps import-time resolution working when gradio is
# absent (handler-level tests call the handler with a plain fake instead).
try:  # pragma: no cover - exercised in every real app run
    import gradio as gr  # noqa: F401

    SelectData = gr.SelectData
except Exception:  # pragma: no cover - non-UI environments
    class SelectData:  # type: ignore[no-redef]
        """Placeholder when gradio is not installed."""


def status_ok(message: str) -> str:
    return f"✅ {message}"


def status_error(message: str) -> str:
    return f"⚠️ {message}"


def chip_html(value: str, state: str = "warn") -> str:
    """Top-bar chip markup. Colors come only from ui_theme CSS variables."""
    return f'<span class="td-chip" data-state="{state}">{value}</span>'

_log = get_logger("teledrive.handlers")


def action(action_id: str) -> Callable:
    """Bind a handler to its spec and give it uniform logging + error mapping."""

    def decorator(func: Callable) -> Callable:
        spec = action_registry.get(action_id)
        if spec is None:
            raise KeyError(f"handler declared for undeclared action {action_id!r}")

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            correlation = uuid.uuid4().hex[:8]
            _log.info("action=%s cid=%s start", action_id, correlation)
            try:
                vault = getattr(self.ctx, "session_vault", None)
                if vault is not None and vault.pending:
                    vault.flush_pending()
            except Exception:  # noqa: BLE001 - a vault retry must never break an action
                _log.warning("vault flush skipped action=%s", action_id)
            try:
                result = func(self, *args, **kwargs)
                _log.info("action=%s cid=%s ok", action_id, correlation)
                return result
            except TeleDriveError as exc:
                message = f"{t(exc.message_key)} [{correlation}]"
                _log.warning("action=%s cid=%s failed: %s", action_id, correlation,
                             safe_exception(exc))
                return self._error(action_id, message)
            except Exception as exc:  # noqa: BLE001 — never leak a traceback to the UI
                _log.exception("action=%s cid=%s crashed", action_id, correlation)
                return self._error(action_id, f"{t('err.unknown')} [{correlation}]")

        wrapper.action_id = action_id
        wrapper.service_path = spec.service_path
        return wrapper

    return decorator


# Number of UI outputs each action writes; used to shape error returns.
ERROR_ARITY: dict[str, int] = {
    "telegram.set_credentials": 4,
    "telegram.send_code": 4,
    "telegram.resend_code": 4,
    "telegram.verify_code": 4,
    "telegram.verify_password": 4,
    "telegram.logout": 4,
    "telegram.status": 4,
    "session.save": 3,
    "session.autorestore": 3,
    "session.forget": 3,
    "drive.connect": 2,
    "drive.reconnect": 2,
    "drive.status": 2,
    "drive.list_folders": 2,
    # DOC-39 §4: one folder truth broadcast to every panel + the top chip:
    # (own choice, own current, own message, top chip,
    #  other currents x3, other messages x3).
    "drive.create_folder": 10,
    "drive.select_folder": 10,
    "drive.refresh_quota": 2,
    # DOC-39 §5 selection stage: (analyze_message, candidates_table,
    # selection_preview, enqueue_btn, group_choice).
    "analyze.run": 5,
    "analyze.set_mode": 4,
    "analyze.apply_filters": 5,
    "analyze.select_all": 5,
    "analyze.clear_selection": 5,
    "analyze.select_range": 5,
    "analyze.toggle_row": 5,
    "analyze.select_group": 5,
    # (analyze_message, queue_table, queue_status, selection_preview, enqueue_btn)
    "analyze.enqueue_selected": 5,
    "logs.refresh": 2,       # (logs_text, status)
    "logs.search": 2,        # (logs_text, status)
    "logs.download": 2,      # (file_component, status)
    "dashboard.refresh": 1,  # (dashboard_json)
    "settings.set_concurrency": 2,  # (slider_value, status)
    "settings.toggle_language": 1,  # (lang_state)
    "settings.set_theme": 2,        # (theme_style_html, status)
    "export.build_zip": 2,          # (message, file)
    "export.colab_cells": 2,        # (text, status)
    "recovery.restore": 1,
    "maintenance.checkpoint": 1,
    # M20-T03: the whole derived step layout, in ui.py's flow_outputs order.
    "flow.sync": 12,
    "react.bridge.request": 1,
}
DEFAULT_QUEUE_ARITY = 2


class Handlers:
    def __init__(self, ctx) -> None:
        self.ctx = ctx
        # M24: one adapter over this same context. It owns no runtime/client/DB.
        from .react_bridge import ReactBridge

        self.live_ui_state = LiveUiStateService(ctx)
        self.react_bridge = ReactBridge(
            ctx, action_registry, self.live_ui_state.snapshot
        )

    # ---- plumbing ----

    def call(self, action_id: str, *args, **kwargs) -> Any:
        """Resolve and invoke the service_path declared for this action."""
        spec = action_registry.get(action_id)
        if spec is None:
            raise TeleDriveError(f"unknown action {action_id}", "err.unknown_action")
        return self.ctx.resolve(spec.service_path)(*args, **kwargs)

    def bridge_request(self, request_payload):
        """Service path for the single registered React bridge event."""
        return self.react_bridge.handle(request_payload)

    def bridge_initial_response(self) -> dict[str, Any]:
        """The first browser value is a redacted snapshot, never demo data."""
        return self.react_bridge.initial_response()

    def _error(self, action_id: str, message: str):
        if action_id.startswith("telegram."):
            # A failed action must never desync the login panels: visibility is
            # re-derived from the LIVE state machine, not from the failed call.
            state = getattr(getattr(self.ctx, "telegram_auth", None), "state", "")
            return (message, None, *self._telegram_panels(state))
        if action_id == "analyze.enqueue_selected":
            # A refused enqueue (empty selection / no folder / disk / quota)
            # must not blank the queue table: keep every panel live.
            header, queue_rows = self._queue_view(self.ctx.queue_manager.snapshot())
            rows, preview, enqueue_update, _groups = self._selection_view()
            return message, queue_rows, header, preview, enqueue_update
        arity = ERROR_ARITY.get(action_id, DEFAULT_QUEUE_ARITY)
        if arity <= 1:
            return message
        return (message, *([None] * (arity - 1)))

    # ---- shared renderers ----

    def _telegram_panels(self, state: str) -> tuple[Any, Any]:
        """OTP panel ONLY in CODE_REQUESTED, 2FA panel ONLY in PASSWORD_REQUIRED.

        No field is ever rendered "just in case": a user without 2FA never sees
        a password box, and nobody sees an OTP box before Telegram really sent
        a code.
        """
        return (
            component_update(visible=state == CODE_REQUESTED),
            component_update(visible=state == PASSWORD_REQUIRED),
        )

    def _telegram_view(self, status) -> tuple[str, str, Any, Any]:
        label = t("status.connected") if status.authorized else t("status.disconnected")
        detail = f"{label} · {status.state}"
        if status.account_label:
            detail += f" · {status.account_label}"
        if status.can_resend_in:
            detail += f" · {t('btn.resend_code')} {status.can_resend_in}s"
        code_panel, password_panel = self._telegram_panels(status.state)
        return (
            detail,
            chip_html(label, "ok" if status.authorized else "err"),
            code_panel,
            password_panel,
        )

    def _drive_view(self, status) -> tuple[str, str]:
        label = t("status.connected") if status.connected else t("status.disconnected")
        detail = f"{label} · {status.state}"
        if status.account_label:
            detail += f" · {status.account_label}"
        return detail, chip_html(label, "ok" if status.connected else "err")

    # ---- DOC-39 §5 selection stage (shared renderers) ----

    def _selection_view(self) -> tuple[list, str, dict, dict]:
        """(candidate_rows, preview_text, enqueue_update, group_update).

        Everything derives from LIVE context state — the candidates, the
        selection, and the persisted Drive target. Empty state renders as an
        empty table and a disabled enqueue button; nothing is fabricated.
        """
        ctx = self.ctx
        sel = ctx.selection
        visible = sel.visible()
        rows = candidate_rows_for(visible, sel.selected_ids)
        summary = sel.summary()
        ref = ctx.drive_folders.selected()
        folder_label = (ref.name or ref.id) if ref else t("msg.no_folder_selected")
        preview = (
            f"{t('sel.count')}: {summary['count']} · "
            f"{t('sel.total_size')}: {human_bytes(summary['total_bytes'])} · "
            f"{t('sel.required_space')}: {human_bytes(summary['total_bytes'])} · "
            f"{t('sel.target_folder')}: {folder_label}"
        )
        can_enqueue = summary["count"] > 0 and ref is not None
        groups = sel.groups()
        return (
            rows,
            preview,
            component_update(interactive=can_enqueue),
            component_update(choices=groups),
        )

    def _queue_view(self, snapshot: dict) -> tuple[str, list]:
        counts = ", ".join(f"{t('state.' + k)}: {v}" for k, v in (snapshot.get("counts") or {}).items())
        header = f"{t('dash.queue_status')}: {snapshot.get('status', '')}"
        if counts:
            header += f" · {counts}"
        return header, self.queue_rows()

    def queue_rows(self) -> list:
        from . import database as db

        return rows_for(db.list_items(limit=500))

    # ---- Telegram ----

    @action("telegram.set_credentials")
    def h_telegram_set_credentials(self, api_id: str, api_hash: str):
        # DOC-39 follow-up (§10, M18-T02): TelegramAuth.set_credentials creates
        # the Telethon client and calls connect()/is_authorized() WITHOUT an
        # exception handler, so any transport/DC-level failure (asyncio
        # IncompleteReadError, TimeoutError, ConnectionError, OSError, an RPC
        # error during the handshake, a locked session file, ...) escapes the
        # service and the generic @action wrapper turns it into a dead-end
        # "err.unknown". Bad api_id/api_hash still surface as their own
        # classified TeleDriveError (err.bad_api_id / err.bad_api_hash) — this
        # branch only re-classifies the *transport* failures into a localized,
        # retryable message while the full traceback stays in the logs
        # (redacted) for diagnosis.
        try:
            status = self.call("telegram.set_credentials", api_id, api_hash)
        except TeleDriveError:
            raise
        except Exception as exc:  # noqa: BLE001 — see comment above
            _log.exception("telegram.set_credentials transport failure at connect")
            raise TeleDriveError(
                f"telegram connect failed: {type(exc).__name__}",
                "err.tg_connect_failed",
            ) from exc
        # M24-T03: an existing local session authorizes right here; if this
        # Drive account has no vault yet, create it now (skipped when present).
        if getattr(status, "authorized", False):
            self.ctx.session_vault.save_after_login()
        return self._telegram_view(status)

    @action("telegram.send_code")
    def h_telegram_send_code(self, phone: str):
        return self._telegram_view(self.call("telegram.send_code", phone))

    @action("telegram.resend_code")
    def h_telegram_resend_code(self):
        return self._telegram_view(self.call("telegram.resend_code"))

    @action("telegram.verify_code")
    def h_telegram_verify_code(self, code: str):
        status = self.call("telegram.verify_code", code)
        # M24-T03: persist the sign-in the moment it becomes real, so the next
        # Colab VM on this Drive account needs no code. Quiet by design: a
        # Drive failure must never turn a successful login into an error.
        if getattr(status, "authorized", False):
            self.ctx.session_vault.save_after_login()
        return self._telegram_view(status)

    @action("telegram.verify_password")
    def h_telegram_verify_password(self, password: str):
        status = self.call("telegram.verify_password", password)
        if getattr(status, "authorized", False):
            self.ctx.session_vault.save_after_login()
        return self._telegram_view(status)

    @action("telegram.logout")
    def h_telegram_logout(self):
        # M24-T03: the Drive vault must die WITH the account. This runs BEFORE
        # the logout while Drive and the session are still live, and it is
        # quiet so a Drive hiccup can never block signing out.
        self.ctx.session_vault.forget_quiet()
        return self._telegram_view(self.call("telegram.logout"))

    @action("telegram.status")
    def h_telegram_status(self):
        return self._telegram_view(self.call("telegram.status"))

    def _session_view(self, result, telegram_status=None) -> tuple[str, str, str]:
        view = self._telegram_view(telegram_status or self.ctx.telegram_auth.status())
        detail, chip = view[0], view[1]
        message = t(result.message_key)
        if getattr(result, "phone_label", ""):
            message += f" · {result.phone_label}"
        return message, detail, chip

    @action("session.save")
    def h_session_save(self, api_id: str = "", api_hash: str = "", phone: str = ""):
        result = self.call("session.save", api_id, api_hash, phone)
        return self._session_view(result)

    @action("session.autorestore")
    def h_session_autorestore(self):
        result = self.call("session.autorestore")
        return self._session_view(result)

    @action("session.forget")
    def h_session_forget(self):
        result = self.call("session.forget")
        return self._session_view(result)

    # ---- Drive ----

    @action("drive.connect")
    def h_drive_connect(self):
        return self._drive_view(self.call("drive.connect"))

    @action("drive.reconnect")
    def h_drive_reconnect(self):
        return self._drive_view(self.call("drive.reconnect"))

    @action("drive.status")
    def h_drive_status(self):
        return self._drive_view(self.call("drive.status"))

    @action("drive.list_folders")
    def h_drive_list_folders(self, parent_id: str = "root"):
        folders = self.call("drive.list_folders", (parent_id or "root").strip() or "root")
        choices = [f"{folder.name} :: {folder.id}" for folder in folders]
        # A Gradio Dropdown consumes choices via an update payload; a bare list
        # would be misread as the *selected value*, leaving the menu empty.
        return t("msg.folders_loaded"), component_update(choices=choices)

    def _folder_broadcast(self, choice_update: dict, name: str, message: str) -> tuple:
        """DOC-39 §4: one folder truth, propagated to every visible panel.

        Return shape (10 values) mirrors the wiring in ui.py:
        (own choice, own current, own message, top chip,
         other-1 current, other-2 current, other-3 current,
         other-1 message, other-2 message, other-3 message).
        """
        return (
            choice_update,
            name,
            message,
            chip_html(name or t("msg.no_folder_selected"), "ok"),
            name, name, name,
            message, message, message,
        )

    @action("drive.create_folder")
    def h_drive_create_folder(self, name: str, parent_id: str = "root"):
        folder = self.call("drive.create_folder", name, (parent_id or "root").strip() or "root")
        # Creation selects immediately: the persisted destination is always its ID,
        # while the name is strictly a display value.
        choice = f"{folder.name} :: {folder.id}"
        return self._folder_broadcast(
            component_update(choices=[choice], value=choice),
            folder.name,
            t("msg.folder_created"),
        )

    @action("drive.select_folder")
    def h_drive_select_folder(self, choice: str):
        folder_id = str(choice or "").split("::")[-1].strip()
        folder = self.call("drive.select_folder", folder_id)
        selected = f"{folder.name} :: {folder.id}"
        return self._folder_broadcast(
            component_update(value=selected),
            folder.name,
            t("msg.folder_selected"),
        )

    @action("drive.refresh_quota")
    def h_drive_refresh_quota(self):
        return _quota_view(self.call("drive.refresh_quota"))

    # ---- Analyze ----

    @action("analyze.run")
    def h_analyze_run(
        self,
        link: str,
        mode: str = DEFAULT_SCAN_MODE,
        message_id: int | None = None,
        start_id: int | None = None,
        end_id: int | None = None,
        limit: int | float | None = None,
        media_types=None,
        *args,
        **kwargs,
    ):
        # Backward-compat: old tests call with (link, scope) where scope=="auto".
        # Support both `mode` and legacy `scope` names, and tolerate fewer args.
        if "scope" in kwargs:
            mode = kwargs.pop("scope", mode)
        # If caller supplied only 2 args: handler(link, "auto") -> mode will be "auto"
        # Keep alias auto->chat for validation, but keep scope in summary.
        # Normalize mode alias here as well.
        if isinstance(mode, str) and mode.strip().lower() == "auto":
            mode = "chat"
        # Handle legacy positional where second arg was scope but caller passed via *args
        # (not needed for spec flow, but keeps contract tests green).
        if args and mode == "chat" and len(args) >= 1:
            # extra positional arg could be limit when legacy signature used
            try:
                if limit is None:
                    limit = int(args[0])
            except Exception:
                pass
        result = self.call(
            "analyze.run",
            link,
            mode,
            int(message_id) if message_id else None,
            int(start_id) if start_id else None,
            int(end_id) if end_id else None,
            int(limit or 1000),
            media_types or ["all"],
        )
        summary = f"{result.total} · {human_bytes(result.total_bytes)} · {result.scope}"
        return summary, *self._selection_view()

    @action("analyze.set_mode")
    def h_analyze_set_mode(self, mode: str):
        """Show only the numeric inputs the chosen scan mode consumes.

        Visibility is derived from the scanner service, never from a copy of the
        mapping kept in the layout, so the UI can never offer a field the
        validator will ignore or hide one it requires.
        """
        fields = self.call("analyze.set_mode", mode)
        return (
            component_update(visible=fields["message_id"]),
            component_update(visible=fields["start_id"]),
            component_update(visible=fields["end_id"]),
            component_update(visible=fields["limit"]),
        )

    @action("analyze.apply_filters")
    def h_analyze_apply_filters(
        self, media_types, extensions, min_size_mb, max_size_mb, date_from, date_to, include, exclude
    ):
        items = self.call(
            "analyze.apply_filters", media_types, extensions, min_size_mb, max_size_mb,
            date_from, date_to, include, exclude,
        )
        return f"{len(items)}", *self._selection_view()

    @action("analyze.select_all")
    def h_analyze_select_all(self):
        selected = self.call("analyze.select_all")
        return f"{t('btn.select_all')}: {len(selected)}", *self._selection_view()

    @action("analyze.clear_selection")
    def h_analyze_clear_selection(self):
        self.call("analyze.clear_selection")
        return f"{t('btn.clear_selection')}: 0", *self._selection_view()

    @action("analyze.toggle_row")
    def h_analyze_toggle_row(self, evt: SelectData):
        """Manual row selection: the clicked table row toggles its candidate.

        ``evt.index`` is the (row, col) cell index Gradio sends on
        ``Dataframe.select``; only the row matters. The table re-renders with
        the marker cell (☑/☐) reflecting the live selection state.
        """
        index = getattr(evt, "index", None)
        row = index[0] if isinstance(index, (tuple, list)) else index
        self.call("analyze.toggle_row", int(row or 0))
        count = len(self.ctx.selection.selected_ids)
        return f"{t('btn.toggle_row')}: {count}", *self._selection_view()

    @action("analyze.select_range")
    def h_analyze_select_range(self, start_id, end_id):
        selected = self.call("analyze.select_range", start_id, end_id)
        return f"{t('btn.select_range')}: {len(selected)}", *self._selection_view()

    @action("analyze.select_group")
    def h_analyze_select_group(self, choice: str):
        chat_id = str(choice or "").split("::")[-1].strip()
        selected = self.call("analyze.select_group", chat_id)
        return f"{t('btn.select_group')}: {len(selected)}", *self._selection_view()

    @action("analyze.enqueue_selected")
    def h_analyze_enqueue_selected(self):
        items = self.call("analyze.enqueue_selected")
        header, queue_rows = self._queue_view(self.ctx.queue_manager.snapshot())
        msg = f"{t('btn.enqueue_selected')}: {len(items)}"
        rows, preview, enqueue_update, _groups = self._selection_view()
        return msg, queue_rows, header, preview, enqueue_update

    # ---- Transfers ----

    @action("queue.start_selected")
    def h_queue_start_selected(self):
        self.call("queue.start_selected")
        return self._queue_view(self.ctx.queue_manager.snapshot())

    @action("queue.pause")
    def h_queue_pause(self):
        return self._queue_view(self.call("queue.pause"))

    @action("queue.resume")
    def h_queue_resume(self):
        return self._queue_view(self.call("queue.resume"))

    @action("queue.stop")
    def h_queue_stop(self):
        return self._queue_view(self.call("queue.stop"))

    @action("queue.retry_failed")
    def h_queue_retry_failed(self):
        return self._queue_view(self.call("queue.retry_failed"))

    @action("queue.clear_completed")
    def h_queue_clear_completed(self):
        return self._queue_view(self.call("queue.clear_completed"))

    @action("queue.clear_incomplete")
    def h_queue_clear_incomplete(self):
        return self._queue_view(self.call("queue.clear_incomplete"))

    @action("queue.refresh")
    def h_queue_refresh(self):
        return self._queue_view(self.call("queue.refresh"))

    @action("queue.pause_item")
    def h_queue_pause_item(self, item_id: str):
        return self._queue_view(self.call("queue.pause_item", str(item_id).strip()))

    @action("queue.resume_item")
    def h_queue_resume_item(self, item_id: str):
        return self._queue_view(self.call("queue.resume_item", str(item_id).strip()))

    @action("queue.stop_item")
    def h_queue_stop_item(self, item_id: str):
        return self._queue_view(self.call("queue.stop_item", str(item_id).strip()))

    @action("queue.retry_item")
    def h_queue_retry_item(self, item_id: str):
        return self._queue_view(self.call("queue.retry_item", str(item_id).strip()))

    # ---- Dashboard / logs ----

    @action("dashboard.refresh")
    def h_dashboard_refresh(self):
        # service_path is stats.dashboard; Handlers.call resolves via the
        # declared action_id -> spec.service_path, so we pass the action_id.
        data = self.call("dashboard.refresh")
        return component_update(value=data)

    @action("logs.refresh")
    def h_logs_refresh(self, level: str = "ALL"):
        text = self.call("logs.refresh", 300, str(level or "ALL"))
        return component_update(value=text), status_ok(t("msg.logs_refreshed"))

    @action("logs.search")
    def h_logs_search(self, query: str, level: str = "ALL"):
        text = self.call("logs.search", str(query or ""), 2000, str(level or "ALL"))
        lines = 0 if not text else text.count("\n") + 1
        return component_update(value=text), status_ok(f"{t('msg.logs_refreshed')} · {lines}")

    @action("logs.download")
    def h_logs_download(self, level: str = "ALL"):
        path = self.call("logs.download", str(level or "ALL"))
        return component_update(value=path, visible=True), status_ok(t("msg.zip_ready"))

    # ---- Settings ----

    @action("settings.set_concurrency")
    def h_settings_set_concurrency(self, value):
        # ADR-0001: default 2, hard cap 100. Accept an integer 1..100 or a
        # named level (safe/balanced/fast/turbo/max). Out-of-range values are
        # rejected — the slider returns to its previous value with a localized
        # error — so the number on screen is always the number the engine uses.
        # Above CONCURRENCY_WARN_ABOVE the value is accepted with a risk note.
        from .config import CONCURRENCY_LEVELS, CONCURRENCY_MIN, HARD_CONCURRENCY_CAP

        current = self.ctx.settings.current()
        n = None
        if not isinstance(value, bool):
            try:
                n = int(value)
            except (TypeError, ValueError):
                key = str(value or "").strip().lower()
                if key in CONCURRENCY_LEVELS:
                    n = CONCURRENCY_LEVELS[key]
        if n is None or n < CONCURRENCY_MIN or n > HARD_CONCURRENCY_CAP:
            return (
                component_update(value=current),
                status_error(t("settings.concurrency.invalid")),
            )
        result = self.call("settings.set_concurrency", n)
        workers = result.get("workers", n)
        line = f"{t('settings.concurrency.saved')} · {workers}/{result.get('cap', HARD_CONCURRENCY_CAP)}"
        if result.get("warn"):
            return (
                component_update(value=workers),
                status_ok(f"{line} · {t('warn.concurrency_high')}"),
            )
        return (component_update(value=workers), status_ok(line))

    @action("settings.toggle_language")
    def h_settings_toggle_language(self):
        return self.call("settings.toggle_language")

    @action("settings.set_theme")
    def h_settings_set_theme(self, theme: str):
        chosen = self.call("settings.set_theme", theme)
        return (
            component_update(value=theme_style_block(chosen)),
            status_ok(t(f"settings.theme.{chosen}")),
        )

    # ---- Export ----

    @action("export.build_zip")
    def h_export_build_zip(self):
        result = self.call("export.build_zip")
        return (
            status_ok(f"{t('msg.zip_ready')} · {result.zip_path}"),
            component_update(value=result.zip_path, visible=True),
        )

    @action("export.colab_cells")
    def h_export_colab_cells(self):
        text = redact(self.call("export.colab_cells"))
        return component_update(value=text), status_ok(t("msg.zip_ready"))

    # ---- Maintenance ----

    @action("recovery.restore")
    def h_recovery_restore(self):
        result = self.call("recovery.restore")
        return status_ok(
            f"{t(result['message_key'])} · imported={result['imported']}"
        )

    @action("maintenance.checkpoint")
    def h_maintenance_checkpoint(self):
        result = self.call("maintenance.checkpoint")
        return status_ok(f"{t('msg.checkpoint_saved')} · {result['at']}")

    # ---- React bridge (M24, official Gradio component transport) ----

    @action("react.bridge.request")
    def h_react_bridge_request(self, request_payload):
        response = self.call("react.bridge.request", request_payload)
        return component_update(value=response)

    # ---- Flow ----

    @action("flow.sync")
    def h_flow_sync(self):
        """Recompute the whole step layout from the live context.

        Returns exactly the 12 updates declared by ``flow_outputs`` in ui.py.
        The gradio coupling stays inside the view module, not here.
        """
        from .ui_flow_view import render

        return render(self.call("flow.sync"))


def _quota_view(quota: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Read-only quota line shared by the refresh handler and the shell seed."""
    warning = t("warn.drive_almost_full") if quota.get("warn") else ""
    line = f"{quota['label']} · {t('dash.free')}: {human_bytes(quota['free'])} {warning}".strip()
    return line, quota


def shell_seed(ctx) -> dict[str, Any]:
    """Initial UI values, always derived from LIVE context state.

    The graphite shell re-renders in a new language/direction without touching
    the runtime: Telegram login state, the queue, transfers and the selection
    all live on the ApplicationContext. These seeds rebuild every component
    from that live state so a re-render can never reset panels to a default
    that contradicts reality (e.g. hiding an OTP box while CODE_REQUESTED) and
    never fabricates a value (empty tables stay empty, chips start
    Disconnected only when the state machine really says so).
    """
    handlers = ctx.handlers
    telegram_detail, telegram_chip, code_panel, password_panel = handlers._telegram_view(
        ctx.telegram_auth.status()
    )
    drive_detail, drive_chip = handlers._drive_view(ctx.drive_auth.status())
    queue_header, queue_rows = handlers._queue_view(ctx.queue_manager.snapshot())
    quota_last = ctx.drive_quota.last or None
    quota_line, quota_payload = _quota_view(quota_last) if quota_last else ("", None)

    # DOC-39 §4: the top folder chip always reads the ONE persisted folder ID.
    dr_connected = ctx.drive_auth.connected
    folder_name = ctx.drive_folders.current_folder_name() if dr_connected else ""
    if not dr_connected:
        folder_label, folder_state = t("status.disconnected"), "err"
    elif folder_name:
        folder_label, folder_state = folder_name, "ok"
    else:
        folder_label, folder_state = t("msg.no_folder_selected"), "warn"

    # DOC-39 §5: selection stage seeds — all derived from live context.
    rows, preview, enqueue_update, group_update = handlers._selection_view()
    summary = ctx.selection.summary()
    folder_ref = ctx.drive_folders.selected()
    return {
        "language": ctx.ui_state.language,
        # M20-T02: light-only shell -> light default (see services.DEFAULT_THEME).
        "theme": ctx.ui_state.extra.get("theme", DEFAULT_THEME),
        "telegram_detail": telegram_detail,
        "telegram_chip": telegram_chip,
        "telegram_connected": ctx.telegram_auth.authorized,
        "otp_visible": bool(code_panel.get("visible")),
        "password_visible": bool(password_panel.get("visible")),
        "drive_detail": drive_detail,
        "drive_chip": drive_chip,
        "drive_connected": dr_connected,
        "folder_chip": chip_html(folder_label, folder_state),
        "folder_label": folder_label,
        "queue_header": queue_header,
        "queue_rows": queue_rows,
        "analyze_rows": rows,
        "selection_count": summary["count"],
        "selection_size": human_bytes(summary["total_bytes"]),
        "selection_preview": preview,
        "enqueue_allowed": bool(summary["count"] > 0 and folder_ref is not None),
        "group_choices": [label for label, _value in (group_update.get("choices") or [])],
        "analyze_mode": DEFAULT_SCAN_MODE,
        "analyze_fields": ctx.scanner.mode_fields(DEFAULT_SCAN_MODE),
        "dashboard": ctx.stats.dashboard(),
        "logs": ctx.log_service.tail(300),
        "quota_line": quota_line,
        "quota_payload": quota_payload,
        "concurrency": ctx.config.concurrency_value(),
    }
