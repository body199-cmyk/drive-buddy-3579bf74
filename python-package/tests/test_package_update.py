"""M15-T07 — Cell 1 pre-bootstrap package update gate contract.

The code under test is lifted VERBATIM from the single notebook generator
(``teledrive.notebook_cells.CELL_1_PACKAGE_UPDATER``) — the same bytes shipped
in both notebook copies and in ``colab_cells.json`` — executed with a fake
transport against a tmp ``/content``. No network, no Colab, no real runtime.

Proven here:
  * verified success: .part-only download, digest+size verified, atomic swap
    of archive AND package directory, state record written, ONE SUCCESS line;
  * already-current: manifest checked, archive endpoint never called;
  * digest mismatch / truncated download / unavailable endpoint: REFUSED, the
    old package stays byte-identical, updater-owned .part files are removed;
  * untrusted or incomplete manifest: REFUSED before any archive fetch;
  * any teledrive module already imported (live runtime): REFUSED before any
    network call — a running ApplicationContext/UI is never hot-swapped;
  * the swap preserves /content/teledrive_runtime (SQLite, checkpoints, logs,
    quarantine) and clears updater-owned leftovers;
  * secret-looking manifest junk never reaches the output line or the state;
  * the updater block is lift-safe for the AST harness (no module-level calls).
"""
from __future__ import annotations

import ast
import hashlib
import io
import json
import sys
import types
import urllib.error
import zipfile

import pytest

from teledrive import notebook_cells

SOURCE = notebook_cells.CELL_1_PACKAGE_UPDATER


def _namespace() -> dict:
    namespace: dict = {"__name__": "cell1_updater"}
    exec(compile(SOURCE, "<cell1-updater>", "exec"), namespace)  # noqa: S102 — repo source
    return namespace


NS = _namespace()

RELEASE = NS["PKG_RELEASE_TAG"]
ARCHIVE_URL = NS["PKG_RELEASE_BASE"] + "teledrive_v4.5.zip"
MANIFEST_URL = NS["PKG_MANIFEST_URL"]
COMMIT = "0123456789abcdef0123456789abcdef01234567"
PKG_DIGEST = hashlib.sha256(b"").hexdigest()  # replaced below, keeps linters calm


def _tested_zip_bytes(marker: bytes = b"lock-v1\n") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("teledrive-v4.5/requirements.lock", marker)
        archive.writestr("teledrive-v4.5/teledrive/__init__.py", b"# pkg\n")
        archive.writestr("teledrive-v4.5/teledrive/config.py", b"VERSION='4.5.0'\n")
    return buffer.getvalue()


PKG_BYTES = _tested_zip_bytes()
OTHER_BYTES = _tested_zip_bytes(b"lock-v2\n")
PKG_DIGEST = hashlib.sha256(PKG_BYTES).hexdigest()


def _manifest(payload: bytes = PKG_BYTES, **overrides) -> dict:
    manifest = {
        "schema": 1,
        "package": "teledrive",
        "product_version": "4.5.0",
        "release": RELEASE,
        "commit": COMMIT,
        "archive_url": ARCHIVE_URL,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
        "published_at_utc": "2026-08-09T18:00:00Z",
    }
    manifest.update(overrides)
    return manifest


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def _make_fetch(routes: dict, calls: list):
    def fetch(url, timeout=30):
        calls.append(url)
        outcome = routes[url]
        if isinstance(outcome, Exception):
            raise outcome
        return _FakeResponse(outcome)

    return fetch


@pytest.fixture()
def clean_modules(monkeypatch):
    """Scrub teledrive imports so the gate sees a fresh, unloaded runtime."""
    scrubbed = {
        name: module
        for name, module in sys.modules.items()
        if name != "teledrive" and not name.startswith("teledrive.")
    }
    monkeypatch.setattr(sys, "modules", scrubbed)
    return scrubbed


def _try(content, **kwargs):
    lines: list[str] = []
    result = NS["pkg_try_update"](content, emit=lines.append, **kwargs)
    return result, lines


def _install_current(content):
    (content / "teledrive_v4.5.zip").write_bytes(PKG_BYTES)
    package_dir = content / "teledrive-v4.5"
    package_dir.mkdir()
    (package_dir / "requirements.lock").write_bytes(b"lock-v1\n")
    NS["_pkg_state_write"](content, _manifest())


