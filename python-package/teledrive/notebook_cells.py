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
    belong to verified Uploaded items and quarantines everything unknown;
  * cell 1 runs a pre-bootstrap integrity-verified update gate (pinned release
    manifest + sha256, ``.part``-only downloads, atomic swap) that REFUSES to
    touch a live runtime and never hot-reloads; the archived ZIP in Drive
    stays the sanctioned fallback, and refusal is never fatal.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

NOTEBOOK_VERSION = "5.0.0"
TITLE = "TeleDrive v5.0 — Telegram → Google Drive (native Colab)"

PACKAGE_ROOT = Path(__file__).resolve().parent.parent  # python-package/
REPO_ROOT = PACKAGE_ROOT.parent
NOTEBOOK_PATHS = (
    PACKAGE_ROOT / "notebook" / "TeleDrive.ipynb",
    REPO_ROOT / "public" / "TeleDrive.ipynb",
)
CELLS_JSON = Path(__file__).resolve().parent / "colab_cells.json"

HEADER_MARKDOWN = f"""# {TITLE}

Run the cells top to bottom after every **new** Colab VM (cells 1–4).
A dead runtime wipes `/content` — the last cell alone cannot revive the app.

* Store `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` once in Colab Secrets
  (left sidebar key icon). Cell 3 reads them; it only prompts if a secret
  is missing **and** this Drive account has no saved Telegram session.
  Secrets stay in your Google account, never in this notebook.
* After the first successful Telegram login, press **Save Telegram sign-in
  to Drive** in the UI. The next VM on the **same Drive account** restores
  `telegram.session` plus the stored credentials automatically — no API
  re-entry and no new Telegram code. A different Drive account does not
  restore. Logout / Forget deletes that saved sign-in.
* Google Drive auth is **native Colab** — usually one click on a new VM.
  No desktop OAuth JSON and no pasted authorization code.
* Cell 4 starts a keep-alive (2-min heartbeat + Connect click). It delays
  idle disconnect; it does **not** beat the 12-hour free cap or a closed tab.
* The interface runs **locally in this runtime** (`share=False`).
* The database and temporary files live on local `/content`; only finished
  uploads and the session vault go to Google Drive.
* Cell 1 first runs an integrity-verified update check against the pinned
  release manifest. The tested Drive ZIP remains the fallback.
"""

