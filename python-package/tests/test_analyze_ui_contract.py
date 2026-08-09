"""M15-T11 — Analyze tab contract.

Asserts the Analyze tab exposes the scoped scan controls, the media filters,
the selection queue actions, and that every visible control is wired through
the named handler/binder system without direct Gradio event handlers.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

gr = pytest.importorskip("gradio")

from teledrive import action_registry, ui
from teledrive.i18n import t

UI_SOURCE = Path(__file__).resolve().parents[1] / "teledrive" / "ui.py"
EN_LOCALE = Path(__file__).resolve().parents[1] / "teledrive" / "locale" / "en.json"
AR_LOCALE = Path(__file__).resolve().parents[1] / "teledrive" / "locale" / "ar.json"

PROVES = ()  # this file guards the shell; it does not claim a registry proof


def _ui_text() -> str:
    return UI_SOURCE.read_text(encoding="utf-8")


def _render(ctx, lang: str = "ar"):
    with gr.Blocks() as demo:
        refs = ui._render_shell(ctx, ctx.binder, gr.State(lang), lang)
    return demo, refs


def test_analyze_tab_has_required_controls():
    text = _ui_text()
    # Instructions markdown and scoped controls must exist
    assert 't("analyze.instructions")' in text
    assert 't("form.scan_mode")' in text
    assert 't("form.media_types")' in text
    assert 't("form.message_id")' in text
    assert 't("form.start_message")' in text
    assert 't("form.end_message")' in text
    assert 't("form.message_limit")' in text
    # Scan mode radio choices must be the four canonical modes
    assert re.search(r'choices=\["message",\s*"range",\s*"latest",\s*"chat"\]', text)
    # Media types checkbox must contain all eight canonical types
    assert 'choices=["all", "video", "audio", "document", "photo", "voice", "animation", "sticker"]' in text
    # Scan inputs must be declared
    assert "link = gr.Textbox" in text
    assert "mode = gr.Radio" in text
    assert "media_types = gr.CheckboxGroup" in text
    assert "message_id = gr.Number" in text
    assert "start_id = gr.Number" in text
    assert "end_id = gr.Number" in text
    assert "limit = gr.Number" in text
    # Filter accordion must use separate filter_media_types (not reused scan control)
    assert "filter_media_types = gr.CheckboxGroup" in text
    assert 'value=["all"]' in text
    # Selection actions must still exist
    assert 'binder.button(gr, "analyze.select_all")' in text
    assert 'binder.button(gr, "analyze.clear_selection")' in text
    assert 'binder.button(gr, "analyze.enqueue_selected"' in text


def test_analyze_run_wiring_has_seven_inputs(ctx):
    text = _ui_text()
    # The analyze.run wiring must pass the full 7-tuple, not the old 2-tuple.
    # Look for the wire_if_ready block with the seven names.
    assert 'binder.wire_if_ready(' in text
    # Must contain the exact input list order: link, mode, message_id, start_id, end_id, limit, media_types
    assert re.search(r'binder\.wire_if_ready\(\s*analyze_btn,\s*"analyze\.run",\s*\[link,\s*mode,\s*message_id,\s*start_id,\s*end_id,\s*limit,\s*media_types\]', text)
    # Filter wiring must use filter_media_types, not the scan media_types
    assert re.search(r'binder\.wire_if_ready\(\s*filters_btn,\s*"analyze\.apply_filters",\s*\[filter_media_types,', text)
    # Ensure the old wiring `[link, scope]` is gone
    assert "[link, scope]" not in text
    # Also ensure SCOPE_CHOICES is not used for the analyze mode (old constant)
    # The new mode radio does not reference SCOPE_CHOICES
    mode_section = re.search(r'mode = gr\.Radio\(.*?\)', text, re.DOTALL)
    assert mode_section and "SCOPE_CHOICES" not in mode_section.group(0)


def test_no_direct_gradio_handlers_in_analyze_block():
    text = _ui_text()
    # The repo forbids direct .click/.change/.submit and lambdas in UI code.
    # The analyze tab must not introduce them.
    # Extract the analyze Tab block roughly (from nav.link to next Tab)
    analyze_start = text.find('with gr.Tab(t("nav.link"))')
    assert analyze_start != -1
    # Take 150 lines after start to cover the block
    analyze_block = text[analyze_start: analyze_start + 8000]
    assert ".click(" not in analyze_block
    assert ".change(" not in analyze_block
    assert ".submit(" not in analyze_block
    # No lambda expression in UI code — docstring mentions "no lambdas" is allowed, but an actual `lambda:` must not exist
    # Use regex to avoid false positive on the word "lambdas" in docstring
    assert re.search(r"\blambda\s*:", text) is None
    # No direct binder.wire (only wire_if_ready allowed for analyze)
    # The whole file should only use wire_if_ready
    assert "binder.wire(" not in text.replace("binder.wire_if_ready(", "")


def test_analyze_table_is_seeded_from_real_selection(ctx):
    demo, refs = _render(ctx, "ar")
    # Initially empty, seeded from selection.visible() which is []
    assert refs["candidates_table"].value["data"] == []
    # After adding a candidate, re-render shows it
    from teledrive.models import MediaItem
    item = MediaItem(safe_name="clip.mp4", media_type="video", size_bytes=1234)
    ctx.selection.set_candidates([item])
    demo2, refs2 = _render(ctx, "ar")
    data = refs2["candidates_table"].value["data"]
    assert len(data) == 1
    assert data[0][0] == item.id
    # analyze.run outputs must not include the queue table
    for bf in demo2.fns.values():
        if getattr(getattr(bf, "fn", None), "action_id", None) == "analyze.run":
            assert refs2["queue_table"] not in bf.outputs


def test_locale_keys_present_in_both_languages():
    import json
    en = json.loads(EN_LOCALE.read_text(encoding="utf-8"))
    ar = json.loads(AR_LOCALE.read_text(encoding="utf-8"))
    required = [
        "analyze.instructions",
        "form.scan_mode",
        "form.media_types",
        "form.message_id",
        "form.start_message",
        "form.end_message",
        "form.message_limit",
        "scan.mode.message",
        "scan.mode.range",
        "scan.mode.latest",
        "scan.mode.chat",
        "media.all",
        "media.video",
        "media.audio",
        "media.document",
        "media.photo",
        "media.voice",
        "media.animation",
        "media.sticker",
    ]
    for key in required:
        assert key in en, f"missing {key} in en.json"
        assert key in ar, f"missing {key} in ar.json"
        assert en[key].strip() != ""
        assert ar[key].strip() != ""


def test_binder_wires_all_analyze_actions_and_no_orphans(ctx):
    demo, refs = _render(ctx, "ar")
    assert ctx.binder.missing() == []
    assert ctx.binder.orphans() == []
    wired_ids = {bf.fn.action_id for bf in demo.fns.values() if getattr(getattr(bf, "fn", None), "action_id", None)}
    # All analyze actions must be wired
    for aid in ("analyze.run", "analyze.apply_filters", "analyze.select_all", "analyze.clear_selection", "analyze.enqueue_selected"):
        assert aid in wired_ids, f"{aid} not wired"