# ---- the shipped code shape -------------------------------------------------


def test_updater_block_is_lift_safe():
    """No module-level call: the AST harness (test_restore_package) lifts this
    layer and must never execute the gate itself."""
    tree = ast.parse(SOURCE)
    assert tree.body, "updater block must exist"
    allowed = (ast.Import, ast.Assign, ast.FunctionDef)
    for node in tree.body:
        assert isinstance(node, allowed), f"unexpected module-level {type(node).__name__}"
        if isinstance(node, ast.Assign):
            assert not any(isinstance(child, ast.Call) for child in ast.walk(node.value)), (
                "module-level calls would run inside the lifted test namespace"
            )


def test_shipped_cell1_calls_gate_after_mount_and_before_restore():
    cell = notebook_cells.CELLS[0]["code"]
    mount = cell.index("colab_drive.mount(")
    gate = cell.index("pkg_try_update(LOCAL_ROOT)")
    resolve = cell.index("PACKAGE_ZIP = resolve_package_zip(LOCAL_ROOT)")
    assert mount < gate < resolve
    assert cell.count("pkg_try_update(LOCAL_ROOT)") == 1
    assert NS["PKG_RELEASE_TAG"] in cell
    assert "package reference:" in cell


# ---- verified success --------------------------------------------------------


def test_successful_verified_update(tmp_path, clean_modules):
    calls: list[str] = []
    fetch = _make_fetch(
        {MANIFEST_URL: json.dumps(_manifest()).encode(), ARCHIVE_URL: PKG_BYTES},
        calls,
    )
    result, lines = _try(tmp_path, fetch=fetch, manifest_url=MANIFEST_URL)
    assert result["outcome"] == "success"
    expected = "Package update: SUCCESS %s commit=%s sha256=%s" % (
        RELEASE, COMMIT[:12], PKG_DIGEST[:12])
    assert lines == [expected]
    assert (tmp_path / "teledrive_v4.5.zip").read_bytes() == PKG_BYTES
    package_dir = tmp_path / "teledrive-v4.5"
    assert (package_dir / "requirements.lock").read_bytes() == b"lock-v1\n"
    state = json.loads((tmp_path / "teledrive_package_state.json").read_text(encoding="utf-8"))
    assert state["release"] == RELEASE
    assert state["commit"] == COMMIT
    assert state["sha256"] == PKG_DIGEST
    assert state["archive_url"] == ARCHIVE_URL
    assert calls == [MANIFEST_URL, ARCHIVE_URL]
    assert list(tmp_path.glob("*.part")) == []
    assert not list(tmp_path.glob(".teledrive_*"))


def test_already_current_never_downloads_the_archive(tmp_path, clean_modules):
    _install_current(tmp_path)
    calls: list[str] = []
    fetch = _make_fetch({MANIFEST_URL: json.dumps(_manifest()).encode()}, calls)
    result, lines = _try(tmp_path, fetch=fetch, manifest_url=MANIFEST_URL)
    assert result["outcome"] == "already-current"
    assert len(lines) == 1
    assert lines[0].startswith("Package update: ALREADY CURRENT " + RELEASE)
    assert calls == [MANIFEST_URL]  # only the manifest was fetched


def test_verified_local_zip_converges_without_redownload(tmp_path, clean_modules):
    """Crash-recovery: zip already verified, state/dir missing -> no download,
    the verified local bytes are staged, swapped and recorded."""
    (tmp_path / "teledrive_v4.5.zip").write_bytes(PKG_BYTES)
    calls: list[str] = []
    fetch = _make_fetch(
        {MANIFEST_URL: json.dumps(_manifest()).encode(), ARCHIVE_URL: OTHER_BYTES},
        calls,
    )
    result, _ = _try(tmp_path, fetch=fetch, manifest_url=MANIFEST_URL)
    assert result["outcome"] == "success"
    assert calls == [MANIFEST_URL]  # archive endpoint NOT called
    assert (tmp_path / "teledrive-v4.5" / "requirements.lock").read_bytes() == b"lock-v1\n"
    state = json.loads((tmp_path / "teledrive_package_state.json").read_text(encoding="utf-8"))
    assert state["sha256"] == PKG_DIGEST


