"""M15-T04 — Drive readiness gate: Connected is impossible before about().get().

These tests prove the Colab Drive gate with fake service objects only. They do
NOT flip any registry flag: the drive.* specs stay tested=False until a real
owner-run Colab session proves them. What is proven here is the contract the
UI depends on — no code path may report CONNECTED without a successful
``about().get()`` round-trip, and a failing round-trip must surface as an
honest ERROR with no service retained.
"""
from __future__ import annotations

import pytest

from teledrive.drive_auth import (
    ABOUT_FIELDS,
    CONNECTED,
    DISCONNECTED,
    ERROR,
    DriveAuth,
)
from teledrive.errors import TeleDriveError

# Actions proven by this module (see teledrive/action_registry.proof_test): none —
# this file guards the gate the UI relies on; it flips no registry flags.
PROVES: tuple = ()


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
