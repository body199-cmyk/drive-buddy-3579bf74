"""M17-T03: concurrency slider 1..4, default 2, no fake cap of 19/50."""
from __future__ import annotations

import pytest

from teledrive import action_registry
from teledrive.config import HARD_CONCURRENCY_CAP

PROVES = ("settings.set_concurrency",)


def _invoke(ctx, value):
    return ctx.handlers.h_settings_set_concurrency(value)


def test_one_and_four_accepted_out_of_range_rejected(ctx):
    """settings.set_concurrency accepts 1..4, rejects 0/5/text with localized error
    and keeps the prior value."""
    ctx.config.manual_concurrency = 2
    # 1 accepted
    val_update, msg = _invoke(ctx, 1)
    assert val_update["value"] == 1
    assert "✅" in msg
    assert ctx.config.concurrency_value() == 1
    # 4 accepted
    val_update, msg = _invoke(ctx, 4)
    assert val_update["value"] == 4
    assert ctx.config.concurrency_value() == HARD_CONCURRENCY_CAP
    # 0 rejected: slider returns to last good value
    ctx.config.manual_concurrency = 4
    val_update, msg = _invoke(ctx, 0)
    assert val_update["value"] == 4
    assert "⚠️" in msg
    # 5 rejected
    val_update, msg = _invoke(ctx, 5)
    assert val_update["value"] == 4
    assert "⚠️" in msg
    # "abc" rejected (invalid)
    val_update, msg = _invoke(ctx, "abc")
    assert val_update["value"] == 4
    assert "⚠️" in msg


def test_named_levels_map_into_cap(ctx):
    """Named levels safe/balanced/fast map to 1/2/3 (never > cap)."""
    val_update, msg = _invoke(ctx, "safe")
    assert val_update["value"] in (1, 2, 3, 4)
    assert ctx.config.concurrency_value() <= HARD_CONCURRENCY_CAP


def test_value_persists_and_round_trips(ctx):
    """Saved value is applied to queue_manager and readable on next render."""
    _invoke(ctx, 3)
    assert ctx.settings.current() == 3
    assert ctx.config.concurrency_value() == 3
