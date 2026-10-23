"""Single authoritative source for the TeleDrive v4.5 Colab notebook.

Both notebook copies are GENERATED from this module:

    python -m teledrive.notebook_cells --write

writes, byte-identically:

    python-package/notebook/TeleDrive.ipynb
    public/TeleDrive.ipynb

and refreshes ``teledrive/colab_cells.json`` so the in-app "copy the cells"
export can never drift from the shipped notebook.

Constitution rules encoded here:
  * exactly seven required cells plus two optional keep-alive start/stop cells;
  * native Colab Drive auth only (no client_secret.json, no pasted OAuth code,
    no persisted drive_token.json);
  * ``share=False`` — no public tunnel by default;
  * exactly one ApplicationContext, one async runtime, one Telegram client and
    one Drive service, all created in cell 4 and reused afterwards;
  * SQLite and temp files stay on local ``/content``, never on mounted Drive;
  * no blind ``rmtree(TEMP_DIR)`` — maintenance deletes only temp files that
    belong to verified Uploaded items and quarantines everything unknown;
  * cell 1 runs a pre-bootstrap integrity-verified update gate (latest/pinned
    release manifest + sha256, ``.part``-only downloads, atomic swap). Any
    REFUSED outcome stops the cell before local ZIP fallback; this is required
    to guarantee the notebook never silently starts from an unverified stale package.
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

HEADER_MARKDOWN = f"""<details><summary>📘 دليل التشغيل والإعدادات — اضغط للتوسيع / Expand guide</summary>

# {TITLE}

Run cells 1–5 in order after every **new** Colab VM. Cell 5 attempts the optional Vercel handoff; if it fails, the local UI still runs.
A dead runtime wipes `/content` — the last cell alone cannot revive the app.

> 💡 **واجهة مبسطة لغير المبرمجين / Friendly view for non-coders**
> كل خلية الآن تظهر كـ **كارت بعنوان واضح** والكود مخفي افتراضيًا — سترى فقط الوظيفة (مثل "تثبيت الحزمة" أو "تشغيل الواجهة").
> اضغط زر التشغيل ▶️ بجانب كل عنوان لتنفيذه بالترتيب. إذا أردت رؤية الكود، اضغط **Show code / عرض الكود** بجانب العنوان — لا تحتاج لإخفائه يدويًا كل مرة، فهو يبقى مخفيًا تلقائيًا عند فتح النوت‌بوك.
> Every cell now shows as a **titled card** with the code hidden by default — you only see what it does. Press ▶️ to run in order; click **Show code** near the title only if you want to inspect the code.

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
* Cell 4 has a **UI_MODE** dropdown: `Modern_Web_Dashboard` (FastAPI +
  AJAX Polling, port 8765), `Classic_Gradio_Backup` (port 7860), or
  `Run_Both_Together` — the default, so both interfaces (and their two
  printed URLs) come up together. Telegram login secrets are only ever
  typed into the Gradio fields, never into the Web Dashboard.
* Cell 4 starts the UI; Cell 5 attempts the optional Vercel handoff. Cell 11 is the
  live download monitor: run it after starting downloads (you can run it directly
  after Cell 4 without executing cleanup). Do **not** run Cell 8 until downloads
  finish, because it shuts down the app. Optional Cell 9 starts best-effort keep-alive;
  Cell 10 stops it. The monitor/wake lock cannot override Colab's runtime limits.
* The interface runs **locally in this runtime** (`share=False`).
* The database and temporary files live on local `/content`; only finished
  uploads and the session vault go to Google Drive.
* Cell 1 first runs an integrity-verified update check against the pinned
  release manifest. The tested Drive ZIP remains the fallback.

## 🔐 ربط الموقع بـ Vercel (خطوة اختيارية)

لو فتحت صفحة TeleDrive على Vercel وطلبت **رمز الربط السري**، فالرمز ليس كلمة مرور Google ولا تحتاج إلى إنشائه بنفسك.

1. شغّل الخلايا 1–4 بالترتيب. بعد تشغيل الواجهة، نفّذ **الخلية 5: الربط التلقائي مع Vercel**.
2. الخلية 5 تحاول إنشاء نفق HTTPS مؤقت وتعرض زر **Open Vercel Dashboard**. اضغطه لفتح الموقع وربطه تلقائيًا دون نسخ الرمز.
3. لو فشل النفق أو التحويل، استخدم الربط اليدوي أدناه: انسخ `TeleDrive Web Dashboard URL` ورمز `TeleDrive pairing token` من مخرجات الخلية 4.
4. افتح صفحة `/connect` في Vercel والصق الرابط والرمز في الخانتين.