def test_swap_preserves_runtime_data_and_cleans_updater_owned_files(tmp_path, clean_modules):
    runtime = tmp_path / "teledrive_runtime"
    for sub in ("data", "checkpoints", "logs", "temp/_quarantine"):
        (runtime / sub).mkdir(parents=True, exist_ok=True)
    (runtime / "data" / "teledrive.db").write_bytes(b"sqlite-bytes")
    (runtime / "temp" / "_quarantine" / "mystery.bin").write_bytes(b"q")
    old_dir = tmp_path / "teledrive-v4.5"
    old_dir.mkdir()
    (old_dir / "STALE.txt").write_text("from an older package")
    leftover = tmp_path / ".teledrive_v4.5.zip.deadbeef.part"
    leftover.write_bytes(b"interrupted-download")
    stale_staging = tmp_path / ".teledrive_pkg_staging_xyz"
    stale_staging.mkdir()
    (stale_staging / "junk").write_text("junk")

    calls: list[str] = []
    fetch = _make_fetch(
        {MANIFEST_URL: json.dumps(_manifest()).encode(), ARCHIVE_URL: PKG_BYTES},
        calls,
    )
    result, _ = _try(tmp_path, fetch=fetch, manifest_url=MANIFEST_URL)
    assert result["outcome"] == "success"
    assert not (old_dir / "STALE.txt").exists()
    assert (old_dir / "requirements.lock").read_bytes() == b"lock-v1\n"
    assert (runtime / "data" / "teledrive.db").read_bytes() == b"sqlite-bytes"
    assert (runtime / "temp" / "_quarantine" / "mystery.bin").read_bytes() == b"q"
    assert not leftover.exists()
    assert not stale_staging.exists()
    assert list(tmp_path.glob("*.part")) == []
    assert not list(tmp_path.glob(".teledrive_*"))


# ---- refusals keep the old package untouched ---------------------------------


def test_digest_mismatch_refuses_and_keeps_old_package(tmp_path, clean_modules):
    old_zip = tmp_path / "teledrive_v4.5.zip"
    old_zip.write_bytes(OTHER_BYTES)
    old_dir = tmp_path / "teledrive-v4.5"
    old_dir.mkdir()
    (old_dir / "OLD.txt").write_text("keep me")
    calls: list[str] = []
    fetch = _make_fetch(
        {
            MANIFEST_URL: json.dumps(_manifest()).encode(),  # digest pinned to PKG_BYTES
            ARCHIVE_URL: OTHER_BYTES,  # ...but different bytes arrive
        },
        calls,
    )
    result, lines = _try(tmp_path, fetch=fetch, manifest_url=MANIFEST_URL)
    assert result["outcome"] == "refused"
    assert lines == [
        "Package update: REFUSED downloaded bytes failed digest/size verification; "
        "current package unchanged"
    ]
    assert old_zip.read_bytes() == OTHER_BYTES
    assert (old_dir / "OLD.txt").read_text() == "keep me"
    assert not (tmp_path / "teledrive_package_state.json").exists()
    assert list(tmp_path.glob("*.part")) == []
    assert not list(tmp_path.glob(".teledrive_*"))


def test_truncated_download_is_a_size_mismatch(tmp_path, clean_modules):
    calls: list[str] = []
    fetch = _make_fetch(
        {
            MANIFEST_URL: json.dumps(_manifest()).encode(),
            ARCHIVE_URL: PKG_BYTES[: len(PKG_BYTES) // 2],
        },
        calls,
    )
    result, lines = _try(tmp_path, fetch=fetch, manifest_url=MANIFEST_URL)
    assert result["outcome"] == "refused"
    assert "digest/size verification" in lines[0]
    assert not (tmp_path / "teledrive_v4.5.zip").exists()
    assert list(tmp_path.glob("*.part")) == []


class _TruncatedResponse:
    def __init__(self, payload: bytes):
        self._payload = payload
        self._sent = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, n=-1):
        if self._sent:
            raise ConnectionResetError("connection dropped")
        self._sent = True
        return self._payload[:1024]