CELL_1_PACKAGE_UPDATER = '''# ==== Cell 1: verified package update gate + restore + pinned dependencies ====
# Pre-bootstrap order: the update gate first (BEFORE any `import teledrive`
# and before extraction), then the archived-ZIP restore (unchanged, still the
# sanctioned fallback), then the requirements.lock install.
#
# The gate is fail-closed and side-effect free on refusal:
#   * REFUSED when any teledrive module is already imported — a loaded
#     ApplicationContext / event loop / UI is never hot-swapped. Use
#     Runtime > Restart runtime, then re-run Cell 1 for a clean update.
#   * the versioned manifest (release tag + commit + sha256 + size) comes
#     from the pinned GitHub RELEASE of the canonical repo — a stable public
#     endpoint, NOT an ephemeral Actions artifact URL;
#   * archives download to updater-owned .part files only;
#   * bytes are verified against the manifest digest BEFORE anything changes
#     (digest or size mismatch => the current package is never touched);
#   * replacement is atomic (os.replace on the same filesystem) and touches
#     ONLY /content/teledrive_v4.5.zip and /content/teledrive-v4.5/;
#   * /content/teledrive_runtime, SQLite, checkpoints, logs, quarantine and
#     every Drive file are never touched;
#   * REFUSED is never fatal: resolve_package_zip() below still restores the
#     tested archive (Drive copy or official CI-artifact wrapper) as before.
import datetime
import hashlib, json, os, pathlib, sys, tempfile, urllib.request, zipfile

PKG_RELEASE_TAG = "pkg-2026.08.09-m15t07"
PKG_RELEASE_BASE = (
    "https://github.com/body199-cmyk/drive-buddy-3579bf74"
    "/releases/download/" + PKG_RELEASE_TAG + "/"
)
PKG_MANIFEST_URL = PKG_RELEASE_BASE + "teledrive_manifest.json"
PKG_ARCHIVE_ROOT = "teledrive-v4.5"
PKG_INNER_NAME = "teledrive_v4.5.zip"
PKG_STATE_NAME = "teledrive_package_state.json"
PKG_MAX_MANIFEST_BYTES = 64 * 1024
PKG_MAX_ARCHIVE_BYTES = 512 * 1024 * 1024


def _pkg_short(value, length=12):
    text = str(value or "")
    return text[:length] if text else "-"


def _pkg_runtime_refusal_reason():
    loaded = [
        name for name in sys.modules
        if name == "teledrive" or name.startswith("teledrive.")
    ]
    if loaded:
        return "runtime already loaded (%d teledrive module(s) imported)" % len(loaded)
    return None


def _pkg_fetch(url, timeout=30):
    request = urllib.request.Request(url, headers={"User-Agent": "teledrive-update-check"})
    return urllib.request.urlopen(request, timeout=timeout)  # caller closes


def _pkg_load_manifest(fetch, manifest_url):
    with fetch(manifest_url) as response:
        payload = response.read(PKG_MAX_MANIFEST_BYTES + 1)
    if len(payload) > PKG_MAX_MANIFEST_BYTES:
        raise ValueError("manifest too large")
    manifest = json.loads(payload.decode("utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("manifest is not an object")
    return manifest


def _pkg_manifest_is_trusted(manifest):
    digest = manifest.get("sha256")
    url = manifest.get("archive_url")
    size = manifest.get("size_bytes")
    return (
        manifest.get("schema") == 1
        and isinstance(manifest.get("release"), str)
        and bool(manifest.get("release"))
        and isinstance(digest, str)
        and len(digest) == 64
        and all(char in "0123456789abcdef" for char in digest)
        and isinstance(url, str)
        and url.startswith(PKG_RELEASE_BASE)
        and isinstance(size, int)
        and 0 < size <= PKG_MAX_ARCHIVE_BYTES
    )


def _pkg_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pkg_is_tested_archive(path):
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
    except (OSError, zipfile.BadZipFile):
        return False
    prefix = PKG_ARCHIVE_ROOT + "/"
    return any(name.startswith(prefix) for name in names) and (
        prefix + "requirements.lock" in names
    )


def _pkg_members_are_safe(names):
    for name in names:
        pure = pathlib.PurePosixPath(name)
        if pure.is_absolute() or "\\\\" in name or ".." in pure.parts:
            return False
    return True


def _pkg_remove_tree(path):
    # Updater-owned targets only; an explicit walk so no blind-wipe helper
    # ever appears in this notebook.
    path = pathlib.Path(path)
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    for root, dirnames, filenames in os.walk(path, topdown=False, followlinks=False):
        for filename in filenames:
            os.remove(os.path.join(root, filename))
        for dirname in dirnames:
            candidate = os.path.join(root, dirname)
            if os.path.islink(candidate):
                os.remove(candidate)
            else:
                os.rmdir(candidate)
    os.rmdir(path)


def _pkg_quiet_remove(path):
    try:
        _pkg_remove_tree(path)
    except OSError:
        pass


def _pkg_cleanup_leftovers(local_root):
    for pattern in ("." + PKG_INNER_NAME + ".*.part", ".teledrive_pkg_staging_*"):
        for leftover in local_root.glob(pattern):
            _pkg_quiet_remove(leftover)
    stale_state = local_root / (PKG_STATE_NAME + ".part")
    if stale_state.exists() or stale_state.is_symlink():
        _pkg_quiet_remove(stale_state)


def _pkg_download_verified(url, expected_size, expected_digest, fetch, part_path):
    digest = hashlib.sha256()
    total = 0
    with fetch(url) as response:
        with open(part_path, "wb") as handle:
            while True:
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                digest.update(chunk)
                total += len(chunk)
    return total == expected_size and digest.hexdigest() == expected_digest


def _pkg_stage_extraction(zip_path, local_root):
    staging = pathlib.Path(tempfile.mkdtemp(prefix=".teledrive_pkg_staging_", dir=str(local_root)))
    try:
        with zipfile.ZipFile(zip_path) as archive:
            names = archive.namelist()
            if not _pkg_members_are_safe(names):
                raise ValueError("unsafe member name in verified archive")
            archive.extractall(staging)
    except (OSError, ValueError, zipfile.BadZipFile):
        _pkg_quiet_remove(staging)
        raise
    if not (staging / PKG_ARCHIVE_ROOT).is_dir():
        _pkg_quiet_remove(staging)
        raise ValueError("archive root %s missing" % PKG_ARCHIVE_ROOT)
    return staging


def _pkg_state_read(local_root):
    try:
        state = json.loads((local_root / PKG_STATE_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return state if isinstance(state, dict) else None


def _pkg_state_write(local_root, manifest):
    state = {
        "schema": 1,
        "release": manifest["release"],
        "commit": str(manifest.get("commit") or ""),
        "product_version": str(manifest.get("product_version") or ""),
        "sha256": manifest["sha256"],
        "archive_url": manifest["archive_url"],
        "installed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    }
    tmp = local_root / (PKG_STATE_NAME + ".part")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
    os.replace(tmp, local_root / PKG_STATE_NAME)
    return state


def _pkg_state_line(local_root):
    state = _pkg_state_read(local_root)
    if state and state.get("release") and state.get("sha256"):
        return "%s commit=%s sha256=%s" % (
            state["release"],
            _pkg_short(state.get("commit")),
            _pkg_short(state["sha256"]),
        )
    return "(no verified-release record; the archived-ZIP fallback is active)"


def _pkg_refused(reason, emit):
    line = "Package update: REFUSED %s; current package unchanged" % reason
    emit(line)
    return {"outcome": "refused", "reason": reason, "line": line}


def pkg_try_update(local_root, manifest_url=PKG_MANIFEST_URL, fetch=None, emit=print):
    """One fail-closed update check; always prints exactly ONE redacted line.

    Outcomes: 'already-current' | 'success' | 'refused'. Nothing mutates the
    installed package unless the bytes matched the pinned manifest digest.
    """
    local_root = pathlib.Path(local_root)
    fetch = fetch or _pkg_fetch
    _pkg_cleanup_leftovers(local_root)

    reason = _pkg_runtime_refusal_reason()
    if reason is not None:
        return _pkg_refused(reason + "; restart the runtime, then re-run Cell 1", emit)
    try:
        manifest = _pkg_load_manifest(fetch, manifest_url)
    except Exception:
        return _pkg_refused("update endpoint unreachable", emit)
    if not _pkg_manifest_is_trusted(manifest):
        return _pkg_refused("untrusted or incomplete manifest", emit)

    release = manifest["release"]
    digest = manifest["sha256"]
    size = manifest["size_bytes"]
    package_zip = local_root / PKG_INNER_NAME
    package_dir = local_root / PKG_ARCHIVE_ROOT
    state = _pkg_state_read(local_root)
    state_matches = (
        bool(state)
        and state.get("sha256") == digest
        and state.get("release") == release
    )
    zip_matches = (
        package_zip.is_file()
        and _pkg_is_tested_archive(package_zip)
        and _pkg_sha256(package_zip) == digest
    )
    if state_matches and zip_matches and package_dir.is_dir():
        line = "Package update: ALREADY CURRENT %s commit=%s sha256=%s" % (
            release, _pkg_short(manifest.get("commit")), _pkg_short(digest))
        emit(line)
        return {
            "outcome": "already-current",
            "release": release,
            "sha256": digest,
            "line": line,
        }

    part_path = None
    staging = None
    committed = False
    try:
        source_zip = package_zip
        if not zip_matches:
            fd, part_name = tempfile.mkstemp(
                prefix="." + PKG_INNER_NAME + ".",
                suffix=".part",
                dir=str(local_root),
            )
            os.close(fd)
            part_path = pathlib.Path(part_name)
            try:
                verified = _pkg_download_verified(
                    manifest["archive_url"], size, digest, fetch, part_path)
            except Exception:
                verified = None
            if verified is None:
                _pkg_quiet_remove(part_path)
                return _pkg_refused("archive download failed", emit)
            if not verified:
                _pkg_quiet_remove(part_path)
                return _pkg_refused("downloaded bytes failed digest/size verification", emit)
            if not _pkg_is_tested_archive(part_path):
                _pkg_quiet_remove(part_path)
                return _pkg_refused("verified archive has an unexpected layout", emit)
            source_zip = part_path
        staging = _pkg_stage_extraction(source_zip, local_root)
        if not zip_matches:
            os.replace(part_path, package_zip)  # atomic archive replacement
            part_path = None
        committed = True
        if package_dir.exists() or package_dir.is_symlink():
            _pkg_remove_tree(package_dir)  # ONLY the previous package directory
        os.replace(staging / PKG_ARCHIVE_ROOT, package_dir)  # atomic dir rename
        _pkg_quiet_remove(staging)
        staging = None
        _pkg_state_write(local_root, manifest)
        line = "Package update: SUCCESS %s commit=%s sha256=%s" % (
            release, _pkg_short(manifest.get("commit")), _pkg_short(digest))
        emit(line)
        return {"outcome": "success", "release": release, "sha256": digest, "line": line}
    except Exception as exc:  # the gate must never break the cell or the fallback
        for leftover in (part_path, staging):
            if leftover is not None:
                leftover = pathlib.Path(leftover)
                if leftover.exists() or leftover.is_symlink():
                    _pkg_quiet_remove(leftover)
        if committed:
            return _pkg_refused(
                "swap interrupted (%s); runtime data untouched — re-run Cell 1 to converge"
                % type(exc).__name__,
                emit,
            )
        return _pkg_refused("replacement refused (%s)" % type(exc).__name__, emit)
'''

