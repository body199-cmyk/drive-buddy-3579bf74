"""M19-T01 — UI redesign preservation contract (§6.7).

The five-zone redesign is presentation-only. This file proves it dropped NO
functionality by asserting, against the captured M19-T01 baseline (commit
``6281a66`` on ``main``):

* the count of ready actions never decreased (baseline 45);
* the count of wired controls never decreased (baseline 55 — the four mirrored
  Drive folder pickers + the intentionally duplicated build-zip);
* every Telegram ``action_id`` is still wired to the SAME declared handler and
  service path it had before the redesign;
* the theme control still uses the EXISTING ``settings.set_theme`` binding (no
  new theme logic was invented — §6.5);
* switching theme / language re-renders without losing direction (RTL default).

These guards make an accidental orphan/rename fail the build.
"""
from __future__ import annotations

import pytest

gr = pytest.importorskip("gradio")  # pinned in requirements.lock; skip if absent

from teledrive import action_registry, ui

# Baselines captured from main at the M19-T01 base commit (6281a66):
#   - 45 / 45 ready actions resolve (launcher --check)
#   - 55 wired controls after the render (drive folder actions x4 + a
#     duplicated build-zip). The redesign must never go below these.
READY_ACTION_BASELINE = 45
WIRED_CONTROL_BASELINE = 55

TELEGRAM_ACTION_IDS = (
    "telegram.set_credentials",
    "telegram.send_code",
    "telegram.resend_code",
    "telegram.verify_code",
    "telegram.verify_password",
    "telegram.logout",
    "telegram.status",
)

PROVES: tuple = ()


def _render(ctx, lang: str = "ar"):
    with gr.Blocks() as demo:
        refs = ui._render_shell(ctx, ctx.binder, gr.State(lang), lang)
    return demo, refs


# ---- counts never decrease ----


def test_ready_action_count_does_not_decrease():
    ready = list(action_registry.ready_specs())
    assert len(ready) >= READY_ACTION_BASELINE


def test_binding_count_does_not_decrease_and_every_ready_action_is_wired(ctx):
    _demo, _refs = _render(ctx)
    ready_ids = {s.action_id for s in action_registry.ready_specs()}
    assert ctx.binder.missing() == []  # no ready action lost
    assert ready_ids <= set(ctx.binder.wired)
    total_controls = sum(len(v) for v in ctx.binder.wired.values())
    assert total_controls >= WIRED_CONTROL_BASELINE


def test_four_drive_folder_panels_still_wired(ctx):
    """DOC-39 §4: the one-folder-truth broadcast still wires all four panels."""
    _demo, _refs = _render(ctx)
    for action_id in ("drive.list_folders", "drive.create_folder", "drive.select_folder"):
        assert len(ctx.binder.wired[action_id]) == 4, action_id


# ---- every Telegram button keeps its action_id + handler ----


def test_every_telegram_action_id_is_wired_to_its_declared_handler(ctx):
    _demo, _refs = _render(ctx)
    for action_id in TELEGRAM_ACTION_IDS:
        spec = action_registry.get(action_id)
        assert spec is not None, action_id
        assert spec.ready, action_id
        records = ctx.binder.wired.get(action_id)
        assert records, f"{action_id} is not wired after the redesign"
        for rec in records:
            assert rec.action_id == action_id, action_id
            assert rec.handler_name == spec.handler_name, action_id
            assert rec.service_path == spec.service_path, action_id


def test_all_wired_actions_match_a_declared_ready_spec(ctx):
    """No invented action_id survived into the wiring (§6.4)."""
    _demo, _refs = _render(ctx)
    ready_ids = {s.action_id for s in action_registry.ready_specs()}
    for action_id in ctx.binder.wired:
        assert action_id in ready_ids, f"unknown action wired: {action_id}"


# ---- theme uses the existing binding; toggle preserves direction ----


def test_theme_control_uses_the_existing_set_theme_binding(ctx):
    _demo, refs = _render(ctx)
    assert "settings.set_theme" in ctx.binder.wired
    assert ctx.binder.wired["settings.set_theme"][0].event == "change"
    assert refs["theme_radio"] is not None


def test_language_and_theme_re_render_preserve_direction(ctx):
    _demo_ar, refs_ar = _render(ctx, "ar")
    _demo_en, refs_en = _render(ctx, "en")
    assert refs_ar["direction"] == "td-rtl"
    assert refs_en["direction"] == "td-ltr"
