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
    # Scan mode radio choices must be the four canonical modes, localized
    for scan_mode in ("message", "range", "latest", "chat"):
        assert f't("scan.mode.{scan_mode}")' in text, scan_mode
    # Media types checkbox must contain all eight canonical types, localized
    for media in ("all", "video", "audio", "document", "photo", "voice", "animation", "sticker"):
        assert f't("media.{media}")' in text, media
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
    # analyze.run wiring passes the full 7-tuple through binder.wire.
    assert re.search(
        r'binder\.wire\(\s*analyze\["analyze_btn"\],\s*"analyze\.run",\s*'
        r'\[analyze\["link"\],\s*analyze\["mode"\],\s*analyze\["message_id"\],'
        r'\s*analyze\["start_id"\],\s*analyze\["end_id"\],\s*analyze\["limit"\],'
        r'\s*analyze\["media_types"\]\]',
        text,
    )
    # Filter wiring must use filter_media_types, not the scan media_types
    assert re.search(
        r'binder\.wire\(\s*analyze\["filters_btn"\],\s*"analyze\.apply_filters",'
        r'\s*\[analyze\["filter_media_types"\],',
        text,
    )
    # Ensure the old wiring `[link, scope]` is gone
    assert "[link, scope]" not in text


def test_no_direct_gradio_handlers_in_analyze_block():
    text = _ui_text()
    # Extract the analyze Tab block (M17-T03 nav.analyze label).
    analyze_start = text.find('with gr.Tab(t("nav.analyze"))')
    assert analyze_start != -1
    analyze_block = text[analyze_start: analyze_start + 8000]
    assert ".click(" not in analyze_block
    assert ".change(" not in analyze_block
    assert ".submit(" not in analyze_block
    # No lambda expression in UI code
    assert re.search(r"\blambda\s*:", text) is None


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
        "analyze.result",
        "err.bad_scan_mode",
        "err.bad_scan_request",
        "err.link_invite_unsupported",
        "err.scan_limit",
        "err.scan_media_type",
        "err.scan_message_id",
        "err.scan_range_ids",
        "err.scan_range_invalid",
        "err.scan_range_too_large",
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
    for aid in ("analyze.run", "analyze.set_mode", "analyze.apply_filters", "analyze.select_all", "analyze.clear_selection", "analyze.enqueue_selected"):
        assert aid in wired_ids, f"{aid} not wired"