CELL_1_RESTORE = '''# ---- restore the tested archive (sanctioned fallback + CI-artifact unwrap) ----
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

# Pre-bootstrap update check. Prints ONE line (SUCCESS / ALREADY CURRENT /
# REFUSED); REFUSED never aborts the cell — the fallback below still restores.
pkg_try_update(LOCAL_ROOT)

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
print(\"package reference:\", _pkg_state_line(LOCAL_ROOT))
print(\"runtime root (local, not Drive):\", os.environ.setdefault(
    \"TELEDRIVE_ROOT\", \"/content/teledrive_runtime\"))
'''

# Assembled Cell 1: verified update gate + fallback restore. One source, no drift.
CELL_1 = CELL_1_PACKAGE_UPDATER + CELL_1_RESTORE

CELL_2 = '''# ==== Cell 2: bootstrap local directories, logging, SQLite migrations, WAL ====
import os
os.environ.setdefault("TELEDRIVE_ROOT", "/content/teledrive_runtime")

from teledrive import bootstrap

ctx = bootstrap.run()          # the ONE ApplicationContext for this runtime
print("schema version:", ctx.bootstrap_info["schema_version"])
print("free bytes on local disk:", ctx.bootstrap_info["free_bytes"])
print("journal mode:", ctx.db.journal_mode())
'''

