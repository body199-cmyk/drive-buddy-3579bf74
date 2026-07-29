"""ACTION_SPECS — the single declaration of every visible control.

Constitution Section 4: a control may only be rendered when its spec exists,
its handler is named, its service_path resolves on the live context, and a test
proves the handler calls that exact service.

`implemented=True` is set only in the commit that adds handler + service method.
`tested=True` is set only in the commit that adds the passing binding test.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator


@dataclass(frozen=True)
class ActionSpec:
    action_id: str
    handler_name: str
    service_path: str
    label_key: str
    section: str
    implemented: bool = False
    tested: bool = False

    @property
    def ready(self) -> bool:
        return self.implemented and self.tested


def _spec(action_id, handler_name, service_path, label_key, section, ready=True):
    return ActionSpec(
        action_id=action_id,
        handler_name=handler_name,
        service_path=service_path,
        label_key=label_key,
        section=section,
        implemented=ready,
        tested=ready,
    )


ACTION_SPECS: tuple[ActionSpec, ...] = (
    # ---- Connection Center: Telegram ----
    _spec("telegram.set_credentials", "h_telegram_set_credentials",
          "telegram_auth.set_credentials", "btn.connect_telegram", "connection"),
    _spec("telegram.send_code", "h_telegram_send_code",
          "telegram_auth.send_code", "btn.send_code", "connection"),
    _spec("telegram.resend_code", "h_telegram_resend_code",
          "telegram_auth.resend_code", "btn.resend_code", "connection"),
    _spec("telegram.verify_code", "h_telegram_verify_code",
          "telegram_auth.verify_code", "btn.verify", "connection"),
    _spec("telegram.verify_password", "h_telegram_verify_password",
          "telegram_auth.verify_password", "btn.verify_password", "connection"),
    _spec("telegram.logout", "h_telegram_logout",
          "telegram_auth.logout", "btn.logout", "connection"),
    _spec("telegram.status", "h_telegram_status",
          "telegram_auth.status", "dash.telegram_status", "connection"),

    # ---- Connection Center: Google Drive (native Colab auth only) ----
    _spec("drive.connect", "h_drive_connect",
          "drive_auth.connect", "btn.link_drive", "connection"),
    _spec("drive.reconnect", "h_drive_reconnect",
          "drive_auth.reconnect", "btn.drive_reconnect", "connection"),
    _spec("drive.status", "h_drive_status",
          "drive_auth.status", "dash.drive_status", "connection"),
    _spec("drive.list_folders", "h_drive_list_folders",
          "drive_folders.list_children", "btn.drive_list_folders", "connection"),
    _spec("drive.create_folder", "h_drive_create_folder",
          "drive_folders.create", "btn.drive_create_folder", "connection"),
    _spec("drive.select_folder", "h_drive_select_folder",
          "drive_folders.select", "btn.drive_select_folder", "connection"),
    _spec("drive.refresh_quota", "h_drive_refresh_quota",
          "drive_quota.refresh", "btn.refresh_quota", "connection"),

    # ---- Analyze ----
    _spec("analyze.run", "h_analyze_run", "scanner.analyze", "btn.analyze", "analyze"),
    _spec("analyze.apply_filters", "h_analyze_apply_filters",
          "selection.apply_filters", "btn.apply_filters", "analyze"),
    _spec("analyze.select_all", "h_analyze_select_all",
          "selection.select_all_visible", "btn.select_all", "analyze"),
    _spec("analyze.clear_selection", "h_analyze_clear_selection",
          "selection.clear", "btn.clear_selection", "analyze"),
    _spec("analyze.enqueue_selected", "h_analyze_enqueue_selected",
          "selection.enqueue_selected", "btn.enqueue_selected", "analyze"),

    # ---- Transfers ----
    _spec("queue.start_selected", "h_queue_start_selected",
          "queue_manager.start_selected", "btn.start", "transfers"),
    _spec("queue.pause", "h_queue_pause", "queue_manager.pause", "btn.pause", "transfers"),
    _spec("queue.resume", "h_queue_resume", "queue_manager.resume", "btn.resume", "transfers"),
    _spec("queue.stop", "h_queue_stop", "queue_manager.stop", "btn.stop", "transfers"),
    _spec("queue.retry_failed", "h_queue_retry_failed",
          "queue_manager.retry_failed", "btn.retry_failed", "transfers"),
    _spec("queue.clear_completed", "h_queue_clear_completed",
          "queue_manager.clear_completed_metadata", "btn.clear_completed", "transfers"),
    _spec("queue.refresh", "h_queue_refresh",
          "queue_manager.snapshot", "btn.refresh", "transfers"),
    _spec("queue.pause_item", "h_queue_pause_item",
          "queue_manager.pause_item", "btn.pause_item", "transfers"),
    _spec("queue.resume_item", "h_queue_resume_item",
          "queue_manager.resume_item", "btn.resume_item", "transfers"),
    _spec("queue.stop_item", "h_queue_stop_item",
          "queue_manager.stop_item", "btn.stop_item", "transfers"),
    _spec("queue.retry_item", "h_queue_retry_item",
          "queue_manager.retry_item", "btn.retry_item", "transfers"),

    # ---- Dashboard ----
    _spec("dashboard.refresh", "h_dashboard_refresh",
          "stats.dashboard", "btn.refresh", "dashboard"),

    # ---- Logs ----
    _spec("logs.refresh", "h_logs_refresh", "log_service.tail", "btn.refresh", "logs"),
    _spec("logs.search", "h_logs_search", "log_service.search", "btn.search_logs", "logs"),
    _spec("logs.download", "h_logs_download",
          "log_service.export_file", "btn.download_logs", "logs"),

    # ---- Settings ----
    _spec("settings.set_concurrency", "h_settings_set_concurrency",
          "settings.set_concurrency", "form.concurrency", "settings"),
    _spec("settings.toggle_language", "h_settings_toggle_language",
          "preferences.toggle_language", "btn.language", "settings"),
    _spec("settings.set_theme", "h_settings_set_theme",
          "preferences.set_theme", "btn.theme", "settings"),

    # ---- Colab code / export ----
    _spec("export.build_zip", "h_export_build_zip",
          "package_service.build_tested_archive", "btn.build_zip", "export"),
    _spec("export.colab_cells", "h_export_colab_cells",
          "colab_export.cells_text", "btn.colab_cells", "export"),

    # ---- Maintenance / recovery ----
    _spec("recovery.restore", "h_recovery_restore",
          "checkpoints.restore_and_reconcile", "btn.recover", "settings"),
    _spec("maintenance.checkpoint", "h_maintenance_checkpoint",
          "checkpoints.persist", "btn.checkpoint", "settings"),
)


_BY_ID = {s.action_id: s for s in ACTION_SPECS}


def get(action_id: str) -> ActionSpec | None:
    return _BY_ID.get(action_id)


def all_specs() -> tuple[ActionSpec, ...]:
    return ACTION_SPECS


def ready_specs() -> Iterator[ActionSpec]:
    return (s for s in ACTION_SPECS if s.ready)


def sections() -> tuple[str, ...]:
    seen: list[str] = []
    for spec in ACTION_SPECS:
        if spec.section not in seen:
            seen.append(spec.section)
    return tuple(seen)
