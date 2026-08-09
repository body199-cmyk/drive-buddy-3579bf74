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
from .redaction import redact, safe_exception
from .services import rows_for
from .telegram_auth import CODE_REQUESTED, PASSWORD_REQUIRED
from .ui_binder import component_update
from .utils import human_bytes

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
    "drive.connect": 2,
    "drive.reconnect": 2,
    "drive.status": 2,
    "drive.list_folders": 2,
    "drive.create_folder": 2,
    "drive.select_folder": 2,
    "drive.refresh_quota": 2,
    "analyze.run": 2,
    "analyze.apply_filters": 2,
    "analyze.select_all": 2,
    "analyze.clear_selection": 2,
    "analyze.enqueue_selected": 2,
    "logs.refresh": 1,
    "logs.search": 1,
    "logs.download": 1,
    "dashboard.refresh": 1,
    "settings.set_concurrency": 1,
    "settings.toggle_language": 1,
    "settings.set_theme": 1,
    "export.build_zip": 2,
    "export.colab_cells": 1,
    "recovery.restore": 1,
    "maintenance.checkpoint": 1,
}
DEFAULT_QUEUE_ARITY = 2


class Handlers:
    def __init__(self, ctx) -> None:
        self.ctx = ctx

    # ---- plumbing ----

    def call(self, action_id: str, *args, **kwargs) -> Any:
        """Resolve and invoke the service_path declared for this action."""
        spec = action_registry.get(action_id)
        if spec is None:
            raise TeleDriveError(f"unknown action {action_id}", "err.unknown_action")
        return self.ctx.resolve(spec.service_path)(*args, **kwargs)

    def _error(self, action_id: str, message: str):
        if action_id.startswith("telegram."):
            # A failed action must never desync the login panels: visibility is
            # re-derived from the LIVE state machine, not from the failed call.
            state = getattr(getattr(self.ctx, "telegram_auth", None), "state", "")
            return (message, None, *self._telegram_panels(state))
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
        return detail, label, code_panel, password_panel

    def _drive_view(self, status) -> tuple[str, str]:
        label = t("status.connected") if status.connected else t("status.disconnected")
        detail = f"{label} · {status.state}"
        if status.account_label:
            detail += f" · {status.account_label}"
        return detail, label

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
        return self._telegram_view(self.call("telegram.set_credentials", api_id, api_hash))

    @action("telegram.send_code")
    def h_telegram_send_code(self, phone: str):
        return self._telegram_view(self.call("telegram.send_code", phone))

    @action("telegram.resend_code")
    def h_telegram_resend_code(self):
        return self._telegram_view(self.call("telegram.resend_code"))

    @action("telegram.verify_code")
    def h_telegram_verify_code(self, code: str):
        return self._telegram_view(self.call("telegram.verify_code", code))

    @action("telegram.verify_password")
    def h_telegram_verify_password(self, password: str):
        return self._telegram_view(self.call("telegram.verify_password", password))

    @action("telegram.logout")
    def h_telegram_logout(self):
        return self._telegram_view(self.call("telegram.logout"))

    @action("telegram.status")
    def h_telegram_status(self):
        return self._telegram_view(self.call("telegram.status"))

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
        return t("msg.folders_loaded"), choices

    @action("drive.create_folder")
    def h_drive_create_folder(self, name: str, parent_id: str = "root"):
        folder = self.call("drive.create_folder", name, (parent_id or "root").strip() or "root")
        return t("msg.folder_created"), f"{folder.name} :: {folder.id}"

    @action("drive.select_folder")
    def h_drive_select_folder(self, choice: str):
        folder_id = str(choice or "").split("::")[-1].strip()
        folder = self.call("drive.select_folder", folder_id)
        return t("msg.folder_selected"), folder.id

    @action("drive.refresh_quota")
    def h_drive_refresh_quota(self):
        return _quota_view(self.call("drive.refresh_quota"))

    # ---- Analyze ----

    @action("analyze.run")
    def h_analyze_run(
        self,
        link: str,
        mode: str = "chat",
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
        return summary, result.rows

    @action("analyze.apply_filters")
    def h_analyze_apply_filters(
        self, media_types, extensions, min_size_mb, max_size_mb, date_from, date_to, include, exclude
    ):
        items = self.call(
            "analyze.apply_filters", media_types, extensions, min_size_mb, max_size_mb,
            date_from, date_to, include, exclude,
        )
        return f"{len(items)}", rows_for(items)

    @action("analyze.select_all")
    def h_analyze_select_all(self):
        selected = self.call("analyze.select_all")
        return f"{t('btn.select_all')}: {len(selected)}", rows_for(self.ctx.selection.visible())

    @action("analyze.clear_selection")
    def h_analyze_clear_selection(self):
        self.call("analyze.clear_selection")
        return f"{t('btn.clear_selection')}: 0", rows_for(self.ctx.selection.visible())

    @action("analyze.enqueue_selected")
    def h_analyze_enqueue_selected(self):
        items = self.call("analyze.enqueue_selected")
        return f"{t('btn.enqueue_selected')}: {len(items)}", self.queue_rows()

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
        return self.call("dashboard.refresh")

    @action("logs.refresh")
    def h_logs_refresh(self):
        return self.call("logs.refresh", 300)

    @action("logs.search")
    def h_logs_search(self, query: str):
        return self.call("logs.search", query)

    @action("logs.download")
    def h_logs_download(self):
        return self.call("logs.download")

    # ---- Settings ----

    @action("settings.set_concurrency")
    def h_settings_set_concurrency(self, level: str):
        result = self.call("settings.set_concurrency", level)
        return f"{result['level']} · {result['workers']}/{result['cap']}"

    @action("settings.toggle_language")
    def h_settings_toggle_language(self):
        return self.call("settings.toggle_language")

    @action("settings.set_theme")
    def h_settings_set_theme(self, theme: str):
        return self.call("settings.set_theme", theme)

    # ---- Export ----

    @action("export.build_zip")
    def h_export_build_zip(self):
        result = self.call("export.build_zip")
        return f"{t('msg.zip_ready')} · {result.zip_path}", result.zip_path

    @action("export.colab_cells")
    def h_export_colab_cells(self):
        return redact(self.call("export.colab_cells"))

    # ---- Maintenance ----

    @action("recovery.restore")
    def h_recovery_restore(self):
        result = self.call("recovery.restore")
        return f"{t(result['message_key'])} · imported={result['imported']}"

    @action("maintenance.checkpoint")
    def h_maintenance_checkpoint(self):
        result = self.call("maintenance.checkpoint")
        return f"{t('msg.checkpoint_saved')} · {result['at']}"


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
    telegram_detail, telegram_label, code_panel, password_panel = handlers._telegram_view(
        ctx.telegram_auth.status()
    )
    drive_detail, drive_label = handlers._drive_view(ctx.drive_auth.status())
    queue_header, queue_rows = handlers._queue_view(ctx.queue_manager.snapshot())
    quota_last = ctx.drive_quota.last or None
    quota_line, quota_payload = _quota_view(quota_last) if quota_last else ("", None)
    return {
        "language": ctx.ui_state.language,
        "theme": ctx.ui_state.extra.get("theme", "dark"),
        "telegram_detail": telegram_detail,
        "telegram_label": telegram_label,
        "otp_visible": bool(code_panel.get("visible")),
        "password_visible": bool(password_panel.get("visible")),
        "drive_detail": drive_detail,
        "drive_label": drive_label,
        "queue_header": queue_header,
        "queue_rows": queue_rows,
        "analyze_rows": rows_for(ctx.selection.visible()),
        "dashboard": ctx.stats.dashboard(),
        "logs": ctx.log_service.tail(300),
        "quota_line": quota_line,
        "quota_payload": quota_payload,
        "concurrency": ctx.config.concurrency_value(),
    }