def test_interrupted_download_cleans_part_and_keeps_old_package(tmp_path, clean_modules):
    old_zip = tmp_path / "teledrive_v4.5.zip"
    old_zip.write_bytes(OTHER_BYTES)

    def fetch(url, timeout=30):
        if url == ARCHIVE_URL:
            return _TruncatedResponse(PKG_BYTES)
        return _FakeResponse(json.dumps(_manifest()).encode())

    result, lines = _try(tmp_path, fetch=fetch, manifest_url=MANIFEST_URL)
    assert result["outcome"] == "refused"
    assert lines == ["Package update: REFUSED archive download failed; current package unchanged"]
    assert old_zip.read_bytes() == OTHER_BYTES
    assert list(tmp_path.glob("*.part")) == []


def test_unavailable_endpoint_refuses_without_touching_anything(tmp_path, clean_modules):
    old_zip = tmp_path / "teledrive_v4.5.zip"
    old_zip.write_bytes(OTHER_BYTES)
    calls: list[str] = []
    fetch = _make_fetch({MANIFEST_URL: urllib.error.URLError("offline")}, calls)
    result, lines = _try(tmp_path, fetch=fetch, manifest_url=MANIFEST_URL)
    assert result["outcome"] == "refused"
    assert lines == ["Package update: REFUSED update endpoint unreachable; current package unchanged"]
    assert calls == [MANIFEST_URL]
    assert old_zip.read_bytes() == OTHER_BYTES


@pytest.mark.parametrize(
    "override",
    [
        {"sha256": "z" * 64},
        {"sha256": None},
        {"archive_url": "https://example.com/teledrive_v4.5.zip"},
        {"archive_url": None},
        {"size_bytes": 0},
        {"release": ""},
        {"schema": 2},
    ],
)
def test_untrusted_or_incomplete_manifest_refused_before_any_archive_fetch(
    tmp_path, clean_modules, override
):
    calls: list[str] = []
    fetch = _make_fetch(
        {MANIFEST_URL: json.dumps(_manifest(**override)).encode(), ARCHIVE_URL: PKG_BYTES},
        calls,
    )
    result, lines = _try(tmp_path, fetch=fetch, manifest_url=MANIFEST_URL)
    assert result["outcome"] == "refused"
    assert lines == [
        "Package update: REFUSED untrusted or incomplete manifest; current package unchanged"
    ]
    assert calls == [MANIFEST_URL]  # archive endpoint never called
    assert not (tmp_path / "teledrive_v4.5.zip").exists()


# ---- live runtime is never hot-swapped --------------------------------------


def test_loaded_runtime_refuses_before_any_fetch(tmp_path, monkeypatch):
    scrubbed = {
        name: module
        for name, module in sys.modules.items()
        if not (name == "teledrive" or name.startswith("teledrive."))
    }
    scrubbed["teledrive.app_context"] = types.ModuleType("teledrive.app_context")
    monkeypatch.setattr(sys, "modules", scrubbed)
    calls: list[str] = []
    fetch = _make_fetch(
        {MANIFEST_URL: json.dumps(_manifest()).encode(), ARCHIVE_URL: PKG_BYTES}, calls
    )
    result, lines = _try(tmp_path, fetch=fetch, manifest_url=MANIFEST_URL)
    assert result["outcome"] == "refused"
    assert lines[0].startswith(
        "Package update: REFUSED runtime already loaded (1 teledrive module(s) imported)"
    )
    assert "restart the runtime" in lines[0]
    assert calls == []  # refused BEFORE touching the network


# ---- no secrets in output or state -------------------------------------------


def test_secret_looking_manifest_fields_never_leak(tmp_path, clean_modules):
    booby = _manifest(
        maintainer_note="x-access-token: S3cr3tV4lu3",
        internal_url="https://user:hunter2@example.invalid/x",
    )
    calls: list[str] = []
    fetch = _make_fetch({MANIFEST_URL: json.dumps(booby).encode(), ARCHIVE_URL: PKG_BYTES}, calls)
    result, lines = _try(tmp_path, fetch=fetch, manifest_url=MANIFEST_URL)
    assert result["outcome"] == "success"
    assert len(lines) == 1
    line = lines[0]
    assert "S3cr3tV4lu3" not in line and "hunter2" not in line
    state_text = (tmp_path / "teledrive_package_state.json").read_text(encoding="utf-8")
    assert "S3cr3tV4lu3" not in state_text and "hunter2" not in state_text
