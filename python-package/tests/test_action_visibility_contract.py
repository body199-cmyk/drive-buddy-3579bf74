"""M17-T03: every action is either (ready + wired) or visible-disabled with
a localized reason. Silent hiding is forbidden (KNOWN_ISSUES #28)."""
from __future__ import annotations

import pytest

from teledrive import action_registry
from teledrive.i18n import keyset


PROVES = ()


def test_all_tested_actions_have_proof_and_no_blocked_reason():
    for spec in action_registry.ACTION_SPECS:
        if spec.tested:
            assert spec.proof_test, f"{spec.action_id}: tested=True requires proof_test"
            assert spec.blocked_reason_key is None, (
                f"{spec.action_id}: tested action must not carry blocked_reason_key"
            )


def test_unready_actions_carry_localized_reason_in_both_languages():
    ar = keyset("ar")
    en = keyset("en")
    for spec in action_registry.ACTION_SPECS:
        if spec.tested:
            continue
        assert spec.blocked_reason_key, (
            f"{spec.action_id}: silent hiding forbidden (KNOWN_ISSUES #28)"
        )
        assert spec.blocked_reason_key in ar, \
            f"{spec.action_id}: ar locale missing key {spec.blocked_reason_key}"
        assert spec.blocked_reason_key in en, \
            f"{spec.action_id}: en locale missing key {spec.blocked_reason_key}"


def test_registry_assert_complete_passes():
    # With all specs either tested or carrying a localized reason, this must
    # NOT raise.
    action_registry.assert_complete()


def test_unready_without_reason_is_rejected():
    from teledrive.action_registry import ActionSpec, RegistryError, assert_complete
    # Temporarily inject a bad spec — impossible since ACTION_SPECS is a tuple
    # and frozen dataclass; instead verify the function raises on broken state
    # by monkeypatching all_specs().
    import teledrive.action_registry as ar_mod
    bad = ActionSpec(
        action_id="__bad__.x", handler_name="h", service_path="a.b",
        label_key="btn.refresh", section="settings",
        implemented=True, tested=False,
        blocked_reason_key=None,
    )
    original = ar_mod.ACTION_SPECS
    ar_mod.ACTION_SPECS = original + (bad,)
    try:
        with pytest.raises(RegistryError):
            assert_complete()
    finally:
        ar_mod.ACTION_SPECS = original
