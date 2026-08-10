"""M15-T04 — Drive readiness gate: Connected is impossible before about().get().

M17-T02 extension: the same fake-factory harness now also proves the four
connection-side Drive ACTIONS at the handler level (connect / reconnect /
status / refresh_quota), which flips their registry specs to tested=True with
named proof tests. What these tests still do NOT prove is the live native
Colab flow (owner-side, M15-T01) — no fake test ever claims that.
"""
from __future__ import annotations

import pytest

from teledrive import action_registry
from teledrive.drive_auth import (
    ABOUT_FIELDS,
    CONNECTED,
    DISCONNECTED,
    ERROR,
    DriveAuth,
)
from teledrive.errors import TeleDriveError
from teledrive.handlers import ERROR_ARITY
from teledrive.i18n import t

# Actions proven by this module (see teledrive/action_registry.proof_test):
# handler-level proofs below run a FAKE Drive service through the REAL gate.
PROVES = (
    "drive.connect",
    "drive.reconnect",
    "drive.status",
    "drive.refresh_quota",
)

#: the seven Drive actions M17-T02 exposes; folder actions are proven in
#: tests/test_drive_folders.py.
DRIVE_ACTIONS = (
    "drive.connect",
    "drive.reconnect",
    "drive.status",
    "drive.list_folders",
    "drive.create_folder",
    "drive.select_folder",
    "drive.refresh_quota",
)


class _AboutRequest:
    def __init__(self, parent):
        self.parent = parent

    def execute(self):
        self.parent.executed.append("about.get")
        if self.parent.fail_about:
            raise RuntimeError("drive is unreachable")
        return {
            "user": {"emailAddress": "user@example.com", "displayName": "User"},
            "storageQuota": {"limit": "100", "usage": "40"},
        }


class _AboutService:
    def __init__(self, fail_about: bool = False):
        self.fail_about = fail_about
        self.executed: list[str] = []

    def about(self):
        parent = self

        class _Get:
            def get(self, fields=None):
                assert fields == ABOUT_FIELDS
                return _AboutRequest(parent)

        return _Get()


def test_fresh_drive_auth_is_honestly_disconnected(ctx):
    drive = DriveAuth(ctx, service_factory=lambda: _AboutService())
    status = drive.status()
    assert status.state == DISCONNECTED
    assert status.connected is False
    assert drive.connected is False


def test_connected_only_after_about_get_executes(ctx):
    service = _AboutService()
    drive = DriveAuth(ctx, service_factory=lambda: service)
    assert service.executed == []  # nothing contacted Drive at construction

    status = drive.connect()

    assert service.executed == ["about.get"], "about().get() must run before CONNECTED"
    assert status.state == CONNECTED
    assert drive.connected is True
    assert status.account_label == "user@example.com"
    assert drive.quota == {"limit": 100, "usage": 40}


def test_failed_about_get_never_reports_connected(ctx):
    service = _AboutService(fail_about=True)
    drive = DriveAuth(ctx, service_factory=lambda: service)
    with pytest.raises(TeleDriveError) as excinfo:
        drive.connect()
    assert excinfo.value.message_key == "err.drive_auth_failed"
    assert service.executed == ["about.get"]
    assert drive.state == ERROR
    assert drive.connected is False
    assert drive.service is None
    assert drive.status().connected is False


def test_reconnect_clears_state_and_reruns_the_gate(ctx):
    service = _AboutService()
    drive = DriveAuth(ctx, service_factory=lambda: service)
    drive.connect()
    assert drive.connected is True

    drive._factory = lambda: _AboutService(fail_about=True)
    with pytest.raises(TeleDriveError):
        drive.reconnect()
    assert drive.connected is False
    assert drive.state == ERROR
    assert drive.service is None


# ---------------------------------------------------------------------------
# M17-T02 — handler-level action proofs (fake factory, REAL Handlers wiring)
# ---------------------------------------------------------------------------


def _fake_drive(ctx, fail_about: bool = False):
    """Swap the context's DriveAuth for one backed by a controllable fake."""
    service = _AboutService(fail_about=fail_about)
    drive = DriveAuth(ctx, service_factory=lambda: service)
    ctx.drive_auth = drive
    return drive, service


def test_connect_action_reports_connected_only_after_about_get(ctx):
    drive, service = _fake_drive(ctx)
    assert service.executed == [], "UI must not contact Drive before the click"

    out = ctx.handlers.h_drive_connect()

    assert ctx.handlers.h_drive_connect.action_id == "drive.connect"
    assert isinstance(out, tuple) and len(out) == 2
    detail, label = out
    assert service.executed == ["about.get"], "Connected before about().get() is forbidden"
    assert label == t("status.connected")
    assert "user@example.com" in detail
    assert drive.state == CONNECTED and drive.connected is True