CELL_3 = '''# ==== Cell 3: native Colab Drive auth + optional Telegram vault probe ====
# Drive is connected FIRST. If this Drive account already has a saved
# Telegram session (telegram.session + telegram_creds.json in TeleDrive_AppData),
# manual API input is skipped. Otherwise Colab Secrets are preferred, then a
# hidden prompt for THIS runtime only. Values are never printed or logged.

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

from teledrive.session_vault import SessionVault

probe = SessionVault(ctx).probe(drive_service)
api_id = ""
api_hash = ""
phone = probe.get("phone", "")
cred_source = "hidden prompt"

if probe.get("has_session") and probe.get("has_creds"):
    print("saved Telegram session found for:", probe.get("phone_label") or "(hidden)")
    print("manual Telegram API input skipped for this Drive account")
else:
    print("no saved Telegram session found for this Drive account")
    try:
        from google.colab import userdata as _td_userdata
        try:
            api_id = str(_td_userdata.get("TELEGRAM_API_ID") or "").strip()
        except Exception:
            api_id = ""
        try:
            api_hash = str(_td_userdata.get("TELEGRAM_API_HASH") or "").strip()
        except Exception:
            api_hash = ""
        if api_id.isdigit() and api_hash:
            cred_source = "Colab Secrets"
    except Exception:
        pass

    if not (api_id.isdigit() and api_hash):
        import getpass
        if not api_id.isdigit():
            api_id = getpass.getpass("Telegram API ID (hidden): ").strip()
        if not api_hash:
            api_hash = getpass.getpass("Telegram API Hash (hidden): ").strip()
        if not phone:
            phone = getpass.getpass("Telegram phone (hidden, international format): ").strip()

    assert api_id.isdigit() and api_hash, "API ID must be numeric and API Hash non-empty"
    print("telegram credentials: loaded from", cred_source)
'''

