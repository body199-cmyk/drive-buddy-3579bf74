"""Regression tests for Colab's third UI launcher choice.

The third UI is the existing hosted React frontend, not a second transfer
engine. Never drop the original Gradio/Web modes or expose tokens in Cell 4.
"""
from __future__ import annotations

import ast
import json

from teledrive import notebook_cells


def test_cell4_offers_three_interfaces_and_retains_legacy_modes():
    source = notebook_cells.CELL_4
    ast.parse(source)
    for mode in (
        "Classic_Gradio_Backup",
        "Modern_Web_Dashboard",
        "TeleDrive_Next",
        "Run_Both_Together",
        "Run_All_Three",
    ):
        assert mode in source
    assert 'UI_MODE = "Run_Both_Together"' in source
    assert 'if UI_MODE in ("Classic_Gradio_Backup", "Run_Both_Together", "Run_All_Three")' in source
    assert (
        'if UI_MODE in ("Modern_Web_Dashboard", "Run_Both_Together", '
        '"TeleDrive_Next", "Run_All_Three")'
    ) in source
    assert "launch_web_dashboard(ctx, port=WEB_DASHBOARD_PORT)" in source
    assert "launch(ctx, share=False, inline=False, blocking=False)" in source
    assert "/teledrive-next" in source
    assert "/connect-next" not in source
    assert "remote_control_token" not in source


def test_cell5_handoff_targets_new_frontend_without_removing_old_one():
    source = notebook_cells.CELL_4B_VERCEL_HANDOFF
    ast.parse(source)
    assert "VERCEL_NEXT_CONNECT_URL" in source
    assert "/teledrive-next" in source
    assert "VERCEL_CONNECT_URL" in source
    assert '"Run_All_Three"' in source
    assert '"TeleDrive_Next"' in source
    assert "secrets.token_urlsafe(32)" in source
    assert "html.escape(_handoff, quote=True)" in source
    assert "remote_handoff_tokens" in source


def test_notebook_artifacts_generated_from_canonical_source():
    # All copies and in-app copy-cells export must describe the same menu.
    assert notebook_cells.check_all() == []
    for path in notebook_cells.NOTEBOOK_PATHS:
        document = json.loads(path.read_text(encoding="utf-8"))
        cell_four = "".join(document["cells"][4]["source"])
        assert '"TeleDrive_Next"' in cell_four
        assert '"Run_All_Three"' in cell_four
    exported = json.loads(notebook_cells.CELLS_JSON.read_text(encoding="utf-8"))
    assert '"TeleDrive_Next"' in exported["cells"][3]["code"]


def test_next_frontend_opens_directly_and_pairs_without_an_auth_form():
    path = notebook_cells.REPO_ROOT / "src" / "routes" / "teledrive-next.tsx"
    content = path.read_text(encoding="utf-8")
    assert 'createFileRoute("/teledrive-next")' in content
    assert "component: NextDashboardPage" in content
    assert "<TeleDriveNext" in content
    assert '"api/pairing/exchange"' in content
    assert "window.history.replaceState" in content
    assert 'href="/connect-next?manual=1"' in content  # Optional manual fallback only.
    assert "window.localStorage.setItem" not in content


def test_old_next_connect_links_redirect_to_dashboard():
    path = notebook_cells.REPO_ROOT / "src" / "routes" / "connect-next.tsx"
    content = path.read_text(encoding="utf-8")
    assert 'window.location.replace("/teledrive-next" + window.location.hash)' in content
    assert 'get("manual") !== "1"' in content
    assert "showManualForm" in content
