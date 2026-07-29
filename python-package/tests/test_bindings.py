"""Binding contract: every declared action resolves, every handler is named,
and the layout wires every ready action exactly once."""
from __future__ import annotations

import pytest

from teledrive import action_registry
from teledrive.errors import DeadControlError, IncompleteBindingError, UnknownActionError
from teledrive.ui_binder import UIBinder


class FakeComponent:
    def __init__(self):
        self.bound = []

    def click(self, fn, inputs, outputs):
        self.bound.append(("click", fn, inputs, outputs))

    def change(self, fn, inputs, outputs):
        self.bound.append(("change", fn, inputs, outputs))


def test_every_spec_resolves_on_the_live_context(ctx):
    for spec in action_registry.ACTION_SPECS:
        assert callable(ctx.resolve(spec.service_path)), spec.action_id


def test_every_spec_has_a_named_decorated_handler(ctx):
    for spec in action_registry.ACTION_SPECS:
        handler = getattr(ctx.handlers, spec.handler_name, None)
        assert callable(handler), spec.handler_name
        assert handler.action_id == spec.action_id
        assert handler.service_path == spec.service_path


def test_all_specs_are_implemented_and_tested():
    not_ready = [s.action_id for s in action_registry.ACTION_SPECS if not s.ready]
    assert not_ready == []


def test_wire_rejects_unknown_action(ctx):
    binder = UIBinder(ctx, ctx.handlers)
    with pytest.raises(UnknownActionError):
        binder.wire(FakeComponent(), "does.not.exist")


def test_wire_rejects_not_ready_action(ctx, monkeypatch):
    spec = action_registry.ACTION_SPECS[0]
    dead = action_registry.ActionSpec(
        action_id=spec.action_id, handler_name=spec.handler_name,
        service_path=spec.service_path, label_key=spec.label_key,
        section=spec.section, implemented=True, tested=False,
    )
    monkeypatch.setitem(action_registry._BY_ID, spec.action_id, dead)
    binder = UIBinder(ctx, ctx.handlers)
    with pytest.raises(DeadControlError):
        binder.wire(FakeComponent(), spec.action_id)


def test_assert_complete_fails_when_an_action_is_unwired(ctx):
    binder = UIBinder(ctx, ctx.handlers)
    with pytest.raises(IncompleteBindingError):
        binder.assert_complete()


def test_wiring_every_ready_action_satisfies_assert_complete(ctx):
    binder = UIBinder(ctx, ctx.handlers)
    for spec in action_registry.ready_specs():
        binder.wire(FakeComponent(), spec.action_id)
    binder.assert_complete()
    assert len(binder.inventory()) == len(action_registry.ACTION_SPECS)


def test_ui_module_wires_the_same_set_of_actions():
    import re
    from pathlib import Path

    source = Path(__file__).resolve().parents[1] / "teledrive" / "ui.py"
    text = source.read_text(encoding="utf-8")
    wired = set(re.findall(r'binder\.wire\([^,]+,\s*"([^"]+)"', text))
    declared = {s.action_id for s in action_registry.ready_specs()}
    assert wired == declared
