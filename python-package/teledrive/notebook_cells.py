"""Single authoritative source for the TeleDrive v3.1 Colab notebook.

Both notebook copies are GENERATED from this module:

    python -m teledrive.notebook_cells --write

writes, byte-identically:

    python-package/notebook/TeleDrive.ipynb
    public/TeleDrive.ipynb

and refreshes ``teledrive/colab_cells.json`` so the in-app "copy the cells"
export can never drift from the shipped notebook.

Constitution rules encoded here:
  * exactly seven required cells;
  * native Colab Drive auth only (no client_secret.json, no pasted OAuth code,
    no persisted drive_token.json);
  * ``share=False`` — no public tunnel by default;
  * exactly one ApplicationContext, one async runtime, one Telegram client and
    one Drive service, all created in cell 4 and reused afterwards;
  * SQLite and temp files stay on local ``/content``, never on mounted Drive;
  * no blind ``rmtree(TEMP_DIR)`` — maintenance deletes only temp files that
    belong to verified Uploaded items and quarantines everything unknown.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

NOTEBOOK_VERSION = "3.1.0"
TITLE = "TeleDrive v3.1 — Telegram → Google Drive (native Colab)"

PACKAGE_ROOT = Path(__file__).resolve().parent.parent  # python-package/
REPO_ROOT = PACKAGE_ROOT.parent
NOTEBOOK_PATHS = (
    PACKAGE_ROOT / "notebook" / "TeleDrive.ipynb",
    REPO_ROOT / "public" / "TeleDrive.ipynb",
)
CELLS_JSON = Path(__file__).resolve().parent / "colab_cells.json"

HEADER_MARKDOWN = f"""# {TITLE}

Run the cells top to bottom, once, in a single Colab runtime.

* Google Drive auth is **native Colab** — no desktop OAuth JSON upload and
  no pasted authorization code anywhere.
* Telegram API ID / API Hash are typed into a hidden prompt and are never
  printed, logged, snapshotted or packaged.
* The interface runs **locally in this runtime** (`share=False`). No public
  tunnel is created unless you deliberately opt in.
* The database and temporary files live on local `/content`; only the finished
  uploads go to Google Drive.
