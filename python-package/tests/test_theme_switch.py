"""M17-T03: theme_style_block drives a real CSS-variable <style> block; no JS."""
from __future__ import annotations

from teledrive import action_registry
from teledrive.ui_theme import PALETTES, _all_token_keys, theme_style_block

PROVES = ("settings.set_theme",)


def test_dark_differs_from_light_and_invalid_falls_back():
    dark = theme_style_block("dark")
    light = theme_style_block("light")
    assert dark != light
    assert "data-td-theme=\"dark\"" in dark
    assert "data-td-theme=\"light\"" in light
    # invalid -> dark
    assert "data-td-theme=\"dark\"" in theme_style_block("banana")


def test_all_tokens_present_for_both_themes():
    for theme_name in ("dark", "light"):
        block = theme_style_block(theme_name)
        for key in _all_token_keys():
            css_var = f"--td-{key}"
            assert css_var in block, f"{theme_name} missing token {css_var}"
        assert "style id=\"td-theme-vars\"" in block


def test_set_theme_handler_returns_style_block(ctx):
    """Handler returns (gr.update for HTML host, ok status)."""
    html_update, status = ctx.handlers.h_settings_set_theme("dark")
    assert html_update["value"] == theme_style_block("dark")
    assert "✅" in status
    # Preference persisted.
    assert ctx.preferences.current_theme() == "dark"
    html_update, status = ctx.handlers.h_settings_set_theme("light")
    assert html_update["value"] == theme_style_block("light")
    assert ctx.preferences.current_theme() == "light"


def test_invalid_theme_falls_back_to_dark(ctx):
    html_update, _status = ctx.handlers.h_settings_set_theme("garbage")
    assert "data-td-theme=\"dark\"" in html_update["value"]
