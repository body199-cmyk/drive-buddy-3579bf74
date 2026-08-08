"""Single authoritative source for the TeleDrive v4.5 Colab notebook.

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

NOTEBOOK_VERSION = "4.5.0"
TITLE = "TeleDrive v4.5 — Telegram → Google Drive (native Colab)"

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
#
# GitHub Actions downloads the artifact as an OUTER wrapper named
# teledrive-package.zip that CONTAINS the real teledrive_v4.5.zip inside it.
# Upload either file as-is: resolve_package_zip() detects the wrapper by
# content and unwraps it automatically (temp file + atomic move — it never
# reads and writes the same file). Renaming the wrapper is never needed.
import os, pathlib, shutil, sys, tempfile, zipfile

LOCAL_ROOT = pathlib.Path(\"/content\")
PACKAGE_ZIP = LOCAL_ROOT / \"teledrive_v4.5.zip\"
DRIVE_ZIP = pathlib.Path(\"/content/drive/MyDrive/TeleDrive/teledrive_v4.5.zip\")
WRAPPER_NAME = \"teledrive-package.zip\"   # official GitHub Actions artifact download
INNER_NAME = \"teledrive_v4.5.zip\"        # the only member ever unwrapped
EXPECTED_ROOT = \"teledrive-v4.5\"         # directory the tested archive must contain

def _zip_member_names(path):
    try:
        with zipfile.ZipFile(path) as archive:
            return archive.namelist()
    except (OSError, zipfile.BadZipFile):
        return None

def _is_tested_archive(path):
    \"\"\"True only for the real tested archive: an EXPECTED_ROOT/ tree with its lock.\"\"\"
    names = _zip_member_names(path)
    if not names:
        return False
    prefix = EXPECTED_ROOT + \"/\"
    return any(name.startswith(prefix) for name in names) and (
        prefix + \"requirements.lock\" in names
    )

def _safe_inner_member(names):
    \"\"\"Pick the ONE safe inner member, or None.

    Absolute paths, backslashes and \"..\" components are never trusted (no
    path traversal); only a member whose final component is exactly
    teledrive_v4.5.zip is unwrapped.
    \"\"\"
    for name in names:
        pure = pathlib.PurePosixPath(name)
        if pure.is_absolute() or \"\\\\\" in name or \"..\" in pure.parts:
            continue
        if pure.name == INNER_NAME:
            return name
    return None

def _unwrap_inner(wrapper_path, destination):
    \"\"\"Unwrap the wrapper's inner archive onto destination, safely.

    Bytes go to a DIFFERENT temp file, the inner archive is validated there
    (EXPECTED_ROOT + requirements.lock), and only then is it moved atomically
    onto destination. The wrapper is closed before the move, so even a wrapper
    renamed to teledrive_v4.5.zip (destination == wrapper) never reads and
    writes the same file — no self-corruption, no EOFError.
    \"\"\"
    wrapper_path = pathlib.Path(wrapper_path)
    destination = pathlib.Path(destination)
    with zipfile.ZipFile(wrapper_path) as archive:
        member = _safe_inner_member(archive.namelist())
        if member is None:
            raise KeyError(f\"no safe {INNER_NAME} member inside wrapper\")
        payload = archive.read(member)
    fd, tmp_name = tempfile.mkstemp(
        prefix=\".\" + INNER_NAME + \".\", suffix=\".part\", dir=str(destination.parent)
    )
    tmp_path = pathlib.Path(tmp_name)
    try:
        with os.fdopen(fd, \"wb\") as handle:
            handle.write(payload)
        if not _is_tested_archive(tmp_path):
            raise ValueError(
                f\"inner {member} is not the tested archive \"
                f\"(missing {EXPECTED_ROOT}/requirements.lock)\"
            )
        os.replace(tmp_path, destination)  # atomic rename on the same filesystem
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
    return destination

def resolve_package_zip(local_root=LOCAL_ROOT):
    \"\"\"Locate the tested archive, unwrapping the official CI artifact if needed.

    Search order: the real archive at <root>, the real archive in the mounted
    Drive folder, then the official wrapper (teledrive-package.zip) in either
    place. A wrapper RENAMED to teledrive_v4.5.zip is recognized by content —
    it is NOT the tested archive — and is unwrapped via a temp file instead.
    Corrupt files and wrappers without a safe inner member fail with a clear
    error naming the offending path.
    \"\"\"
    local_root = pathlib.Path(local_root)
    package_zip = local_root / INNER_NAME
    drive_dir = local_root / \"drive/MyDrive/TeleDrive\"
    candidates = (
        package_zip,
        drive_dir / INNER_NAME,
        local_root / WRAPPER_NAME,
        drive_dir / WRAPPER_NAME,
    )
    for candidate in candidates:
        if not candidate.exists():
            continue
        if _is_tested_archive(candidate):
            if candidate != package_zip:
                shutil.copy2(candidate, package_zip)  # distinct paths, no self-copy
            return package_zip
        try:
            return _unwrap_inner(candidate, package_zip)
        except (KeyError, ValueError, OSError, zipfile.BadZipFile) as exc:
            raise RuntimeError(f\"invalid package at {candidate}: {exc}\") from exc
    raise AssertionError(
        f\"upload the tested archive to {package_zip} (or {drive_dir / INNER_NAME}) \"
        f\"first; the official GitHub Actions download {WRAPPER_NAME} is accepted \"
        f\"too — upload it as-is, do NOT rename it\"
    )

try:
    from google.colab import drive as colab_drive
    colab_drive.mount(\"/content/drive\", force_remount=False)
except Exception as exc:  # not on Colab, or the user declined the mount
    print(\"drive mount skipped:\", type(exc).__name__)

PACKAGE_ZIP = resolve_package_zip(LOCAL_ROOT)

with zipfile.ZipFile(PACKAGE_ZIP) as archive:
    archive.extractall(LOCAL_ROOT)

PACKAGE_DIR = next(p for p in LOCAL_ROOT.glob(\"teledrive-v4.5*\") if p.is_dir())
os.chdir(PACKAGE_DIR)
sys.path.insert(0, str(PACKAGE_DIR))

# Exact pins, straight from the archive - requirements.lock is the ONE source of
# dependency truth. No version is ever hard-coded in this notebook.
!pip -q install -r \"{PACKAGE_DIR}/requirements.lock\"
print(\"dependency source:\", PACKAGE_DIR / \"requirements.lock\")

print(\"package root:\", PACKAGE_DIR)
print(\"runtime root (local, not Drive):\", os.environ.setdefault(
    \"TELEDRIVE_ROOT\", \"/content/teledrive_runtime\"))
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
