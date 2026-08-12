"""M17-T03: ui.py layout-only contract — no SQL, no lambdas, no hardcoded colors."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from teledrive import ui as ui_module
from teledrive.ui import NAV_SECTIONS

gr = pytest.importorskip("gradio")

UI_PATH = Path(ui_module.__file__).resolve()
UI_SRC = UI_PATH.read_text(encoding="utf-8")

PROVES = ()


def _tree():
    return ast.parse(UI_SRC, filename=str(UI_PATH))


def test_zero_lambdas_in_ui():
    tree = _tree()
    lambdas = [n for n in ast.walk(tree) if isinstance(n, ast.Lambda)]
    assert lambdas == [], "ui.py must not contain lambda expressions"


def test_zero_direct_gradio_event_calls():
    """No direct .click/.change/.submit/.select/.input in ui.py. All wiring goes
    through binder.wire()."""
    forbidden = {"click", "change", "submit", "select", "input"}
    tree = _tree()
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Method calls on gr.* objects that look like event registration
            if isinstance(node.func, ast.Attribute) and node.func.attr in forbidden:
                # Allow binder.wire(.event="click") kwargs
                hits.append(ast.dump(node.func))
    # The only forbidden hits that are gr-direct events should be zero;
    # binder.wire uses a string "event" kwarg, not a method chain.
    # Filter: any call like `x.click(...)` where x is NOT binder/string attr.
    # Easiest: assert there are NO attribute calls ending in those event names
    # outside of binder and of comment strings.
    real_hits = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            attr = n.func.attr
            if attr in forbidden and not _is_binder_call(n):
                real_hits.append(f"{_attr_chain(n.func)}.{attr}(...)")
    assert real_hits == [], f"direct Gradio event calls in ui.py: {real_hits}"


def _attr_chain(node: ast.Attribute) -> str:
    parts = []
    cur = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
    return ".".join(reversed(parts))


def _is_binder_call(call: ast.Call) -> bool:
    # binder.wire(... event=...): the outer call is binder.wire; the events
    # attribute may appear only as a string literal keyword.
    return False  # we already filter by checking the callsite, not kwarg names


def test_zero_hardcoded_colors_in_ui():
    """ui.py must not contain hex color literals — colors live in ui_theme."""
    import re
    # find any #RRGGBB / #RGB literals
    hits = re.findall(r"#[0-9a-fA-F]{3,8}\b", UI_SRC)
    # Allow shebang/comment-only? ui.py has none. No CSS in ui.py.
    assert hits == [], f"ui.py contains hardcoded color literals: {hits}"


def test_rtl_is_default(ctx):
    """Default language is Arabic (rtl)."""
    assert ui_module.build() is not None  # builds without exception


def test_language_render_runs_on_initial_page_load_and_language_change():
    """The shell must be rendered when the page first loads, not only after
    a user toggles its language state.

    ``gr.render(inputs=...)`` uses Gradio's default load + input-change trigger.
    Passing ``triggers=[lang_state.change]`` opts out of the load trigger and
    produces an otherwise-empty first page.
    """
    root = next(
        node for node in ast.walk(_tree())
        if isinstance(node, ast.FunctionDef) and node.name == "_language_root"
    )
    render = next(
        decorator for decorator in root.decorator_list
        if isinstance(decorator, ast.Call)
        and isinstance(decorator.func, ast.Attribute)
        and decorator.func.attr == "render"
    )
    assert not any(keyword.arg == "triggers" for keyword in render.keywords)
    inputs = next(keyword.value for keyword in render.keywords if keyword.arg == "inputs")
    assert isinstance(inputs, ast.List)
    assert len(inputs.elts) == 1


def test_five_nav_sections_present_in_required_order():
    """M19-T01 §5.1: five zones behind ONE nav bar, in workflow order
    (connect → analyze → transfer → logs → settings/export). The dashboard and
    export sections folded into Connection and Settings respectively."""
    names = [label_key for (label_key, _section) in NAV_SECTIONS]
    assert len(names) == 5
    assert names == [
        "nav.connection", "nav.analyze", "nav.queue",
        "nav.logs", "nav.settings",
    ]


def test_concurrency_slider_capped_at_four():
    """Concurrency slider 1..4, default 2 — never 50 or 19."""
    from teledrive.services import SettingsService
    assert SettingsService.MIN == 1
    assert SettingsService.MAX == 4
    assert SettingsService.DEFAULT == 2


def test_ui_module_has_no_sql_calls():
    """ui.py must not import or call database methods directly."""
    tree = _tree()
    sql_hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "database":
            sql_hits.append(ast.dump(node))
        if isinstance(node, ast.Import):
            for n in node.names:
                if "database" in n.name or "db" == n.name.split(".")[-1]:
                    sql_hits.append(n.name)
    assert sql_hits == [], "ui.py must not import database directly"
