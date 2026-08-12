"""Binding proofs for the controls the M20 flow needs to render (M20-T04).

Each test replaces the declared service method with a recorder and asserts the
named handler really reached it. That is the exact claim ``proof_test`` makes —
nothing more. These are contract proofs, level "Fake-tested" in Constitution
section 11; they do NOT prove a live Telegram or Drive round-trip.
"""
from __future__ import annotations

from types import SimpleNamespace

from teledrive import action_registry

PROVES = ()


def _record(ctx, action_id: str, result=None):
    """Swap the declared service method for a recorder. Returns the call log."""
    spec = action_registry.get(action_id)
    assert spec is not None, action_id
    service_name, _, method_name = spec.service_path.partition(".")
    service = getattr(ctx, service_name)
    calls: list = []

    def recorder(*args, **kwargs):
        calls.append((args, kwargs))
        return result

    setattr(service, method_name, recorder)
    return calls


def _run(ctx, action_id: str, *args, result=None):
    calls = _record(ctx, action_id, result=result)
    spec = action_registry.get(action_id)
    handler = getattr(ctx.handlers, spec.handler_name)
    handler(*args)
    assert calls, f"{action_id} never reached {spec.service_path}"
    return calls


DRIVE_STATUS = SimpleNamespace(connected=True, state="CONNECTED", account_label="")
FOLDER = SimpleNamespace(id="folder-1", name="TeleDrive")


# ---- Drive: connection surface (contract level only, audit P0-6 stands) ----

def test_drive_connect_calls_the_declared_service(ctx):
    _run(ctx, "drive.connect", result=DRIVE_STATUS)


def test_drive_reconnect_calls_the_declared_service(ctx):
    _run(ctx, "drive.reconnect", result=DRIVE_STATUS)


def test_drive_status_calls_the_declared_service(ctx):
    _run(ctx, "drive.status", result=DRIVE_STATUS)


def test_drive_list_folders_passes_the_parent_id(ctx):
    calls = _run(ctx, "drive.list_folders", "root", result=[FOLDER])
    assert calls[0][0][0] == "root"


def test_drive_create_folder_passes_name_and_parent(ctx):
    calls = _run(ctx, "drive.create_folder", "Backup", "root", result=FOLDER)
    assert calls[0][0][0] == "Backup"
    assert calls[0][0][1] == "root"


def test_drive_select_folder_passes_the_bare_folder_id(ctx):
    calls = _run(ctx, "drive.select_folder", "TeleDrive :: folder-1", result=FOLDER)
    assert calls[0][0][0] == "folder-1"


# ---- Analyze ----

def test_analyze_run_passes_link_and_scope(ctx):
    scan = SimpleNamespace(total=0, total_bytes=0, scope="auto", rows=[])
    calls = _run(ctx, "analyze.run", "https://t.me/c/1/2", "auto", result=scan)
    assert calls[0][0][0] == "https://t.me/c/1/2"


def test_analyze_select_all_calls_the_declared_service(ctx):
    _run(ctx, "analyze.select_all", result=[])


def test_analyze_clear_selection_calls_the_declared_service(ctx):
    _run(ctx, "analyze.clear_selection", result=[])


# ---- Dashboard / logs ----

def test_dashboard_refresh_calls_the_declared_service(ctx):
    _run(ctx, "dashboard.refresh", result={})


def test_logs_refresh_calls_the_declared_service(ctx):
    _run(ctx, "logs.refresh", result="")


def test_logs_search_passes_the_query(ctx):
    calls = _run(ctx, "logs.search", "floodwait", result="")
    assert calls[0][0][0] == "floodwait"


def test_logs_download_calls_the_declared_service(ctx):
    _run(ctx, "logs.download", result="/tmp/logs.txt")


# ---- Settings ----

def test_settings_set_concurrency_reaches_the_service_with_the_slider_value(ctx):
    calls = _run(ctx, "settings.set_concurrency", 100,
                 result={"level": "100", "workers": 100, "cap": 100, "warn": True})
    assert calls[0][0][0] == 100


def test_settings_set_theme_calls_the_declared_service(ctx):
    calls = _run(ctx, "settings.set_theme", "light", result="light")
    assert calls[0][0][0] == "light"


# ---- Export / maintenance ----

def test_export_colab_cells_calls_the_declared_service(ctx):
    _run(ctx, "export.colab_cells", result="# cell 1")


def test_recovery_restore_calls_the_declared_service(ctx):
    _run(ctx, "recovery.restore",
         result={"imported": 0, "reconciled": {}, "message_key": "msg.recovery_none"})


def test_maintenance_checkpoint_calls_the_declared_service(ctx):
    _run(ctx, "maintenance.checkpoint",
         result={"local": "/tmp/cp", "drive_file_id": None, "at": "now"})