def test_connect_action_failure_returns_localized_error_and_stays_disconnected(ctx):
    drive, service = _fake_drive(ctx, fail_about=True)

    out = ctx.handlers.h_drive_connect()

    assert isinstance(out, tuple) and len(out) == 2
    message, chip = out
    assert chip is None
    assert service.executed == ["about.get"]
    assert drive.state == ERROR and drive.connected is False and drive.service is None
    assert t("err.drive_auth_failed") in message
    assert t("err.unknown") not in message
    assert "Traceback" not in message and "api_hash" not in message


def test_reconnect_action_clears_stale_service_and_auth_state(ctx):
    drive, old_service = _fake_drive(ctx)
    ctx.handlers.h_drive_connect()
    assert drive.service is old_service
    assert ctx.auth.state.drive_authorized is True

    # Failure path: the stale service must be dropped BEFORE the new attempt.
    drive._factory = lambda: _AboutService(fail_about=True)
    assert ctx.handlers.h_drive_reconnect.action_id == "drive.reconnect"
    out = ctx.handlers.h_drive_reconnect()
    assert isinstance(out, tuple) and len(out) == 2
    message, chip = out
    assert chip is None
    assert t("err.drive_auth_failed") in message
    assert drive.service is None
    assert drive.state == ERROR
    assert drive.account_label == "" and drive.quota == {}
    assert ctx.auth.drive is None and ctx.auth.state.drive_authorized is False

    # Success path: a fresh native service fully replaces the old one.
    drive2, old2 = _fake_drive(ctx)
    ctx.handlers.h_drive_connect()
    replacement = _AboutService()
    drive2._factory = lambda: replacement
    detail, label = ctx.handlers.h_drive_reconnect()
    assert drive2.service is replacement and drive2.service is not old2
    assert drive2.state == CONNECTED and drive2.connected is True
    assert label == t("status.connected")
    assert replacement.executed == ["about.get"], "reconnect must re-run the gate"


def test_status_action_is_read_only_and_never_calls_the_service(ctx):
    drive, service = _fake_drive(ctx)
    ctx.handlers.h_drive_connect()
    service.executed.clear()

    assert ctx.handlers.h_drive_status.action_id == "drive.status"
    first = ctx.handlers.h_drive_status()
    second = ctx.handlers.h_drive_status()

    assert isinstance(first, tuple) and len(first) == 2
    assert first == second, "status must be a pure read of cached state"
    assert service.executed == [], "status must never call the Drive API"
    assert first[1] == t("status.connected")
    assert "Traceback" not in str(first)


def test_refresh_quota_action_maps_the_real_storage_quota_shape(ctx):
    drive, service = _fake_drive(ctx)  # fake about reports limit=100, usage=40
    ctx.handlers.h_drive_connect()

    assert ctx.handlers.h_drive_refresh_quota.action_id == "drive.refresh_quota"
    out = ctx.handlers.h_drive_refresh_quota()

    assert isinstance(out, tuple) and len(out) == 2
    line, payload = out
    assert payload["limit"] == 100 and payload["usage"] == 40
    assert payload["free"] == 60 and payload["warn"] is False
    assert isinstance(payload["ratio_used"], float)
    assert payload["label"]

    # And it stays honest when Drive is not connected at all.
    ctx.drive_auth = DriveAuth(ctx, service_factory=lambda: _AboutService())
    message, payload = ctx.handlers.h_drive_refresh_quota()
    assert payload is None
    assert t("err.drive_not_ready") in message
    assert t("status.connected") not in message


def test_all_seven_drive_actions_resolve_from_the_context(ctx):
    for action_id in DRIVE_ACTIONS:
        spec = action_registry.get(action_id)
        assert spec is not None, action_id
        assert callable(ctx.resolve(spec.service_path)), spec.service_path
        handler = getattr(ctx.handlers, spec.handler_name)
        assert handler.action_id == action_id
        assert handler.service_path == spec.service_path


def test_drive_handler_output_arities_match_the_folder_sync_contract():
    for action_id in DRIVE_ACTIONS:
        expected = 3 if action_id in {"drive.create_folder", "drive.select_folder"} else 2
        assert ERROR_ARITY.get(action_id) == expected, action_id


def test_arabic_and_english_labels_exist_for_all_seven_drive_actions():
    from teledrive.i18n import load

    ar, en = load("ar"), load("en")
    for action_id in DRIVE_ACTIONS:
        key = action_registry.get(action_id).label_key
        assert ar.get(key, key) != key, (action_id, key, "ar")
        assert en.get(key, key) != key, (action_id, key, "en")
