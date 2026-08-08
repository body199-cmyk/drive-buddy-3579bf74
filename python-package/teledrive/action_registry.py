"""ACTION_SPECS — the single declaration of every visible control.

Constitution Section 4: a control may only be rendered when its spec exists,
its handler is named, its service_path resolves on the live context, and a test
proves the handler calls that exact service.

Constitution 4A.1 rules 2 and 3:

* ``implemented=True`` is set only in the commit that adds handler + service.
* ``tested=True`` is set only in the commit that adds the passing test, and it
  is **illegal without** ``proof_test`` naming that test (``__post_init__``
  raises ``ValueError``).

There is deliberately no ``ready=`` shortcut: a helper that flips both flags at
once turns the dead-control gate off, which is exactly the v2 failure mode.
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
    implemented: bool
    tested: bool
    proof_test: str = ""

    def __post_init__(self) -> None:
        if self.tested and not self.proof_test:
            raise ValueError(
                f"{self.action_id}: tested=True requires proof_test "
                "('tests/<file>.py::<function>')"
            )
        if self.tested and not self.implemented:
            raise ValueError(f"{self.action_id}: tested=True requires implemented=True")

    @property
    def ready(self) -> bool:
        return self.implemented and self.tested


ACTION_SPECS: tuple[ActionSpec, ...] = (
    # ---- Connection Center: Telegram ----
    ActionSpec(
        action_id="telegram.set_credentials",
        handler_name="h_telegram_set_credentials",
        service_path="telegram_auth.set_credentials",
        label_key="btn.connect_telegram",
        section="connection",
        implemented=True,
        tested=True,
        proof_test="tests/test_telegram_auth.py::test_happy_path_reuses_the_exact_phone_code_hash",
    ),
    ActionSpec(
        action_id="telegram.send_code",
        handler_name="h_telegram_send_code",
        service_path="telegram_auth.send_code",
        label_key="btn.send_code",
        section="connection",
        implemented=True,
        tested=True,
        proof_test="tests/test_telegram_auth.py::test_duplicate_send_code_click_is_idempotent",
    ),
    ActionSpec(
        action_id="telegram.resend_code",
        handler_name="h_telegram_resend_code",
        service_path="telegram_auth.resend_code",
        label_key="btn.resend_code",
        section="connection",
        implemented=True,
        tested=True,
        proof_test="tests/test_telegram_auth.py::test_resend_is_rate_limited",
    ),
    ActionSpec(
        action_id="telegram.verify_code",
        handler_name="h_telegram_verify_code",
        service_path="telegram_auth.verify_code",
        label_key="btn.verify",
        section="connection",
        implemented=True,
        tested=True,
        proof_test="tests/test_telegram_auth.py::test_wrong_code_keeps_the_hash_and_does_not_resend",
    ),
    ActionSpec(
        action_id="telegram.verify_password",
        handler_name="h_telegram_verify_password",
        service_path="telegram_auth.verify_password",
        label_key="btn.verify_password",
        section="connection",
        implemented=True,
        tested=True,
        proof_test="tests/test_telegram_auth.py::test_two_factor_uses_the_same_client_without_a_new_code",
    ),
    ActionSpec(
        action_id="telegram.logout",
        handler_name="h_telegram_logout",
        service_path="telegram_auth.logout",
        label_key="btn.logout",
        section="connection",
        implemented=True,
        tested=True,
        proof_test="tests/test_telegram_auth.py::test_logout_clears_all_secret_state",
    ),
    ActionSpec(
        action_id="telegram.status",
        handler_name="h_telegram_status",
        service_path="telegram_auth.status",
        label_key="dash.telegram_status",
        section="connection",
        implemented=True,
        tested=True,
        proof_test="tests/test_telegram_auth.py::test_status_never_exposes_the_full_phone",
    ),

    # ---- Connection Center: Google Drive (native Colab auth only) ----
    # No real-Drive test exists yet (audit P0-6): status() returns cached state
    # with no about().get() call, so none of these may claim tested=True.
    ActionSpec(
        action_id="drive.connect",
        handler_name="h_drive_connect",
        service_path="drive_auth.connect",
        label_key="btn.link_drive",
        section="connection",
        implemented=True,
        tested=False,
    ),
    ActionSpec(
        action_id="drive.reconnect",
        handler_name="h_drive_reconnect",
        service_path="drive_auth.reconnect",
        label_key="btn.drive_reconnect",
        section="connection",
        implemented=True,
        tested=False,
    ),
    ActionSpec(
        action_id="drive.status",
        handler_name="h_drive_status",
        service_path="drive_auth.status",
        label_key="dash.drive_status",
        section="connection",
        implemented=True,
        tested=False,
    ),
    ActionSpec(
        action_id="drive.list_folders",
        handler_name="h_drive_list_folders",
        service_path="drive_folders.list_children",
        label_key="btn.drive_list_folders",
        section="connection",
        implemented=True,
        tested=False,
    ),
    ActionSpec(
        action_id="drive.create_folder",
        handler_name="h_drive_create_folder",
        service_path="drive_folders.create",
        label_key="btn.drive_create_folder",
        section="connection",
        implemented=True,
        tested=False,
    ),
    ActionSpec(
        action_id="drive.select_folder",
        handler_name="h_drive_select_folder",
        service_path="drive_folders.select",
        label_key="btn.drive_select_folder",
        section="connection",
        implemented=True,
        tested=False,
    ),
    ActionSpec(
        action_id="drive.refresh_quota",
        handler_name="h_drive_refresh_quota",
        service_path="drive_quota.refresh",
        label_key="btn.refresh_quota",
        section="connection",
        implemented=True,
        tested=True,
        proof_test="tests/test_drive_quota.py::test_warn_90",
    ),

    # ---- Analyze ----
    ActionSpec(
        action_id="analyze.run",
        handler_name="h_analyze_run",
        service_path="scanner.analyze",
        label_key="btn.analyze",
        section="analyze",
        implemented=True,
        tested=False,
    ),
    ActionSpec(
        action_id="analyze.apply_filters",
        handler_name="h_analyze_apply_filters",
        service_path="selection.apply_filters",
        label_key="btn.apply_filters",
        section="analyze",
        implemented=True,
        tested=True,
        proof_test="tests/test_filters.py::test_by_type",
    ),
    ActionSpec(
        action_id="analyze.select_all",
        handler_name="h_analyze_select_all",
        service_path="selection.select_all_visible",
        label_key="btn.select_all",
        section="analyze",
        implemented=True,
        tested=True,
        proof_test="tests/test_selection.py::test_select_all_visible_only",
    ),
    ActionSpec(
        action_id="analyze.clear_selection",
        handler_name="h_analyze_clear_selection",
        service_path="selection.clear",
        label_key="btn.clear_selection",
        section="analyze",
        implemented=True,
        tested=True,
        proof_test="tests/test_selection.py::test_clear_selection_preserves_items_and_visible_rows",
    ),
    ActionSpec(
        action_id="analyze.enqueue_selected",
        handler_name="h_analyze_enqueue_selected",
        service_path="selection.enqueue_selected",
        label_key="btn.enqueue_selected",
        section="analyze",
        implemented=True,
        tested=True,
        proof_test="tests/test_queue.py::test_enqueue_and_deduplicate",
    ),

    # ---- Transfers ----
    # PHASE B proved the transfer pipeline (tests/test_transfer_manager.py) and
    # PHASE C proved the queue contract (tests/test_phase_c.py). Controls that
    # still lack a named proof stay tested=False.
    ActionSpec(
        action_id="queue.start_selected",
        handler_name="h_queue_start_selected",
        service_path="queue_manager.start_selected",
        label_key="btn.start",
        section="transfers",
        implemented=True,
        tested=True,
        proof_test="tests/test_phase_c.py::test_start_selected_never_processes_the_whole_table",
    ),
    ActionSpec(
        action_id="queue.pause",
        handler_name="h_queue_pause",
        service_path="queue_manager.pause",
        label_key="btn.pause",
        section="transfers",
        implemented=True,
        tested=True,
        proof_test="tests/test_phase_c.py::test_pause_exports_a_checkpoint_before_reporting_paused",
    ),
    ActionSpec(
        action_id="queue.resume",
        handler_name="h_queue_resume",
        service_path="queue_manager.resume",
        label_key="btn.resume",
        section="transfers",
        implemented=True,
        tested=True,
        proof_test="tests/test_phase_3.py::test_resume_clears_the_pause_gate_on_the_owned_manager",
    ),
    ActionSpec(
        action_id="queue.stop",
        handler_name="h_queue_stop",
        service_path="queue_manager.stop",
        label_key="btn.stop",
        section="transfers",
        implemented=True,
        tested=True,
        proof_test="tests/test_phase_3.py::test_stop_sets_the_manager_stop_flag_and_reports_stopped",
    ),
    ActionSpec(
        action_id="queue.retry_failed",
        handler_name="h_queue_retry_failed",
        service_path="queue_manager.retry_failed",
        label_key="btn.retry_failed",
        section="transfers",
        implemented=True,
        tested=True,
        proof_test="tests/test_phase_c.py::test_retry_failed_never_revives_a_stopped_item",
    ),

    ActionSpec(
        action_id="queue.clear_completed",
        handler_name="h_queue_clear_completed",
        service_path="queue_manager.clear_completed_metadata",
        label_key="btn.clear_completed",
        section="transfers",
        implemented=True,
        tested=True,
        proof_test="tests/test_phase_3.py::test_clear_completed_removes_finished_rows_only",
    ),
    ActionSpec(
        action_id="queue.refresh",
        handler_name="h_queue_refresh",
        service_path="queue_manager.snapshot",
        label_key="btn.refresh",
        section="transfers",
        implemented=True,
        tested=True,
        proof_test="tests/test_phase_3.py::test_refresh_snapshot_reports_live_counts",
    ),
    ActionSpec(
        action_id="queue.pause_item",
        handler_name="h_queue_pause_item",
        service_path="queue_manager.pause_item",
        label_key="btn.pause_item",
        section="transfers",
        implemented=True,
        tested=True,
        proof_test="tests/test_phase_3.py::test_pause_item_marks_an_in_flight_item_paused",
    ),
    ActionSpec(
        action_id="queue.resume_item",
        handler_name="h_queue_resume_item",
        service_path="queue_manager.resume_item",
        label_key="btn.resume_item",
        section="transfers",
        implemented=True,
        tested=True,
        proof_test="tests/test_phase_3.py::test_pause_item_and_resume_item_only_touch_that_item",
    ),
    ActionSpec(
        action_id="queue.stop_item",
        handler_name="h_queue_stop_item",
        service_path="queue_manager.stop_item",
        label_key="btn.stop_item",
        section="transfers",
        implemented=True,
        tested=True,
        proof_test="tests/test_phase_3.py::test_stop_item_is_permanent_for_that_item",
    ),
    ActionSpec(
        action_id="queue.retry_item",
        handler_name="h_queue_retry_item",
        service_path="queue_manager.retry_item",
        label_key="btn.retry_item",
        section="transfers",
        implemented=True,
        tested=True,
        proof_test="tests/test_phase_3.py::test_retry_item_returns_a_failed_item_to_pending",
    ),

    # ---- Dashboard ----
    ActionSpec(
        action_id="dashboard.refresh",
        handler_name="h_dashboard_refresh",
        service_path="stats.dashboard",
        label_key="btn.refresh",
        section="dashboard",
        implemented=True,
        tested=False,
    ),

    # ---- Logs ----
    ActionSpec(
        action_id="logs.refresh",
        handler_name="h_logs_refresh",
        service_path="log_service.tail",
        label_key="btn.refresh",
        section="logs",
        implemented=True,
        tested=False,
    ),
    ActionSpec(
        action_id="logs.search",
        handler_name="h_logs_search",
        service_path="log_service.search",
        label_key="btn.search_logs",
        section="logs",
        implemented=True,
        tested=False,
    ),
    ActionSpec(
        action_id="logs.download",
        handler_name="h_logs_download",
        service_path="log_service.export_file",
        label_key="btn.download_logs",
        section="logs",
        implemented=True,
        tested=False,
    ),

    # ---- Settings ----
    ActionSpec(
        action_id="settings.set_concurrency",
        handler_name="h_settings_set_concurrency",
        service_path="settings.set_concurrency",
        label_key="form.concurrency",
        section="settings",
        implemented=True,
        tested=False,
    ),
    ActionSpec(
        action_id="settings.toggle_language",
        handler_name="h_settings_toggle_language",
        service_path="preferences.toggle_language",
        label_key="btn.language",
        section="settings",
        implemented=True,
        tested=True,
        proof_test="tests/test_i18n.py::test_toggle",
    ),
    ActionSpec(
        action_id="settings.set_theme",
        handler_name="h_settings_set_theme",
        service_path="preferences.set_theme",
        label_key="btn.theme",
        section="settings",
        implemented=True,
        tested=False,
    ),

    # ---- Colab code / export ----
    ActionSpec(
        action_id="export.build_zip",
        handler_name="h_export_build_zip",
        service_path="package_service.build_tested_archive",
        label_key="btn.build_zip",
        section="export",
        implemented=True,
        tested=False,
    ),
    ActionSpec(
        action_id="export.colab_cells",
        handler_name="h_export_colab_cells",
        service_path="colab_export.cells_text",
        label_key="btn.colab_cells",
        section="export",
        implemented=True,
        tested=False,
    ),

    # ---- Maintenance / recovery ----
    ActionSpec(
        action_id="recovery.restore",
        handler_name="h_recovery_restore",
        service_path="checkpoints.restore_and_reconcile",
        label_key="btn.recover",
        section="settings",
        implemented=True,
        tested=False,
    ),
    ActionSpec(
        action_id="maintenance.checkpoint",
        handler_name="h_maintenance_checkpoint",
        service_path="checkpoints.persist",
        label_key="btn.checkpoint",
        section="settings",
        implemented=True,
        tested=False,
    ),
)


_BY_ID = {s.action_id: s for s in ACTION_SPECS}


def get(action_id: str) -> ActionSpec | None:
    return _BY_ID.get(action_id)


def all_specs() -> tuple[ActionSpec, ...]:
    return ACTION_SPECS


def ready_specs() -> Iterator[ActionSpec]:
    return (s for s in ACTION_SPECS if s.ready)


def unready_specs() -> Iterator[ActionSpec]:
    return (s for s in ACTION_SPECS if not s.ready)


def sections() -> tuple[str, ...]:
    seen: list[str] = []
    for spec in ACTION_SPECS:
        if spec.section not in seen:
            seen.append(spec.section)
    return tuple(seen)