"""

CELL_1 = '''# ==== Cell 1: restore the tested package and install pinned dependencies ====
# Mounted Drive is used ONLY to fetch the tested archive. SQLite, logs and temp
# files stay on local /content — never on the mounted Drive filesystem.
import os, pathlib, shutil, sys, zipfile

LOCAL_ROOT = pathlib.Path("/content")
PACKAGE_ZIP = LOCAL_ROOT / "teledrive_v3.1.zip"
DRIVE_ZIP = pathlib.Path("/content/drive/MyDrive/TeleDrive/teledrive_v3.1.zip")

try:
    from google.colab import drive as colab_drive
    colab_drive.mount("/content/drive", force_remount=False)
except Exception as exc:  # not on Colab, or the user declined the mount
    print("drive mount skipped:", type(exc).__name__)

if not PACKAGE_ZIP.exists() and DRIVE_ZIP.exists():
    shutil.copy2(DRIVE_ZIP, PACKAGE_ZIP)

assert PACKAGE_ZIP.exists(), (
    f"upload the tested archive to {PACKAGE_ZIP} (or {DRIVE_ZIP}) first"
)

with zipfile.ZipFile(PACKAGE_ZIP) as archive:
    archive.extractall(LOCAL_ROOT)

PACKAGE_DIR = next(p for p in LOCAL_ROOT.glob("teledrive-v3.1*") if p.is_dir())
os.chdir(PACKAGE_DIR)
sys.path.insert(0, str(PACKAGE_DIR))

# Exact pins, straight from the archive - requirements.lock is the ONE source of
# dependency truth. No version is ever hard-coded in this notebook.
!pip -q install -r "{PACKAGE_DIR}/requirements.lock"
print("dependency source:", PACKAGE_DIR / "requirements.lock")

print("package root:", PACKAGE_DIR)
print("runtime root (local, not Drive):", os.environ.setdefault(
    "TELEDRIVE_ROOT", "/content/teledrive_runtime"))
'''

CELL_2 = '''# ==== Cell 2: bootstrap local directories, logging, SQLite migrations, WAL ====
import os
os.environ.setdefault("TELEDRIVE_ROOT", "/content/teledrive_runtime")

from teledrive import bootstrap

ctx = bootstrap.run()          # the ONE ApplicationContext for this runtime
print("schema version:", ctx.bootstrap_info["schema_version"])
print("free bytes on local disk:", ctx.bootstrap_info["free_bytes"])
print("journal mode:", ctx.db.journal_mode())
'''

CELL_3 = '''# ==== Cell 3: credentials — hidden Telegram input + native Colab Drive auth ====
import getpass

# Telegram: hidden input, never echoed, never written to logs or snapshots.
api_id = getpass.getpass("Telegram API ID (hidden): ").strip()
api_hash = getpass.getpass("Telegram API Hash (hidden): ").strip()
assert api_id.isdigit() and api_hash, "API ID must be numeric and API Hash non-empty"

# Google Drive: native Colab credentials only. No desktop OAuth JSON upload,
# no pasted authorization code, no persisted Drive token file.
from google.colab import auth as colab_auth
import google.auth
from googleapiclient.discovery import build

colab_auth.authenticate_user(clear_output=False)
creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/drive"])
drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)

# The gate: nothing may report "Connected" before this call succeeds.
about = drive_service.about().get(
    fields="user(displayName,emailAddress),storageQuota(limit,usage)").execute()
print("drive verified for:", about["user"].get("emailAddress", "(hidden)"))
'''

CELL_4 = '''# ==== Cell 4: inject into the ONE context and launch the interface ====
# No second context, no second event loop, no second Telegram client, no second
# Drive service. Everything below reuses the objects created in cells 2 and 3.
from teledrive.app import launch

ctx.telegram_auth.set_credentials(api_id, api_hash)   # secrets stay in memory
del api_id, api_hash

ctx.drive_auth.adopt_service(drive_service)           # already verified above
print("drive status:", ctx.drive_auth.status().state)

ctx.checkpoints.restore_and_reconcile()               # safe state, no auto-resume

# share=False: the UI is reachable inside this runtime only. A public link is an
# explicit opt-in (pass share to launch yourself) and is never the default.
# blocking=False: the cell returns immediately, so cells 5-7 (handoff, tests,
# maintenance) stay runnable while the interface keeps serving. The launch
# handle lives on ctx.ui and is closed by ctx.shutdown() in cell 7.
launch(ctx, share=False, inline=True, blocking=False)
print("ui running (non-blocking); cells 5-7 can be run while it serves")
'''

CELL_5 = '''# ==== Cell 5: redacted handoff snapshot ====
from teledrive import handoff

# handoff.generate() runs every line through redaction before returning it.
print(handoff.generate(objective="controlled Colab run", phase="9 (Colab readiness)"))
print("snapshot generated (secrets redacted)")
'''


CELL_6 = '''# ==== Cell 6: run the packaged test suite and fail loudly ====
import subprocess, sys

proc = subprocess.run(
    [sys.executable, "-m", "pytest", "-q", "tests"],
    capture_output=True, text=True,
)
print(proc.stdout)
print(proc.stderr, file=sys.stderr)
if proc.returncode != 0:
    raise SystemExit(f"test suite failed with exit code {proc.returncode}")
print("tests passed")
'''

CELL_7 = '''# ==== Cell 7: safe maintenance — targeted cleanup, never a blind wipe ====
# There is deliberately no blind wipe of the temp directory here. Only files that
# belong to items verified as Uploaded are deleted; anything unrecognised or
# incomplete is moved to the quarantine directory for manual review.
print(ctx.checkpoints.persist())

from teledrive import storage_manager

report = storage_manager.cleanup_verified_temp()
print("deleted verified temp files:", report["deleted"])
print("quarantined unknown/incomplete files:", report["quarantined"])

ctx.shutdown()      # closes the UI handle, stops the async runtime, closes SQLite
print("runtime closed")
'''

CELLS: tuple[dict[str, str], ...] = (
    {"title": "Restore package and install pinned dependencies", "code": CELL_1},
    {"title": "Bootstrap directories, logging, SQLite migrations and WAL", "code": CELL_2},
    {"title": "Telegram credentials (hidden) and native Colab Drive auth", "code": CELL_3},
    {"title": "Inject into the one context and launch the UI (share=False)", "code": CELL_4},
    {"title": "Redacted handoff snapshot", "code": CELL_5},
    {"title": "Run the packaged test suite", "code": CELL_6},
    {"title": "Safe maintenance and clean shutdown", "code": CELL_7},
)

REQUIREMENTS_LOCK = PACKAGE_ROOT / "requirements.lock"


def lock_pins() -> dict[str, str]:
    """Return {package: version} parsed from requirements.lock (one source of truth)."""
    pins: dict[str, str] = {}
    if not REQUIREMENTS_LOCK.exists():  # pragma: no cover - lock always shipped
        return pins
    for raw in REQUIREMENTS_LOCK.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "==" not in line:
            continue
        name, _, version = line.partition("==")
        pins[name.strip().lower()] = version.strip()
    return pins


def hardcoded_pins_in_cells() -> list[str]:
    """Every ``package==version`` literal duplicated inside the notebook cells."""
    import re

    found: list[str] = []
    for cell in CELLS:
        found.extend(re.findall(r"[A-Za-z0-9_.\-]+==\d[\w.]*", cell["code"]))
    return found


REQUIRED_CELL_COUNT = 7


def _source_lines(text: str) -> list[str]:
    lines = text.rstrip("\n").split("\n")
    return [line + "\n" for line in lines[:-1]] + [lines[-1]]


def build_notebook() -> dict[str, Any]:
    """Return the notebook JSON document generated from CELLS."""
    cells: list[dict[str, Any]] = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": _source_lines(HEADER_MARKDOWN),
        }
    ]
    for cell in CELLS:
        cells.append(
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {"teledrive_title": cell["title"]},
                "outputs": [],
                "source": _source_lines(cell["code"]),
            }
        )
    return {
        "cells": cells,
        "metadata": {
            "teledrive_version": NOTEBOOK_VERSION,
            "colab": {"name": "TeleDrive.ipynb", "provenance": []},
            "kernelspec": {"display_name": "Python 3", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 0,
    }


def notebook_text() -> str:
    return json.dumps(build_notebook(), ensure_ascii=False, indent=1) + "\n"


def cells_payload() -> dict[str, Any]:
    return {"version": NOTEBOOK_VERSION, "cells": [dict(c) for c in CELLS]}


def cells_json_text() -> str:
    return json.dumps(cells_payload(), ensure_ascii=False, indent=2) + "\n"


def write_all() -> list[Path]:
    written: list[Path] = []
    text = notebook_text()
    for path in NOTEBOOK_PATHS:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        written.append(path)
    CELLS_JSON.write_text(cells_json_text(), encoding="utf-8")
    written.append(CELLS_JSON)
    return written


def check_all() -> list[Path]:
    """Return the paths whose content differs from the generated source."""
    text = notebook_text()
    stale = [p for p in NOTEBOOK_PATHS if not p.exists() or p.read_text(encoding="utf-8") != text]
    if not CELLS_JSON.exists() or CELLS_JSON.read_text(encoding="utf-8") != cells_json_text():
        stale.append(CELLS_JSON)
    return stale


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the TeleDrive notebooks")
    parser.add_argument("--write", action="store_true", help="write both notebook copies")
    parser.add_argument("--check", action="store_true", help="fail when a copy is stale")
    args = parser.parse_args(argv)

    if args.check or not args.write:
        stale = check_all()
        for path in stale:
            print("stale:", path)
        if stale:
            return 1
        print("notebooks are in sync")
        return 0

    for path in write_all():
        print("wrote:", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
