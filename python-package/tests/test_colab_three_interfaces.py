"""Regression tests for Colab's third UI launcher choice.

The third UI is the existing hosted React frontend, not a second transfer
engine. Never drop the original Gradio/Web modes or expose tokens in Cell 4.
"""
from __future__ import annotations

import ast
import json
import re
import textwrap

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
    assert "شغّل الخلية الخامسة" in source
    assert "VERCEL_NEXT_CONNECT_URL" not in source
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
    assert "_reuse_tunnel" in source
    assert "_teledrive_tunnel_url" in source
    assert "if _reuse_tunnel:" in source
    assert 'if _mode in ("TeleDrive_Next", "Run_Both_Together") else' in source


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
    assert "window.sessionStorage.setItem" in content
    assert "window.sessionStorage.getItem" in content
    assert "window.sessionStorage.removeItem" in content


def test_old_next_connect_links_redirect_to_dashboard():
    path = notebook_cells.REPO_ROOT / "src" / "routes" / "connect-next.tsx"
    content = path.read_text(encoding="utf-8")
    assert 'window.location.replace("/teledrive-next" + window.location.hash)' in content
    assert 'get("manual") !== "1"' in content
    assert "showManualForm" in content



def test_handoff_cell_rerun_keeps_existing_tunnel_alive():
    """An existing healthy Cloudflare process must not be killed on rerun."""
    source = notebook_cells.CELL_4B_VERCEL_HANDOFF
    start = source.index("        # Keep the same healthy tunnel across handoff-cell reruns.")
    end = source.index("        _now = time.time()", start)
    code = textwrap.dedent(source[start:end])

    class FakeProcess:
        terminated = False

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True
            raise AssertionError("Healthy tunnel must not be terminated")

    process = FakeProcess()
    context = object()
    environment = {
        "_port": 8765,
        "ctx": context,
        "_teledrive_tunnel": process,
        "_teledrive_tunnel_url": "https://my-long-tunnel.trycloudflare.com",
        "_teledrive_tunnel_port": 8765,
        "_teledrive_tunnel_ctx_id": id(context),
        "re": re,
        "print": lambda *args: None,
    }
    exec(compile(code, "<tunnel reuse>", "exec"), environment)
    assert environment["_reuse_tunnel"] is True
    assert environment["_tunnel_url"] == "https://my-long-tunnel.trycloudflare.com"
    assert environment["_teledrive_tunnel"] is process
    assert environment["_tunnel_created_this_run"] is False
    assert not process.terminated
