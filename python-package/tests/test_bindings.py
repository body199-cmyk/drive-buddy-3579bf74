"""Binding contract: every declared action resolves, every handler is named,
and the layout wires every ready action exactly once.

The old `test_all_specs_are_implemented_and_tested` was deleted: it asserted the
opposite of Constitution 4A.1 (it forced every spec to claim ready). The proof
gate now lives in tests/test_action_proofs.py.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from teledrive import action_registry
from teledrive.errors import DeadControlError, IncompleteBindingError, UnknownActionError
from teledrive.ui_binder import UIBinder

UI_SOURCE = Path(__file__).resolve().parents[1] / "teledrive" / "ui.py"


class FakeComponent:
    def __init__(self):
        self.bound = []

    def click(self, fn, inputs, outputs):
        self.bound.append(("click", fn, inputs, outputs))

    def change(self, fn, inputs, outputs):
        self.bound.append(("change", fn, inputs, outputs))


class FakeGradio:
    """Minimal gr stand-in for the binder's button factory."""

    class Button(FakeComponent):
        def __init__(self, value="", **kwargs):
            super().__init__()
            self.value = value
            self.interactive = kwargs.get("interactive", True)
            self.visible = kwargs.get("visible", True)


def test_every_spec_resolves_on_the_live_context(ctx):
    for spec in action_registry.ACTION_SPECS:
        assert callable(ctx.resolve(spec.service_path)), spec.action_id


def test_every_spec_has_a_named_decorated_handler(ctx):
    for spec in action_registry.ACTION_SPECS:
        handler = getattr(ctx.handlers, spec.handler_name, None)
        assert callable(handler), spec.handler_name
        assert handler.action_id == spec.action_id
        assert handler.service_path == spec.service_path


def test_wire_rejects_unknown_action(ctx):
    binder = UIBinder(ctx, ctx.handlers)
    with pytest.raises(UnknownActionError):
        binder.wire(FakeComponent(), "does.not.exist")


def test_wire_rejects_not_ready_action(ctx):
    unready = next(action_registry.unready_specs())
    binder = UIBinder(ctx, ctx.handlers)
    with pytest.raises(DeadControlError):
        binder.wire(FakeComponent(), unready.action_id)


def test_wire_if_ready_skips_an_unready_action_but_still_rejects_unknown(ctx):
    unready = next(action_registry.unready_specs())
    binder = UIBinder(ctx, ctx.handlers)
    assert binder.wire_if_ready(FakeComponent(), unready.action_id) is None
    assert binder.wired == {}
    with pytest.raises(UnknownActionError):
        binder.wire_if_ready(FakeComponent(), "does.not.exist")


def test_button_factory_hides_and_disables_unready_controls(ctx):
    binder = UIBinder(ctx, ctx.handlers)
    unready = next(action_registry.unready_specs())
    button = binder.button(FakeGradio, unready.action_id)
    assert button.interactive is False
    assert button.visible is False
    assert unready.action_id in binder.disabled
    assert unready.action_id not in binder.wired


def test_button_factory_renders_ready_controls_normally(ctx):
    binder = UIBinder(ctx, ctx.handlers)
    ready = next(action_registry.ready_specs())
    button = binder.button(FakeGradio, ready.action_id)
    assert button.interactive is True
    assert button.visible is True
    assert ready.action_id not in binder.disabled


def test_assert_complete_fails_when_an_action_is_unwired(ctx):
    binder = UIBinder(ctx, ctx.handlers)
    with pytest.raises(IncompleteBindingError):
        binder.assert_complete()


def test_assert_complete_detects_an_orphan_rendered_control(ctx):
    binder = UIBinder(ctx, ctx.handlers)
    for spec in action_registry.ready_specs():
        binder.wire(FakeComponent(), spec.action_id)
    orphan = next(action_registry.ready_specs())
    binder.wired.pop(orphan.action_id)
    binder.rendered[orphan.action_id] = FakeComponent()
    with pytest.raises(IncompleteBindingError):
        binder.assert_complete()


def test_wiring_every_ready_action_satisfies_assert_complete(ctx):
    binder = UIBinder(ctx, ctx.handlers)
    for spec in action_registry.ready_specs():
        binder.wire(FakeComponent(), spec.action_id)
    binder.assert_complete()
    assert len(binder.inventory()) == len(list(action_registry.ready_specs()))


def test_ui_module_renders_every_declared_action():
    text = UI_SOURCE.read_text(encoding="utf-8")
    rendered = set(re.findall(r'binder\.(?:button\(gr|is_ready\(),?\s*"([^"]+)"', text))
    rendered |= set(re.findall(r'binder\.is_ready\("([^"]+)"\)', text))
    declared = {s.action_id for s in action_registry.ACTION_SPECS}
    assert declared - rendered == set()


def test_ui_module_wires_exactly_the_ready_actions():
    text = UI_SOURCE.read_text(encoding="utf-8")
    wired = set(re.findall(r'binder\.wire_if_ready\(\s*[^,]+,\s*"([^"]+)"', text))
    declared = {s.action_id for s in action_registry.ACTION_SPECS}
    assert wired == declared, "every declared action must go through wire_if_ready"
    assert "binder.wire(" not in text.replace("binder.wire_if_ready(", "")


def test_wire_rejects_an_unresolvable_service_path(ctx, monkeypatch):
    """A ready spec whose service vanished must fail the build, not render."""
    from teledrive.errors import ServicePathError

    spec = next(iter(action_registry.ready_specs()))
    service_name = spec.service_path.partition(".")[0]
    monkeypatch.setattr(ctx, service_name, None, raising=False)
    binder = UIBinder(ctx, ctx.handlers)
    with pytest.raises(ServicePathError):
        binder.wire(FakeComponent(), spec.action_id)
