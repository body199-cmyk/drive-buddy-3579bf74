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


def test_title_is_v50(notebooks):
    for path, nb in notebooks.items():
        head = "".join(nb["cells"][0]["source"])
        assert "TeleDrive v5.0" in head, path
        assert "v2" not in head.replace("v5.0", ""), path
        assert "v3.1" not in head, path


def test_seven_required_and_two_optional_code_cells(notebooks):
    for path, nb in notebooks.items():
        code = [c for c in nb["cells"] if c["cell_type"] == "code"]
        assert notebook_cells.REQUIRED_CELL_COUNT == 7
        assert notebook_cells.OPTIONAL_CELL_COUNT == 2
        assert len(code) == notebook_cells.TOTAL_CELL_COUNT, path
        assert "Optional start of best-effort Colab keep-alive" in code[7]["metadata"]["teledrive_title"]
        assert "Optional stop of Colab keep-alive" in code[8]["metadata"]["teledrive_title"]


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
    assert len(payload["cells"]) == notebook_cells.TOTAL_CELL_COUNT
    assert [c["code"] for c in payload["cells"]] == [c["code"] for c in notebook_cells.CELLS]


def test_cell_4_is_non_blocking_so_cells_5_to_7_stay_runnable():
    cell4 = notebook_cells.CELLS[3]["code"]
    assert "blocking=False" in cell4
    assert "non-blocking" in cell4


def test_cell_3_uses_drive_managed_vault_before_optional_secret_migration():
    cell3 = notebook_cells.CELLS[2]["code"]
    assert 'api_id = str(probe.get("api_id") or "").strip()' in cell3
    assert 'api_hash = str(probe.get("api_hash") or "").strip()' in cell3
    assert 'cred_source = "Drive-managed vault"' in cell3
    assert "no Colab Secret required" in cell3
    assert "from google.colab import userdata" in cell3
    assert "TELEGRAM_API_ID" in cell3
    assert "TELEGRAM_API_HASH" in cell3
    assert "getpass.getpass" in cell3
    assert "drive_token" not in cell3
    assert cell3.index('api_hash = str(probe.get("api_hash")') < cell3.index("from google.colab import userdata")
    assert "if not has_saved_vault and not phone:" in cell3


def test_cell_4_restores_vault_and_leaves_keepalive_optional():
    cell4 = notebook_cells.CELLS[3]["code"]
    adopt = cell4.index("ctx.drive_auth.adopt_service")
    restore = cell4.index("session_vault.restore_from_context")
    creds = cell4.index("ctx.telegram_auth.set_credentials")
    assert adopt < restore < creds
    assert "session_vault.start_keepalive" not in cell4


def test_optional_keepalive_cell_has_start_audio_and_stop_control():
    start_cell = notebook_cells.CELLS[7]["code"]
    stop_cell = notebook_cells.CELLS[8]["code"]
    assert "session_vault.start_keepalive()" in start_cell
    assert "wave.open(_silent_audio_buffer" in start_cell
    assert "data:audio/wav;base64,{_silent_audio_base64}" in start_cell
    assert "controls autoplay loop muted playsinline" in start_cell
    assert "display(HTML(silent_audio_code))" in start_cell
    assert "no external URL or network request" in start_cell
    assert "session_vault.stop_keepalive()" in stop_cell
    assert "If the audio player is still playing" in stop_cell


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