CELL_4 = '''# ==== Cell 4: inject into the ONE context, attempt restore, launch the UI ====
# No second context, no second event loop, no second Telegram client, no second
# Drive service. Everything below reuses the objects created in cells 2 and 3.
# Drive is adopted FIRST so the session vault can restore telegram.session
# before set_credentials; an existing session skips phone / OTP / 2FA.
from teledrive.app import launch
from teledrive import session_vault

ctx.drive_auth.adopt_service(drive_service)           # already verified above
print("drive status:", ctx.drive_auth.status().state)

if api_id and api_hash:
    restored = session_vault.restore_from_context(ctx, secret=api_hash)
    print("telegram session vault:", "restored" if restored else "empty (first login or new account)")
    ctx.telegram_auth.set_credentials(api_id, api_hash)   # secrets stay in memory
    del api_id, api_hash
    print("telegram credentials loaded into runtime memory")
    print("telegram status:", ctx.telegram_auth.status().state)
else:
    restored = ctx.session_vault.autorestore()
    print("telegram restore:", restored.message_key)

ctx.checkpoints.restore_and_reconcile()               # safe state, no auto-resume

# share=False: the UI is reachable inside this runtime only. A public link is an
# explicit opt-in (pass share to launch yourself) and is never the default —
# no Gradio public tunnel is created and no secrets are exposed.
# inline=False + the official Colab proxy: launch() binds 0.0.0.0:7860, obtains
# the official google.colab.kernel.proxyPort(7860) URL, seeds Gradio's root_path
# with it so /config, events, assets and queue resolve through the proxy (not
# localhost), and prints ONE usable "TeleDrive URL:" line below. A clickable
# external proxy URL is preferred over a fragile inline iframe.
# blocking=False: the cell returns immediately, so cells 5-7 (handoff, tests,
# maintenance) stay runnable while the interface keeps serving. The launch
# handle lives on ctx.ui and is closed by ctx.shutdown() in cell 7.
launch(ctx, share=False, inline=False, blocking=False)
session_vault.start_keepalive()
print("keep-alive started (2-min heartbeat + Connect click); a closed tab can still idle-out")
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
    {"title": "Verify/update the package, restore and install pinned dependencies", "code": CELL_1},
    {"title": "Bootstrap directories, logging, SQLite migrations and WAL", "code": CELL_2},
    {"title": "Telegram credentials (Colab Secrets or hidden) and native Drive auth", "code": CELL_3},
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
