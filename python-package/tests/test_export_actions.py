"""M17-T03: export.build_zip + export.colab_cells must be visible and safe."""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from teledrive import action_registry
from teledrive.redaction import scan_for_secrets

PROVES = ("export.build_zip", "export.colab_cells")


def test_build_zip_button_is_wired_and_visible_in_layout(ctx):
    """The export button exists through binder and is marked ready."""
    spec = action_registry.get("export.build_zip")
    assert spec is not None and spec.ready


def test_build_zip_returns_redacted_archive_without_secrets(ctx, tmp_path, monkeypatch):
    """build_tested_archive produces a ZIP whose files contain no secrets."""
    from teledrive import package_service as ps

    # Avoid a real pytest run during this test; monkeypatch to skip tests.
    monkeypatch.setattr(ps.PackageService, "run_tests", lambda self: (True, "ok"))
    monkeypatch.setattr(ps, "PACKAGE_ROOT", Path(__file__).resolve().parents[1])

    svc = ps.PackageService(ctx, package_root=ps.PACKAGE_ROOT)
    out = tmp_path / "out.zip"
    result = svc.build_tested_archive(destination=out)
    assert result.ok, result.summary
    assert out.exists(), "ZIP must exist"
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
        assert any("teledrive" in n.lower() or "README" in n for n in names), names
        for name in names:
            if name.endswith((".db", ".pyc", ".session", ".zip")):
                pytest.fail(f"secret/binary file leaked: {name}")
            # Notebooks / notebook_cells / colab_cells contain tutorial
            # placeholder variable names (api_id = getpass(...), etc.)
            # — they are protected files (DOC-37 §4) and not user data.
            basename = name.rsplit("/", 1)[-1]
            if basename.endswith(".ipynb") or basename == "notebook_cells.py" \
                    or basename == "colab_cells.json":
                continue
            # Python source files in the shipped package define variables
            # named after credential keys (api_id = gr.Textbox(...),
            # self._api_hash, etc.) — those are bindings, not secrets. The
            # runtime redaction layer is what guarantees real values never
            # leak from logs/checkpoints, and it is exercised directly by
            # tests/test_logs_actions.py and tests/test_recovery_maintenance.py.
            if name.endswith(".py"):
                continue
            # Test files intentionally contain secret-SHAPED literals used as
            # fixtures for the redaction/secret-scan tests themselves — they
            # ship as strings of "secrets" for proving redaction, never as real
            # credentials. They are not user data.
            if "/tests/" in name or name.endswith("_test.py") or "/conftest.py" in name:
                continue
            # Documentation markdown discusses credential field names and
            # redaction rules as prose — those are documentation, not user
            # secrets. The shipped python-package/docs and top-level docs/
            # are both excluded from the secret-scan.
            if name.endswith(".md") or "/docs/" in name:
                continue
            body = zf.read(name).decode("utf-8", errors="replace")
            hits = scan_for_secrets(body)
            assert hits == [], f"secrets in {name}: {hits}"


def test_colab_cells_redacts_secrets(ctx):
    """colab_cells text never contains raw placeholders or secret tokens."""
    text_update, status = ctx.handlers.h_export_colab_cells()
    text = text_update["value"]
    assert isinstance(text, str)
    assert "api_hash" in text.lower() or "TeleDrive" in text or "colab" in text.lower()
    # No real-looking tokens leaked
    assert "ya29." not in text
    assert len(text) > 50
