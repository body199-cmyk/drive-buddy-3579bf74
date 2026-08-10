"""DOC-39 (M18-T01) §3 + §7 — Colab render contract.

What the first page opened in Colab must contain:
* Arabic RTL by default, English LTR toggle without state loss
* dark graphite theme by default (lime accent, no white background)
* folder picker visible inside transfers/dashboard
* no orphan layout markers, no blank first render, no stray version literal
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

gr = pytest.importorskip("gradio")

from teledrive import ui
from teledrive.handlers import shell_seed
from teledrive.i18n import t
from teledrive.ui_theme import PALETTES, theme_style_block

UI_SOURCE = Path(ui.__file__).resolve().read_text(encoding="utf-8")

PROVES = ()  # this file guards the render itself; no action claims here


def _render(ctx, lang: str = "ar"):
    with gr.Blocks() as demo:
        refs = ui._render_shell(ctx, ctx.binder, gr.State(lang), lang)
    return demo, refs


def test_arabic_rtl_is_the_default_render(ctx):
    demo, refs = _render(ctx, "ar")
    assert refs["direction"] == "td-rtl"
    assert t("nav.queue") == "التحويلات"
    assert t("nav.dashboard") == "لوحة التحكم"

    # English is an explicit toggle that flips direction only
    _demo_en, refs_en = _render(ctx, "en")
    assert refs_en["direction"] == "td-ltr"
    assert t("nav.queue") == "Transfers"


def test_dark_graphite_theme_is_the_default(ctx):
    assert ctx.preferences.current_theme() == "dark"
    block = theme_style_block("dark")
    assert 'data-td-theme="dark"' in block
    assert f"--td-bg: {PALETTES['dark']['bg']};" in block
    assert f"--td-accent: {PALETTES['dark']['accent']};" in block

    # the style host actually rides the first render (dark, not white)
    demo, refs = _render(ctx, "ar")
    host = refs.get("theme_host") or next(
        (c for c in demo.blocks.values() if getattr(c, "elem_id", None) == "td-theme-vars-host"),
        None,
    )
    assert host is not None
    value = host.value if hasattr(host, "value") else ""
    assert "data-td-theme=\"dark\"" in str(value)
    assert "0d0f10" in str(value)  # graphite bg, not white


def test_folder_picker_is_visible_in_transfers_and_dashboard(ctx):
    _demo, refs = _render(ctx, "ar")
    assert "folder_transfer" in refs and "folder_dash" in refs
    for key in ("folder_transfer", "folder_dash"):
        picker = refs[key]
        assert picker["suffix"] in ("transfer", "dash")
        # every required DOC-39 §4 control exists and is visible
        for control in ("list_btn", "create_btn", "select_btn", "new_name", "choice", "current", "message"):
            assert picker[control].visible is True, f"{key}.{control} hidden"
    # the transfer picker is registered with the same drive handlers
    assert len(ctx.binder.wired["drive.list_folders"]) == 4


def test_topbar_chips_are_styled_html_not_raw_textboxes(ctx):
    _demo, refs = _render(ctx, "ar")
    for key in ("telegram_chip", "drive_chip", "folder_chip", "engine_chip"):
        value = refs[key].value
        assert 'class="td-chip"' in value, f"{key} is not a styled chip"
    # real state, not fake: disconnected everything on a fresh context
    assert t("status.disconnected") in refs["telegram_chip"].value
    assert t("status.disconnected") in refs["folder_chip"].value


def test_version_comes_from_config_not_a_literal(ctx):
    """DOC-39 §3: the version chip reads ctx.config.version; ui.py must not
    hardcode 'v4.5.0' (or any version literal)."""
    assert "4.5.0" not in UI_SOURCE
    assert re.search(r"v\{\s*ctx\.config\.version\s*\}", UI_SOURCE) is not None
    _demo, refs = _render(ctx, "ar")
    seed = shell_seed(ctx)
    assert refs  # non-empty render


def test_no_blank_first_render_and_no_orphan_layout_markers(ctx):
    """First render must contain every section's controls — nothing blank,
    nothing orphaned, no stray unformatted symbols in the top bar."""
    demo, refs = _render(ctx, "ar")
    # every ready action is wired, zero orphans (dead controls fail the build)
    assert ctx.binder.missing() == []
    assert ctx.binder.orphans() == []
    # all seven sections exist in the required order
    assert [k for k, _v in ui.NAV_SECTIONS] == [
        "nav.dashboard", "nav.queue", "nav.analyze", "nav.connection",
        "nav.logs", "nav.settings", "nav.export",
    ]
    # the candidates table carries the DOC-39 §5.2 headers (Arabic)
    assert refs["candidates_table"].headers == [t(k) for k in ui.CANDIDATE_HEADERS]
    # queue table keeps its own 7 headers — no bleed between tables
    assert refs["queue_table"].headers == [t(k) for k in ui.TABLE_HEADERS]
    # no raw textbox chip artifacts: the top bar holds HTML chips only
    topbar_html = str(refs["telegram_chip"].value) + str(refs["drive_chip"].value) + \
        str(refs["folder_chip"].value) + str(refs["engine_chip"].value)
    assert "textarea" not in topbar_html
    assert "<span class=\"td-chip\"" in topbar_html


def test_consistent_widths_css_present(ctx):
    """The theme CSS constrains page width and table widths so panels never
    stretch arbitrarily (DOC-39 §3)."""
    from teledrive.ui_theme import BASE_CSS
    assert "max-width" in BASE_CSS
    assert "td-table" in BASE_CSS
    assert "focus-visible" in BASE_CSS


def test_selection_stage_controls_exist_in_analyze_tab(ctx):
    _demo, refs = _render(ctx, "ar")
    # DOC-39 §5: range from/to, group, preview and the explicit enqueue gate
    assert refs["range_start"].visible is True
    assert refs["range_end"].visible is True
    assert refs["selection_preview"].visible is True
    assert refs["group_choice"].visible is True
    assert refs["enqueue_btn"].visible is True
    # fresh context: nothing selected, nothing enqueueable
    assert refs["enqueue_btn"].interactive is False
    assert t("msg.no_folder_selected") in refs["selection_preview"].value