**تنبيه أمان:** رابط الربط التلقائي يحتوي رمزًا سريًا داخل جزء الرابط (#). لا تشاركه ولا تنشر صورة له. النفق مؤقت ويتوقف إذا انتهت جلسة Colab أو توقفت العملية؛ لا توجد آلية مجانية تضمن بقاء Colab متصلًا دائمًا.

</details>"""

CELL_1_PACKAGE_UPDATER = '''# ==== Cell 1: verified package update gate + restore + pinned dependencies ====
# Pre-bootstrap order: the update gate first (BEFORE any `import teledrive`
# and before extraction), then the archived-ZIP restore (unchanged, still the
# sanctioned fallback), then the requirements.lock install.
#
# The gate is fail-closed and stops Cell 1 on every refusal:
#   * no ApplicationContext / event loop / UI is ever hot-swapped;
#   * an unverified endpoint, manifest, archive size or SHA-256 never falls
#     through to an older local/Drive ZIP;
#   * if modules are already loaded, restart the runtime before retrying.
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
#   * any REFUSED result stops Cell 1 before local/Drive ZIP fallback; if the
#     latest package cannot be verified, the notebook fails visibly instead
#     of claiming or silently using an older cached package.
import datetime
import hashlib, json, os, pathlib, sys, tempfile, urllib.request, zipfile

PKG_RELEASE_TAG = "pkg-2026.08.09-m15t07"
PKG_RELEASE_BASE = (
    "https://github.com/body199-cmyk/drive-buddy-3579bf74"
    "/releases/download/" + PKG_RELEASE_TAG + "/"
)
PKG_MANIFEST_URL = PKG_RELEASE_BASE + "teledrive_manifest.json"
PKG_LATEST_API_URL = (
    "https://api.github.com/repos/body199-cmyk/drive-buddy-3579bf74"
    "/releases/latest"
)
PKG_LATEST_PAGE_URL = (
    "https://github.com/body199-cmyk/drive-buddy-3579bf74"
    "/releases/latest"
)
_PKG_TAG_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-"
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
    # GitHub release assets are replaced IN PLACE under the stable tag. Some
    # Colab/mobile/CDN paths cache old bytes for that unchanged URL, making a
    # correct publication appear stale. A unique query parameter and explicit
    # no-cache headers force each request to revalidate manifests and ZIPs.
    # Manifest validation still checks the canonical archive_url and the
    # downloaded bytes against the manifest size and SHA-256.
    import time
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query.append(("_td_cache_bust", str(time.time_ns())))
    fresh_url = urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )
    request = urllib.request.Request(
        fresh_url,
        headers={
            "User-Agent": "teledrive-update-check",
            "Cache-Control": "no-cache, no-store, max-age=0",
            "Pragma": "no-cache",
        },
    )
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


def _pkg_release_base(tag):
    return (
        "https://github.com/body199-cmyk/drive-buddy-3579bf74"
        "/releases/download/" + tag + "/"
    )


def _pkg_tag_is_valid(tag):
    return (
        isinstance(tag, str)
        and tag.startswith("pkg-")
        and 4 < len(tag) <= 80
        and all(char in _PKG_TAG_CHARS for char in tag)
    )


def _pkg_latest_manifest_url(fetch, api_url):
    """Resolve the newest pkg-* release via the public GitHub API.

    Returns (manifest_url, tag) with the URL CONSTRUCTED from the validated
    tag — never taken from the API payload. Raises on anything unexpected so
    the caller falls back to the pinned release."""
    with fetch(api_url) as response:
        payload = response.read(1024 * 1024 + 1)
    if len(payload) > 1024 * 1024:
        raise ValueError("latest-release payload too large")
    info = json.loads(payload.decode("utf-8"))
    tag = info.get("tag_name") if isinstance(info, dict) else None
    if not _pkg_tag_is_valid(tag):
        raise ValueError("latest release is not a pkg-* release")
    return _pkg_release_base(tag) + "teledrive_manifest.json", tag


def _pkg_latest_tag_via_redirect(fetch, page_url):
    """Resolve the newest release tag WITHOUT the GitHub API.

    ``github.com/<repo>/releases/latest`` redirects to
    ``.../releases/tag/<tag>``; urllib follows the redirect and exposes
    the final URL. This path has no API rate limit — shared Colab NAT
    IPs routinely exhaust the unauthenticated 60/hour API quota, which
    used to drop this gate silently onto the ancient pinned package
    (M46-T03). Returns the validated tag; raises on anything else."""
    with fetch(page_url) as response:
        final_url = response.geturl() if hasattr(response, "geturl") else ""
    marker = "/releases/tag/"
    if marker not in str(final_url):
        raise ValueError("latest-release page did not redirect to a tag")
    tag = str(final_url).split(marker, 1)[1].split("/")[0].split("?")[0]
    if not _pkg_tag_is_valid(tag):
        raise ValueError("latest release is not a pkg-* release")
    return tag


def _pkg_manifest_rank(manifest):
    """Comparable build order between two trusted manifests.

    Publishing workflows stamp each manifest with ``build_run_id`` (the
    GitHub Actions run id — monotonically increasing); legacy manifests
    without the field rank 0. A stable tag refreshed in place keeps its
    old creation date, so "/releases/latest" (newest by creation) can
    point at an OLDER build than the pinned tag. Ranking lets the gate
    install whichever trusted manifest was actually built later."""
    try:
        return int(manifest.get("build_run_id") or 0)
    except (TypeError, ValueError):
        return 0


def _pkg_manifest_is_trusted(manifest, expected_tag=None):
    digest = manifest.get("sha256")
    url = manifest.get("archive_url")
    size = manifest.get("size_bytes")
    release = manifest.get("release")
    if expected_tag is None:
        expected_tag = PKG_RELEASE_TAG
    return (
        manifest.get("schema") == 1
        and _pkg_tag_is_valid(release)
        and release == expected_tag
        and isinstance(digest, str)
        and len(digest) == 64
        and all(char in "0123456789abcdef" for char in digest)
        and isinstance(url, str)
        and url.startswith(_pkg_release_base(release))
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


def pkg_try_update(local_root, manifest_url=PKG_MANIFEST_URL, fetch=None,
                   emit=print, latest_api_url=PKG_LATEST_API_URL,
                   latest_page_url=PKG_LATEST_PAGE_URL):
    """One fail-closed update check; always prints exactly ONE redacted line.

    Manifest resolution: the newest pkg-* GitHub release (public API
    first, then the rate-limit-free /releases/latest redirect) AND the
    pinned release are both consulted; when both are trusted, the one
    built later (``build_run_id``) wins — a tie keeps the
    latest-resolved one. Outcomes: 'already-current' | 'success' |
    'refused'. Nothing mutates the installed package unless the bytes
    matched the chosen manifest's digest.
    """
    local_root = pathlib.Path(local_root)
    fetch = fetch or _pkg_fetch
    _pkg_cleanup_leftovers(local_root)

    reason = _pkg_runtime_refusal_reason()
    if reason is not None:
        return _pkg_refused(reason + "; restart the runtime, then re-run Cell 1", emit)
    manifest = None
    if latest_api_url or latest_page_url:
        latest_tag = None
        if latest_api_url:
            try:
                _latest_url, latest_tag = _pkg_latest_manifest_url(
                    fetch, latest_api_url)
            except Exception:
                latest_tag = None  # API down / rate-limited: redirect next
        if latest_tag is None and latest_page_url:
            try:
                latest_tag = _pkg_latest_tag_via_redirect(fetch, latest_page_url)
            except Exception:
                latest_tag = None
        if latest_tag is not None:
            try:
                candidate = _pkg_load_manifest(
                    fetch,
                    _pkg_release_base(latest_tag) + "teledrive_manifest.json")
                if _pkg_manifest_is_trusted(candidate, latest_tag):
                    manifest = candidate
            except Exception:
                manifest = None
    # The pinned manifest is consulted even when a latest candidate is
    # already trusted: "latest" is newest by CREATION date, so a pinned
    # stable tag refreshed in place can carry a newer build than the
    # latest-created release. _pkg_manifest_rank decides; a pinned
    # fetch failure never discards a trusted latest candidate.
    pinned = None
    pinned_untrusted = False
    try:
        pinned_candidate = _pkg_load_manifest(fetch, manifest_url)
        if _pkg_manifest_is_trusted(pinned_candidate, PKG_RELEASE_TAG):
            pinned = pinned_candidate
        else:
            pinned_untrusted = True
    except Exception:
        pinned = None
    if manifest is not None and pinned is not None:
        if _pkg_manifest_rank(pinned) > _pkg_manifest_rank(manifest):
            manifest = pinned
    elif manifest is None:
        if pinned is None:
            if pinned_untrusted:
                return _pkg_refused("untrusted or incomplete manifest", emit)
            return _pkg_refused("update endpoint unreachable", emit)
        manifest = pinned

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
    except Exception as exc:  # return REFUSED; Cell 1 stops before ZIP restore
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

# Pre-bootstrap update check. NEVER fall through to a cached Drive/local ZIP
# after REFUSED: endpoint failures, untrusted manifests, digest mismatches and
# a loaded runtime all mean we cannot prove that the package is current.
# Fix connectivity/manifest issues or restart the runtime, then rerun Cell 1.
PACKAGE_UPDATE_RESULT = pkg_try_update(LOCAL_ROOT)
if PACKAGE_UPDATE_RESULT.get("outcome") == "refused":
    raise RuntimeError(
        "TeleDrive package update could not verify the latest published package: "
        + str(PACKAGE_UPDATE_RESULT.get("reason", "unknown reason"))
        + ". No cached ZIP was restored. Check the connection; if TeleDrive "
        "modules were already imported, use Runtime > Restart session, then "
        "run Cells 1–4 again."
    )

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
# Drive is connected FIRST. A current Drive-managed vault contains the API
# credentials needed only inside this local runtime, so the same Drive account
# restores Telegram after Restart without Colab Secrets, phone or OTP. Legacy
# format-2 vaults remain supported and ask only for their unwrap credential so
# the app can migrate them after a successful restore. Values are never printed
# or logged.

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
has_saved_vault = bool(probe.get("has_session") and probe.get("has_creds"))
api_id = str(probe.get("api_id") or "").strip()
api_hash = str(probe.get("api_hash") or "").strip()
phone = probe.get("phone", "")
cred_source = "Drive-managed vault" if bool(probe.get("drive_managed")) else "hidden prompt"

# Legacy format-2 vaults intentionally omit API Hash from Drive. Colab Secrets
# are an optional migration aid, not a requirement for the new Drive-managed
# format. Values stay in runtime memory only and are never printed.
try:
    from google.colab import userdata as _td_userdata
    try:
        secret_api_id = str(_td_userdata.get("TELEGRAM_API_ID") or "").strip()
    except Exception:
        secret_api_id = ""
    try:
        secret_api_hash = str(_td_userdata.get("TELEGRAM_API_HASH") or "").strip()
    except Exception:
        secret_api_hash = ""
    if secret_api_id.isdigit():
        api_id = secret_api_id
    if secret_api_hash:
        api_hash = secret_api_hash
    if secret_api_id.isdigit() and secret_api_hash:
        cred_source = "Colab Secrets"
except Exception:
    pass

if has_saved_vault:
    print("saved Telegram session found for:", probe.get("phone_label") or "(hidden)")
    if bool(probe.get("drive_managed")):
        print("Telegram restore source: Drive-managed vault (no Colab Secret required)")
    else:
        print("Telegram restore source: legacy vault; API Hash is needed once to migrate")
else:
    print("no saved Telegram session found for this Drive account")

if not (api_id.isdigit() and api_hash):
    import getpass
    if not api_id.isdigit():
        api_id = getpass.getpass("Telegram API ID (hidden): ").strip()
    if not api_hash:
        api_hash = getpass.getpass("Telegram API Hash (hidden): ").strip()
    if not has_saved_vault and not phone:
        phone = getpass.getpass("Telegram phone (hidden, international format): ").strip()

assert api_id.isdigit() and api_hash, "API ID must be numeric and API Hash non-empty"
print("telegram credentials: loaded from", cred_source)
'''

CELL_4 = '''# ==== Cell 4: inject into the ONE context, attempt restore, launch the UI ====
# No second context, no second application event loop, no second Telegram
# client, no second Drive service. Everything below reuses the objects
# created in cells 2 and 3; each UI's HTTP server stays isolated in its
# own framework thread so a web-server failure can never take the
# Telegram/transfer loop down with it (M46-T02).
# Drive is adopted FIRST so the session vault can restore telegram.session
# before set_credentials; an existing session skips phone / OTP / 2FA.
from teledrive.app import launch
from teledrive import session_vault

ctx.drive_auth.adopt_service(drive_service)           # already verified above
print("drive status:", ctx.drive_auth.status().state)

if api_id and api_hash:
    restored = session_vault.restore_from_context(ctx, secret=api_hash)
    print("telegram session vault:", "restored" if restored else "not restored; manual login remains available")
    if not restored:
        ctx.telegram_auth.set_credentials(api_id, api_hash)   # runtime memory only
    del api_id, api_hash
    print("telegram credentials loaded into runtime memory")
    print("telegram status:", ctx.telegram_auth.status().state)
else:
    restored = ctx.session_vault.autorestore()
    print("telegram restore:", restored.message_key)

ctx.checkpoints.restore_and_reconcile()               # safe state, no auto-resume

# UI_MODE (Cell 4 dropdown): pick the interface — both run on the ONE
# context / event loop / Telegram client / Drive service created above.
#   Modern_Web_Dashboard  : FastAPI + AJAX Polling page (port 8765),
#                           live metrics about once a second, no refresh.
#   Classic_Gradio_Backup : the original Gradio UI (port 7860).
#   Run_Both_Together     : both (DEFAULT since M46-T03); secure
#                           Telegram login fields live in Gradio, so
#                           the modern-only mode is a dead end until a
#                           saved session restores as "connected".
UI_MODE = "Run_Both_Together"  # @param ["Modern_Web_Dashboard", "Classic_Gradio_Backup", "Run_Both_Together"]
WEB_DASHBOARD_PORT = 8765  # @param {type:"integer"}

# share=False: the UI is reachable inside this runtime only. A public link is an
# explicit opt-in (pass share to launch yourself) and is never the default —
# no Gradio public tunnel is created and no secrets are exposed.
# inline=False + the official Colab proxy: launch() binds 0.0.0.0:7860, obtains
# the official google.colab.kernel.proxyPort(7860) URL, seeds Gradio's root_path
# with it so /config, events, assets and queue resolve through the proxy (not
# localhost), and prints ONE usable "TeleDrive URL:" line below. A clickable
# external proxy URL is preferred over a fragile inline iframe.
# blocking=False: the cell returns immediately (non-blocking), so cells 5-7
# (session report, health check, cleanup) remain available while the interface keeps
# serving. The Gradio handle lives on ctx.ui, the Web Dashboard handle on
# ctx.web_dashboard; both are closed by ctx.shutdown() in cell 7.
# Classic Gradio launches FIRST (M46-T02): it is the recovery surface, so
# nothing the modern dashboard does during its own startup can ever delay
# or prevent it. launch() is idempotent — re-running this cell while the
# UI is already serving re-prints its URL instead of crashing on the port.
print("selected UI_MODE:", UI_MODE)
_classic_launched = False
if UI_MODE in ("Classic_Gradio_Backup", "Run_Both_Together"):
    try:
        launch(ctx, share=False, inline=False, blocking=False)
        _classic_launched = True
    except Exception as _classic_exc:
        # A stale/busy Gradio port must not prevent Modern Web from coming
        # up in Run_Both_Together; report the exact cause and keep going.
        print("⚠️ Classic Gradio unavailable:", type(_classic_exc).__name__, _classic_exc)

web_server = None
if UI_MODE in ("Modern_Web_Dashboard", "Run_Both_Together"):
    try:
        from teledrive.web_dashboard import launch_web_dashboard

        # Returns only after the server is really listening; on failure it
        # raises with the concrete reason (missing module / busy port / ...).
        web_server = launch_web_dashboard(ctx, port=WEB_DASHBOARD_PORT)
        print("web dashboard: OK on port", WEB_DASHBOARD_PORT)
    except Exception as _web_exc:  # never leave the user with no UI at all
        print("⚠️ web dashboard unavailable:", type(_web_exc).__name__, _web_exc)
        if isinstance(_web_exc, ModuleNotFoundError):
            print(
                "⚠️ الحزمة المثبتة قديمة ولا تحتوي الواجهة الحديثة. "
                "الحل: Runtime > Restart runtime ثم أعد تشغيل الخلايا 1-4 من الأول "
                "(لا تشغّل هذه الخلية وحدها) بعد نشر أحدث حزمة. "
                "Stale package without the web dashboard: restart the runtime "
                "and re-run cells 1-4 from the top."
            )
        if not _classic_launched:
            print("falling back to Classic_Gradio_Backup")
            try:
                launch(ctx, share=False, inline=False, blocking=False)
                _classic_launched = True
            except Exception as _classic_fallback_exc:
                print(
                    "⚠️ Classic Gradio fallback unavailable:",
                    type(_classic_fallback_exc).__name__, _classic_fallback_exc,
                )

if _classic_launched or web_server is not None:
    print("ui running (non-blocking); use optional Cell 9 to start keep-alive and Cell 10 to stop it")
else:
    print("⚠️ no UI is serving; check the startup errors above, free ports 7860/8765, and re-run Cell 4")
'''



CELL_4B_VERCEL_HANDOFF = '''#@title ⚡ خطوة الربط التلقائي — فتح لوحة Vercel | One-click handoff
# Experimental: creates a temporary public HTTPS tunnel to this runtime.
# Only share the handoff link with yourself. The bearer token grants runtime control.
import os, re, time, queue, threading, subprocess, urllib.request, urllib.parse, html, secrets
from IPython.display import display, HTML

VERCEL_CONNECT_URL = "https://teledrive.vercel.app/connect"

if "web_server" not in globals() or web_server is None:
    print("⚠️ لا توجد واجهة ويب حديثة تعمل. الواجهة المحلية/Gradio تظل متاحة.")
else:
    try:
        _port = int(web_server.config.port)
        _token = str(getattr(ctx, "remote_control_token", "") or "")
        _expiry = float(getattr(ctx, "remote_control_token_expires_at", 0) or 0)
        if len(_token) < 32 or _expiry <= time.time():
            raise RuntimeError("رمز الربط غير متاح أو انتهت صلاحيته. أعد تشغيل الخلية 4.")

        import hashlib
        _tunnel_bin = "/content/cloudflared"
        _cloudflared_url = "https://github.com/cloudflare/cloudflared/releases/download/2026.10.2/cloudflared-linux-amd64"
        _cloudflared_sha256 = "35fbdd2beb378436c7da377d7358cea8e33f9c94a6705d1d8036bf9b0d6d8005"

        def _sha256_file(_path):
            _digest = hashlib.sha256()
            with open(_path, "rb") as _stream:
                for _chunk in iter(lambda: _stream.read(1024 * 1024), b""):
                    _digest.update(_chunk)
            return _digest.hexdigest()

        if not os.path.isfile(_tunnel_bin) or _sha256_file(_tunnel_bin) != _cloudflared_sha256:
            print("Downloading pinned Cloudflare Tunnel client (2026.10.2) and verifying SHA-256...")
            _download_tmp = _tunnel_bin + ".download"
            try:
                urllib.request.urlretrieve(_cloudflared_url, _download_tmp)
                if _sha256_file(_download_tmp) != _cloudflared_sha256:
                    raise RuntimeError("cloudflared SHA-256 mismatch; refusing to execute downloaded binary.")
                os.replace(_download_tmp, _tunnel_bin)
            finally:
                if os.path.exists(_download_tmp):
                    os.remove(_download_tmp)
        os.chmod(_tunnel_bin, 0o755)

        # Stop the previous process if this cell is run again.
        _old_tunnel = globals().get("_teledrive_tunnel")
        if _old_tunnel is not None and _old_tunnel.poll() is None:
            _old_tunnel.terminate()
            try:
                _old_tunnel.wait(timeout=5)
            except subprocess.TimeoutExpired:
                _old_tunnel.kill()
                _old_tunnel.wait(timeout=5)

        _tunnel_log = queue.Queue()
        _teledrive_tunnel = subprocess.Popen(
            [_tunnel_bin, "tunnel", "--url", f"http://127.0.0.1:{_port}", "--no-autoupdate"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        def _read_tunnel_log():
            if _teledrive_tunnel.stdout:
                for _line in _teledrive_tunnel.stdout:
                    _tunnel_log.put(_line.rstrip())

        threading.Thread(target=_read_tunnel_log, daemon=True).start()
        _tunnel_url = None
        _deadline = time.time() + 60
        while time.time() < _deadline:
            if _teledrive_tunnel.poll() is not None:
                raise RuntimeError("Cloudflare Tunnel exited before returning a URL.")
            try:
                _line = _tunnel_log.get(timeout=0.5)
            except queue.Empty:
                continue
            _match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", _line, re.I)
            if _match:
                _tunnel_url = _match.group(0)
                break

        if not _tunnel_url:
            raise RuntimeError("Timed out waiting for a Cloudflare Quick Tunnel URL.")

        _now = time.time()
        _handoffs = getattr(ctx, "remote_handoff_tokens", {})
        _handoffs = {k: v for k, v in _handoffs.items() if float(v) > _now}
        _handoff_token = secrets.token_urlsafe(32)
        _handoffs[_handoff_token] = _now + 300
        setattr(ctx, "remote_handoff_tokens", _handoffs)
        _handoff = (
            VERCEL_CONNECT_URL.split("#", 1)[0]
            + "#url=" + urllib.parse.quote(_tunnel_url, safe="")
            + "&handoff=" + urllib.parse.quote(_handoff_token, safe="")
        )
        display(HTML(
            '<div style="border:1px solid #16a34a;border-radius:12px;padding:16px;margin:12px 0">'
            '<strong style="font-size:18px">⚡ Open TeleDrive on Vercel</strong>'
            '<p>اضغط الزر للرجوع إلى لوحة التحكم. الرابط يحتوي رمزًا سريًا مؤقتًا، لا تشاركه.</p>'
            f'<a href="{html.escape(_handoff, quote=True)}" target="_blank" rel="noopener noreferrer" '
            'style="display:inline-block;background:#15803d;color:white;padding:12px 18px;border-radius:8px;text-decoration:none;font-weight:700">Open Vercel Dashboard</a></div>'
        ))
        print("Tunnel established. It will stop when this Colab runtime/process stops.")
    except Exception as _handoff_exc:
        print("⚠️ تعذر الربط التلقائي؛ الواجهة المحلية تظل متاحة ويمكنك استخدام الربط اليدوي.")
        print(type(_handoff_exc).__name__ + ":", str(_handoff_exc))
        _td_proc = globals().get("_teledrive_tunnel")
        if _td_proc is not None and _td_proc.poll() is None:
            _td_proc.terminate()
            try:
                _td_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                _td_proc.kill()
                _td_proc.wait(timeout=5)
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

_td_proc = globals().get('_teledrive_tunnel')
if _td_proc is not None and _td_proc.poll() is None:
    _td_proc.terminate()
    try:
        _td_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        _td_proc.kill()
        _td_proc.wait(timeout=5)
    print('Cloudflare tunnel stopped')

ctx.shutdown()      # closes the UI handle, stops the async runtime, closes SQLite
print("runtime closed")
'''

CELL_8_KEEPALIVE_START = '''# ==== Optional Cell 8: start the best-effort Colab keep-alive ====
# Run only after Cell 4 if you want the browser/runtime hint. Cell 9 stops the
# heartbeat, Connect timer, and silent-audio player without closing TeleDrive.
from teledrive import session_vault
from IPython.display import HTML, display
import base64, io, wave

_keepalive_result = session_vault.start_keepalive()
print("keep-alive:", "started" if _keepalive_result["started"] else _keepalive_result["reason"])

# Inline WAV, generated locally: no external URL or network request.
_silent_audio_buffer = io.BytesIO()
with wave.open(_silent_audio_buffer, "wb") as _silent_wav:
    _silent_wav.setnchannels(1)
    _silent_wav.setsampwidth(2)
    _silent_wav.setframerate(8000)
    _silent_wav.writeframes(bytes(3200))  # 0.2 seconds of PCM silence

_silent_audio_base64 = base64.b64encode(_silent_audio_buffer.getvalue()).decode("ascii")
silent_audio_code = (
    '<audio id="tdSilentAudio" controls autoplay loop muted playsinline style="width: 100%;">'
    f'<source src="data:audio/wav;base64,{_silent_audio_base64}" type="audio/wav">'
    'Your browser does not support audio playback.'
    '</audio>'
    '<script>(function () {'
    'var audio = document.getElementById("tdSilentAudio");'
    'if (!audio || typeof audio.play !== "function") return;'
    'var attempt = audio.play();'
    'if (attempt && typeof attempt.catch === "function") {'
    'attempt.catch(function () { console.log("Silent-audio autoplay was prevented; click Play once if desired."); });'
    '}'
    '})();</script>'
    '<p style="color: gray; font-size: 12px;">ℹ️ محاولة best-effort فقط؛ قد يمنع المتصفح التشغيل التلقائي، وقد تظل جلسة Colab خاضعة لمهلها وحدودها.</p>'
)
display(HTML(silent_audio_code))
'''

CELL_9_KEEPALIVE_STOP = '''# ==== Optional Cell 9: stop keep-alive and silent browser audio ====
# Safe to run while TeleDrive is open; this stops only the keep-alive helpers.
from teledrive import session_vault

_stop_result = session_vault.stop_keepalive()
print("keep-alive:", "stopped" if _stop_result["stopped"] else "not active")
print("If the audio player is still playing, press its Pause button.")
'''



CELL_10_MONITOR = '''#@title 🟢 مراقبة TeleDrive — تعمل تلقائياً طوال فترة التحميل
import sys
import time
import logging
from datetime import datetime
from IPython.display import display, HTML, clear_output

def extract_queue_counts(snap):
    """قراءة أعداد المهام النشطة والمتبقية من ctx.queue_manager.snapshot()"""
    active = 0
    remaining = 0
    terminal_states = {'completed', 'done', 'failed', 'cancelled', 'canceled', 'error', 'finished'}
    active_states = {'active', 'running', 'downloading', 'uploading', 'processing', 'in_progress'}

    if isinstance(snap, dict):
        if 'active' in snap and 'remaining' in snap and isinstance(snap['active'], int):
            return snap['active'], snap['remaining']

        items_list = None
        for k in ('tasks', 'items', 'jobs', 'queue', 'downloads'):
            if k in snap and isinstance(snap[k], (list, tuple, set)):
                items_list = snap[k]
                break

        if items_list is not None:
            snap = items_list
        else:
            for k, v in snap.items():
                state_name = str(k).split('.')[-1].lower()
                count = len(v) if isinstance(v, (list, tuple, set, dict)) else (v if isinstance(v, int) else 0)
                if state_name in active_states:
                    active += count
                elif state_name not in terminal_states:
                    remaining += count
            return active, remaining

    if not isinstance(snap, (list, tuple, set, dict)):
        for attr in ('tasks', 'items', 'jobs', 'queue'):
            if hasattr(snap, attr):
                val = getattr(snap, attr)
                if isinstance(val, (list, tuple, set, dict)):
                    return extract_queue_counts(val)
        if hasattr(snap, 'active') and hasattr(snap, 'remaining'):
            return int(getattr(snap, 'active')), int(getattr(snap, 'remaining'))

    if isinstance(snap, (list, tuple, set)):
        for item in snap:
            state = item.get('status') or item.get('state') if isinstance(item, dict) else getattr(item, 'status', getattr(item, 'state', None))
            state_name = getattr(state, 'name', str(state)).split('.')[-1].lower()
            if state_name in active_states:
                active += 1
            elif state_name not in terminal_states:
                remaining += 1

    return active, remaining

def extract_universal_counts(ctx):
    """Count non-terminal tasks managed separately by UniversalDownloadManager."""
    active = 0
    remaining = 0
    terminal_states = {'completed', 'done', 'failed', 'cancelled', 'canceled', 'error', 'finished'}
    active_states = {'active', 'running', 'downloading', 'uploading', 'processing', 'in_progress'}

    try:
        from teledrive.universal_downloader import get_universal_downloader
        tasks = get_universal_downloader(ctx).list_tasks()
    except Exception:
        return 0, 0

    for task in tasks:
        if not isinstance(task, dict):
            continue
        state_name = str(task.get('status') or task.get('state') or '').split('.')[-1].lower()
        if state_name in active_states:
            active += 1
        elif state_name not in terminal_states:
            remaining += 1
    return active, remaining

def build_status_card(active_count, remaining_count, updated_at, finished=False):
    status_icon = "✅" if finished else "🟢"
    title_text = "TeleDrive — اكتملت التنزيلات" if finished else "TeleDrive — المراقبة تعمل"
    state_text = "اكتملت جميع المهام" if finished else "تعمل (الموقع يحمّل الآن)"

    return f"""
    <div dir="rtl" style="font-family: system-ui, -apple-system, sans-serif; max-width: 320px; padding: 18px; border-radius: 16px; border: 1px solid #e0e0e0; background: #ffffff; color: #1f1f1f; box-shadow: 0 2px 6px rgba(0,0,0,0.04); line-height: 1.8;">
            <div style="font-size: 18px; font-weight: 700; margin-bottom: 10px; display: flex; align-items: center; justify-content: flex-start; gap: 8px;">
                <span>{status_icon}</span> <span>{title_text}</span>
            </div>
            <div style="font-size: 14px; color: #333; margin-bottom: 10px; text-align: right;">
                • <b>حالة المراقبة:</b> {state_text}<br>
                • <b>المهام النشطة (Telegram + الشامل):</b> <span style="font-weight: 700; color: #0b57d0;">{active_count}</span><br>
                • <b>المهام المتبقية (Telegram + الشامل):</b> <span style="font-weight: 700; color: #b06000;">{remaining_count}</span><br>
                • <b>تحديث تلقائي:</b> كل 30 ثانية
            </div>
            <div style="font-size: 12px; color: #777; border-top: 1px solid #f0f0f0; padding-top: 8px; text-align: right;">
                آخر تحديث: {updated_at}
            </div>
    </div>
    <script>
    (async () => {{
        try {{
            if ('wakeLock' in navigator && !window._tdWakeLock) {{
                window._tdWakeLock = await navigator.wakeLock.request('screen');
            }}
        }} catch (e) {{}}
    }})();
    </script>
    """

# حفظ إعدادات التسجيل والمجاري الأصلية لاستعادتها عند الانتهاء
_orig_disable_level = logging.root.manager.disable
_target_streams = {sys.stdout, sys.stderr, sys.__stdout__, sys.__stderr__}
for _h in logging.root.handlers:
    if hasattr(_h, 'stream') and _h.stream is not None:
        _target_streams.add(_h.stream)

for _lg in list(logging.Logger.manager.loggerDict.values()):
    if isinstance(_lg, logging.Logger):
        for _h in _lg.handlers:
            if hasattr(_h, 'stream') and _h.stream is not None:
                _target_streams.add(_h.stream)

_saved_methods = {}
for _s in _target_streams:
    if _s is not None and hasattr(_s, 'write'):
        _saved_methods[_s] = (
            getattr(_s, 'write', None),
            getattr(_s, 'writelines', None),
            getattr(_s, 'flush', None)
        )

def _silent_write(text, *args, **kwargs):
    return len(text) if isinstance(text, (str, bytes)) else 0

try:
    clear_output(wait=False)

    # كتم رسائل WARNING و INFO مؤقتاً أثناء عمل البطاقة مع الإبقاء على CRITICAL
    logging.disable(logging.ERROR)
    for _s in _saved_methods:
        try:
            _s.write = _silent_write
        except Exception:
            pass

    card_handle = display(HTML(build_status_card("...", "...", "جاري الفحص...")), display_id=True)
    has_started_tasks = False
    idle_checks = 0

    while True:
        if 'ctx' in globals() and hasattr(ctx, 'queue_manager'):
            snap = ctx.queue_manager.snapshot()
            active_tasks, remaining_tasks = extract_queue_counts(snap)
            universal_active, universal_remaining = extract_universal_counts(ctx)
            active_tasks += universal_active
            remaining_tasks += universal_remaining
            now_str = datetime.now().strftime("%H:%M:%S")

            if (active_tasks + remaining_tasks) > 0:
                has_started_tasks = True
                idle_checks = 0
                card_handle.update(HTML(build_status_card(active_tasks, remaining_tasks, now_str, finished=False)))
            else:
                if has_started_tasks:
                    idle_checks += 1
                    if idle_checks >= 2:
                        card_handle.update(HTML(build_status_card(0, 0, now_str, finished=True)))
                        break
                card_handle.update(HTML(build_status_card(0, 0, now_str, finished=False)))

        time.sleep(30)

except KeyboardInterrupt:
    pass
finally:
    # استعادة إعدادات التسجيل وجميع دوال المخرجات لحالتها الطبيعية فور توقف الخلية
    logging.disable(_orig_disable_level)
    for _s, (_orig_w, _orig_wl, _orig_fl) in _saved_methods.items():
        for _method_name, _original in (("write", _orig_w), ("writelines", _orig_wl), ("flush", _orig_fl)):
            try:
                if _original is not None:
                    setattr(_s, _method_name, _original)
            except Exception:
                pass'''

# Friendly, non-technical titles shown in Colab's collapsed form view.
# These are what non-coders see; the original `teledrive_title` stays in
# metadata for tracing and never changes logic.
FRIENDLY_TITLES: tuple[str, ...] = (
    "📦 الخطوة 1 — تثبيت وتحديث الحزمة | Install & Update Package",
    "⚙️ الخطوة 2 — تجهيز النظام وقاعدة البيانات | Bootstrap System",
    "🔐 الخطوة 3 — ربط Google Drive و Telegram | Connect Accounts",
    "🚀 الخطوة 4 — تشغيل واجهة TeleDrive | Launch App",
    "⚡ خطوة الربط التلقائي — فتح لوحة Vercel | One-click handoff",
    "📋 الخطوة 6 — تقرير الجلسة (اختياري) | Session Report (optional)",
    "✅ الخطوة 7 — فحص النظام (اختياري) | Health Check (optional)",
    "🧹 الخطوة 8 — تنظيف وإغلاق | Cleanup & Shutdown",
    "📡 خلية اختيارية 9 — إبقاء Colab نشطًا | Start Keep-Alive",
    "⏹️ خلية اختيارية 10 — إيقاف إبقاء Colab نشطًا | Stop Keep-Alive",
    "🟢 مراقبة TeleDrive — تعمل تلقائياً طوال فترة التحميل",
)

def _title_line(friendly_title: str) -> str:
    # Colab form title: shown as a card header when `cellView: form`.
    # The `{ display-mode: "form" }` suffix is optional but makes the intent
    # explicit for Colab's parser and is harmless elsewhere.
    return f'#@title {friendly_title} {{ display-mode: "form" }}\n'


def _wrap_with_friendly_title(code: str, friendly_title: str) -> str:
    # Prepend the form title comment without touching any logic.
    # The title line is a Python comment, so execution is identical.
    if code.startswith("#@title"):
        return code
    return _title_line(friendly_title) + code


CELLS: tuple[dict[str, str], ...] = (
    {"title": "Verify/update the package, restore and install pinned dependencies", "code": CELL_1},
    {"title": "Bootstrap directories, logging, SQLite migrations and WAL", "code": CELL_2},
    {"title": "Telegram credentials (Colab Secrets or hidden) and native Drive auth", "code": CELL_3},
    {"title": "Inject into the one context and launch the UI (share=False)", "code": CELL_4},
    {"title": "Optional Vercel one-click handoff tunnel (experimental)", "code": CELL_4B_VERCEL_HANDOFF},
    {"title": "Redacted handoff snapshot", "code": CELL_5},
    {"title": "Run the packaged test suite", "code": CELL_6},
    {"title": "Safe maintenance and clean shutdown", "code": CELL_7},
    {"title": "Optional start of best-effort Colab keep-alive", "code": CELL_8_KEEPALIVE_START},
    {"title": "Optional stop of Colab keep-alive", "code": CELL_9_KEEPALIVE_STOP},
    {"title": "Automatic TeleDrive download monitor", "code": CELL_10_MONITOR},
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
OPTIONAL_CELL_COUNT = 4
TOTAL_CELL_COUNT = REQUIRED_CELL_COUNT + OPTIONAL_CELL_COUNT


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
    for idx, cell in enumerate(CELLS):
        friendly = FRIENDLY_TITLES[idx] if idx < len(FRIENDLY_TITLES) else cell["title"]
        wrapped_code = _wrap_with_friendly_title(cell["code"], friendly)
        cells.append(
            {
                "cell_type": "code",
                "execution_count": None,
                # Persistent friendly UX for non-coders:
                # - `cellView: form`  -> Colab shows the `#@title` card with code hidden.
                # - `jupyter.source_hidden` + `collapsed` -> JupyterLab/VS Code respect it.
                # - `tags: hide-input` -> JupyterBook/nbconvert compatibility.
                # The code itself never changes; output stays visible.
                "metadata": {
                    "teledrive_title": cell["title"],
                    "cellView": "form",
                    "collapsed": True,
                    "jupyter": {"source_hidden": True},
                    "tags": ["hide-input"],
                },
                "outputs": [],
                "source": _source_lines(wrapped_code),
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
