"""ADR-0001: concurrency slider 1..100, default 2, warning above 8.

Supersedes the M17-T03 "1..4" contract. The cap moved on explicit owner
instruction; everything else about the gate is unchanged — out-of-range and
non-numeric input is still REFUSED with a localized error and the slider still
returns to its last good value, so the UI can never show a worker count the
engine is not really using.
"""
from __future__ import annotations

import pytest

from teledrive import action_registry
from teledrive.config import (
    CONCURRENCY_WARN_ABOVE,
    DEFAULT_CONCURRENCY,
    HARD_CONCURRENCY_CAP,
)
from teledrive.i18n import t

PROVES = ("settings.set_concurrency",)


def _invoke(ctx, value):
    return ctx.handlers.h_settings_set_concurrency(value)


def test_one_and_four_accepted_out_of_range_rejected(ctx):
    """settings.set_concurrency accepts 1..100, rejects 0/101/text.

    The historical name is kept because it is the registry's ``proof_test``
    for this action; the range it proves is now the ADR-0001 one.
    """
    ctx.config.manual_concurrency = DEFAULT_CONCURRENCY
    # 1 accepted
    val_update, msg = _invoke(ctx, 1)
    assert val_update["value"] == 1
    assert "✅" in msg
    assert ctx.config.concurrency_value() == 1
    # 4 accepted (the old cap is now an ordinary value)
    val_update, msg = _invoke(ctx, 4)
    assert val_update["value"] == 4
    assert ctx.config.concurrency_value() == 4
    # the new cap is accepted end to end
    val_update, msg = _invoke(ctx, HARD_CONCURRENCY_CAP)
    assert val_update["value"] == HARD_CONCURRENCY_CAP
    assert ctx.config.concurrency_value() == HARD_CONCURRENCY_CAP
    # 0 rejected: slider returns to last good value
    val_update, msg = _invoke(ctx, 0)
    assert val_update["value"] == HARD_CONCURRENCY_CAP
    assert "⚠️" in msg
    # cap + 1 rejected — never silently clamped
    val_update, msg = _invoke(ctx, HARD_CONCURRENCY_CAP + 1)
    assert val_update["value"] == HARD_CONCURRENCY_CAP
    assert "⚠️" in msg
    # "abc" rejected (invalid)
    val_update, msg = _invoke(ctx, "abc")
    assert val_update["value"] == HARD_CONCURRENCY_CAP
    assert "⚠️" in msg


def test_named_levels_map_into_cap(ctx):
    """Named levels safe/balanced/fast/turbo/max map into 1..100."""
    for name, expected in (("safe", 1), ("balanced", 2), ("fast", 3),
                           ("turbo", 16), ("max", 100)):
        val_update, msg = _invoke(ctx, name)
        assert val_update["value"] == expected, name
        assert ctx.config.concurrency_value() == expected <= HARD_CONCURRENCY_CAP


def test_value_persists_and_round_trips(ctx):
    """Saved value is applied to queue_manager and readable on next render."""
    _invoke(ctx, 3)
    assert ctx.settings.current() == 3
    assert ctx.config.concurrency_value() == 3


def test_high_values_are_allowed_but_carry_the_risk_warning(ctx):
    """ADR-0001: above 8 the value is honoured AND the risk is stated."""
    _val, msg = _invoke(ctx, CONCURRENCY_WARN_ABOVE)
    assert t("warn.concurrency_high") not in msg
    val_update, msg = _invoke(ctx, CONCURRENCY_WARN_ABOVE + 1)
    assert val_update["value"] == CONCURRENCY_WARN_ABOVE + 1
    assert "✅" in msg
    assert t("warn.concurrency_high") in msg
    assert ctx.config.concurrency_value() == CONCURRENCY_WARN_ABOVE + 1


def test_the_service_reports_the_real_cap_and_warn_flag(ctx):
    result = ctx.settings.set_concurrency(50)
    assert result == {"level": 50, "workers": 50, "cap": HARD_CONCURRENCY_CAP,
                      "warn": True}
    assert ctx.settings.set_concurrency(2)["warn"] is False
