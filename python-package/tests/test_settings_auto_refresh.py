"""M44-T01: persisted React auto-refresh preference.

The browser heartbeat was hard-wired to one second. The owner asked for an
explicit off switch, so the interval is now a persisted Python setting read by
the live snapshot. These tests prove the persistence, the snapshot contract,
and the handler's refusal path without inventing a browser-side value.
"""
from __future__ import annotations

import pytest

from teledrive import database as db
from teledrive.errors import TeleDriveError

PROVES = ("settings.set_auto_refresh",)


def test_set_auto_refresh_persists_and_snapshot_reports_it(ctx):
    # Default preserves the previous behaviour exactly.
    assert ctx.settings.auto_refresh_ms() == 1000
    assert ctx.handlers.live_ui_state.snapshot()["autoRefreshMs"] == 1000

    result = ctx.settings.set_auto_refresh(0)
    assert result == {
        "auto_refresh_ms": 0,
        "enabled": False,
        "options": [0, 1000, 2000, 5000],
    }
    assert db.get_setting("auto_refresh_ms") == "0"
    assert ctx.handlers.live_ui_state.snapshot()["autoRefreshMs"] == 0

    ctx.settings.set_auto_refresh(2000)
    assert db.get_setting("auto_refresh_ms") == "2000"
    assert ctx.handlers.live_ui_state.snapshot()["autoRefreshMs"] == 2000


def test_invalid_auto_refresh_values_are_rejected_not_clamped(ctx):
    for value in (-1, 1500, 60000, "fast", True, None):
        with pytest.raises(TeleDriveError):
            ctx.settings.set_auto_refresh(value)
    # A rejected value never reaches SQLite and never changes the live value.
    assert ctx.settings.auto_refresh_ms() == 1000
    assert db.get_setting("auto_refresh_ms") == ""


def test_handler_rejects_an_invalid_value_without_calling_the_service(ctx):
    calls: list[tuple] = []
    original = ctx.settings.set_auto_refresh

    def spy(*args, **kwargs):
        calls.append(args)
        return original(*args, **kwargs)

    ctx.settings.set_auto_refresh = spy
    try:
        value_update, status = ctx.handlers.h_settings_set_auto_refresh(1500)
    finally:
        del ctx.settings.set_auto_refresh

    assert calls == []
    assert value_update["value"] == 1000
    assert status.startswith("⚠️")
    assert ctx.settings.auto_refresh_ms() == 1000


def test_saved_value_is_restored_on_a_new_settings_service(ctx):
    ctx.settings.set_auto_refresh(5000)

    from teledrive.services import SettingsService

    restored = SettingsService(ctx)
    assert restored.auto_refresh_ms() == 5000
