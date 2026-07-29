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
    "telegram.set_credentials": 2,
    "telegram.send_code": 2,
    "telegram.resend_code": 2,
    "telegram.verify_code": 2,
    "telegram.verify_password": 2,
    "telegram.logout": 2,
    "telegram.status": 2,
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
        arity = ERROR_ARITY.get(action_id, DEFAULT_QUEUE_ARITY)
        if arity <= 1:
            return message
        return (message, *([None] * (arity - 1)))

    # ---- shared renderers ----

    def _telegram_view(self, status) -> tuple[str, str]:
        label = t("status.connected") if status.authorized else t("status.disconnected")
        detail = f"{label} · {status.state}"
        if status.account_label:
            detail += f" · {status.account_label}"
        if status.can_resend_in:
            detail += f" · {t('btn.resend_code')} {status.can_resend_in}s"
        return detail, label

    def _drive_view(self, status) -> tuple[str, str]:
        label = t("status.connected") if status.connected else t("status.disconnected")
        detail = f"{label} · {status.state}"
        if status.account_label:
            detail += f" · {status.account_label}"
        return detail, label

    def _queue_view(self, snapshot: dict) -> tuple[str, list]:
        counts = ", ".join(f"{t('state.' + k)}: {v}" for k, v in (snapshot.get("counts") or {}).items())
        header = f"{t('dash.queue_status')}: {snapshot.get('status', '')} · {counts}"
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
        quota = self.call("drive.refresh_quota")
        warning = t("warn.drive_almost_full") if quota.get("warn") else ""
        return f"{quota['label']} · {t('dash.free')}: {human_bytes(quota['free'])} {warning}".strip(), quota

    # ---- Analyze ----

    @action("analyze.run")
    def h_analyze_run(self, link: str, scope: str = "auto"):
        result = self.call("analyze.run", link, scope)
        summary = f"{result.total} · {human_bytes(result.total_bytes)}"
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
