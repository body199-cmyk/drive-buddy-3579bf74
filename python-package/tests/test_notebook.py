"""Notebook acceptance tests — both copies are generated from one source."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from teledrive import notebook_cells

FORBIDDEN = (
    "client_secret",
    "InstalledAppFlow",
    "drive_token",
    "share=True",
    "rmtree",
    "credentials.json",
    "oauth2client",
)


@pytest.fixture(scope="module")
def notebooks() -> dict[Path, dict]:
    return {p: json.loads(p.read_text(encoding="utf-8")) for p in notebook_cells.NOTEBOOK_PATHS}


def test_both_copies_exist_and_are_byte_identical():
    texts = {p: p.read_text(encoding="utf-8") for p in notebook_cells.NOTEBOOK_PATHS}
    assert len(texts) == 2
    assert len(set(texts.values())) == 1, "the two notebook copies differ"


def test_copies_match_the_generator():
    assert notebook_cells.check_all() == [], "run: python -m teledrive.notebook_cells --write"


def test_title_is_v31(notebooks):
    for path, nb in notebooks.items():
        head = "".join(nb["cells"][0]["source"])
        assert "TeleDrive v3.1" in head, path
        assert "v2" not in head.replace("v3.1", ""), path


def test_exactly_seven_code_cells(notebooks):
    for path, nb in notebooks.items():
        code = [c for c in nb["cells"] if c["cell_type"] == "code"]
        assert len(code) == notebook_cells.REQUIRED_CELL_COUNT, path


def test_no_forbidden_patterns(notebooks):
    for path, nb in notebooks.items():
        body = json.dumps(nb)
        for needle in FORBIDDEN:
            assert needle not in body, f"{needle} found in {path}"


def test_uses_native_colab_drive_auth(notebooks):
    for _, nb in notebooks.items():
        body = json.dumps(nb)
        assert "from google.colab import auth as colab_auth" in body
        assert "google.auth.default" in body
        assert "cache_discovery=False" in body
        assert "about().get(" in body


def test_launch_is_not_shared_and_uses_the_one_context(notebooks):
    for _, nb in notebooks.items():
        body = json.dumps(nb)
        assert "share=False" in body
        assert "adopt_service(drive_service)" in body
        assert "launch(ctx" in body
        assert body.count("bootstrap.run()") == 1


def test_sqlite_stays_on_local_content(notebooks):
    for _, nb in notebooks.items():
        body = json.dumps(nb)
        assert "/content/teledrive_runtime" in body
        assert "/content/drive/MyDrive/teledrive_runtime" not in body


def test_test_cell_fails_the_notebook(notebooks):
    for _, nb in notebooks.items():
        body = json.dumps(nb)
        assert "pytest" in body
        assert "returncode" in body


def test_maintenance_cell_is_targeted(notebooks):
    for _, nb in notebooks.items():
        body = json.dumps(nb)
        assert "cleanup_verified_temp" in body
        assert "quarantined" in body
        assert "ctx.shutdown()" in body


def test_colab_cells_export_matches_the_notebook_source():
    payload = json.loads(notebook_cells.CELLS_JSON.read_text(encoding="utf-8"))
    assert payload["version"] == notebook_cells.NOTEBOOK_VERSION
    assert len(payload["cells"]) == notebook_cells.REQUIRED_CELL_COUNT
    assert [c["code"] for c in payload["cells"]] == [c["code"] for c in notebook_cells.CELLS]


def test_cell_4_is_non_blocking_so_cells_5_to_7_stay_runnable():
    cell4 = notebook_cells.CELLS[3]["code"]
    assert "blocking=False" in cell4
    assert "non-blocking" in cell4


def test_requirements_lock_is_the_only_dependency_source():
    assert notebook_cells.hardcoded_pins_in_cells() == [], (
        "notebook cells must not duplicate versions; edit requirements.lock instead"
    )
    assert "requirements.lock" in notebook_cells.CELLS[0]["code"]
    pins = notebook_cells.lock_pins()
    assert pins and "gradio" in pins


def test_colab_cells_json_carries_no_dependency_versions():
    payload = notebook_cells.CELLS_JSON.read_text(encoding="utf-8")
    for name, version in notebook_cells.lock_pins().items():
        assert f"{name}=={version}" not in payload
