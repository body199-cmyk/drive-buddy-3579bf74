"""Cell 1 package-restore contract (M15-T02): direct archive, official wrapper, traps.

No Colab runtime and no /content are needed: the helper layer of Cell 1 is
lifted AST-exactly from the single generator source (teledrive.notebook_cells)
and executed in isolation, so the code under test is the code shipped in the
notebook itself.

What is proven here (mirrors the DOC scenarios):
  * a direct teledrive_v4.5.zip (real tested archive) is accepted untouched;
  * the official wrapper teledrive-package.zip is unwrapped via a DIFFERENT
    temp file (never read+write on the same file) and atomically moved into
    place;
  * a wrapper renamed to teledrive_v4.5.zip is detected by content — never
    treated as the real archive, never self-corrupted (no EOFError);
  * a missing archive keeps the existing clear assertion error;
  * unsafe member names (path traversal) and bad/corrupt payloads are rejected
    before anything is accepted;
  * Drive-side locations (real archive or wrapper) are honoured.
"""
from __future__ import annotations

import ast
import io
import pathlib
import zipfile

import pytest

from teledrive import notebook_cells

CELL_1 = notebook_cells.CELLS[0]["code"]
EXPECTED_ROOT = "teledrive-v4.5"
INNER_NAME = "teledrive_v4.5.zip"
WRAPPER_NAME = "teledrive-package.zip"


def _cell1_namespace() -> dict:
    """Exec ONLY the import/constant/function layer of Cell 1.

    The runtime flow (drive mount Try block, extraction, os.chdir, the !pip
    magic) is deliberately excluded so the helpers run anywhere, without
    Colab and without touching the real filesystem root.
    """
    source = "\n".join(
        line for line in CELL_1.splitlines() if not line.lstrip().startswith("!")
    )
    tree = ast.parse(source)
    cut = next(i for i, node in enumerate(tree.body) if isinstance(node, ast.Try))
    keep = [
        node
        for node in tree.body[:cut]
        if isinstance(node, (ast.Import, ast.Assign, ast.FunctionDef))
    ]
    module = ast.fix_missing_locations(ast.Module(body=keep, type_ignores=[]))
    namespace: dict = {}
    exec(compile(module, "<cell1>", "exec"), namespace)  # noqa: S102 — trusted repo source
    return namespace


NS = _cell1_namespace()


def _tested_zip_bytes() -> bytes:
    """Minimal valid 'tested archive': EXPECTED_ROOT/ tree with requirements.lock."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(f"{EXPECTED_ROOT}/requirements.lock", b"telethon==0.0\n")
        archive.writestr(f"{EXPECTED_ROOT}/teledrive/__init__.py", b"")
    return buffer.getvalue()


INNER_BYTES = _tested_zip_bytes()


def _write_tested_archive(path: pathlib.Path) -> pathlib.Path:
    path.write_bytes(INNER_BYTES)
    return path


def _write_wrapper(path: pathlib.Path, member: str = INNER_NAME,
                   payload: bytes = INNER_BYTES) -> pathlib.Path:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(member, payload)
    return path


@pytest.fixture()
def content(tmp_path: pathlib.Path) -> pathlib.Path:
    root = tmp_path / "content"
    root.mkdir()
    return root


def test_direct_archive_is_accepted_unchanged(content):
    target = _write_tested_archive(content / INNER_NAME)
    result = NS["resolve_package_zip"](content)
    assert result == target
    assert result.read_bytes() == INNER_BYTES  # untouched, no rewrite


def test_wrapper_is_unwrapped_via_temp_and_moved_atomically(content):
    wrapper = _write_wrapper(content / WRAPPER_NAME)
    wrapper_bytes = wrapper.read_bytes()
    result = NS["resolve_package_zip"](content)
    assert result == content / INNER_NAME
    assert result.read_bytes() == INNER_BYTES  # destination holds the INNER archive
    assert NS["_is_tested_archive"](result)
    assert wrapper.read_bytes() == wrapper_bytes  # wrapper itself never modified
    assert list(content.glob("*.part")) == []  # temp file moved away, nothing leaked


def test_renamed_wrapper_is_detected_not_treated_as_real(content):
    renamed = _write_wrapper(content / INNER_NAME)  # the M15-T01 trap
    assert not NS["_is_tested_archive"](renamed)  # content detection says: NOT the real archive
    result = NS["resolve_package_zip"](content)
    assert result == renamed  # same destination path...
    assert result.read_bytes() == INNER_BYTES  # ...but now holding the INNER bytes
    assert NS["_is_tested_archive"](result)  # no EOFError, no self-corruption
    assert list(content.glob("*.part")) == []


def test_missing_archive_keeps_the_clear_error(content):
    with pytest.raises(AssertionError, match="upload the tested archive"):
        NS["resolve_package_zip"](content)


def test_missing_archive_error_accepts_wrapper_hint(content):
    with pytest.raises(AssertionError, match="teledrive-package.zip"):
        NS["resolve_package_zip"](content)


@pytest.mark.parametrize("member", ["../teledrive_v4.5.zip",
                                    "../../x/teledrive_v4.5.zip",
                                    "/teledrive_v4.5.zip",
                                    "..\\teledrive_v4.5.zip"])
def test_unsafe_member_names_are_rejected(content, member):
    _write_wrapper(content / WRAPPER_NAME, member=member)
    with pytest.raises(RuntimeError, match="invalid package"):
        NS["resolve_package_zip"](content)
    assert not (content / INNER_NAME).exists()  # nothing accepted, nothing extracted


def test_wrapper_with_bad_inner_payload_is_rejected_before_accepting(content):
    _write_wrapper(content / WRAPPER_NAME, payload=b"garbage-not-a-zip")
    with pytest.raises(RuntimeError, match="invalid package"):
        NS["resolve_package_zip"](content)
    assert not (content / INNER_NAME).exists()
    assert list(content.glob("*.part")) == []  # temp cleaned on failure


def test_wrapper_without_inner_member_is_rejected(content):
    _write_wrapper(content / WRAPPER_NAME, member="README.txt", payload=b"hi")
    with pytest.raises(RuntimeError, match="invalid package"):
        NS["resolve_package_zip"](content)
    assert not (content / INNER_NAME).exists()


def test_safe_nested_member_path_is_accepted(content):
    _write_wrapper(content / WRAPPER_NAME, member="nested/dir/" + INNER_NAME)
    result = NS["resolve_package_zip"](content)
    assert NS["_is_tested_archive"](result)


def test_drive_side_real_archive_is_copied_into_place(content):
    drive_dir = content / "drive/MyDrive/TeleDrive"
    drive_dir.mkdir(parents=True)
    source = _write_tested_archive(drive_dir / INNER_NAME)
    result = NS["resolve_package_zip"](content)
    assert result == content / INNER_NAME
    assert NS["_is_tested_archive"](result)
    assert source.exists()  # original on Drive untouched


def test_drive_side_wrapper_is_supported(content):
    drive_dir = content / "drive/MyDrive/TeleDrive"
    drive_dir.mkdir(parents=True)
    _write_wrapper(drive_dir / WRAPPER_NAME)
    result = NS["resolve_package_zip"](content)
    assert result == content / INNER_NAME
    assert NS["_is_tested_archive"](result)


def test_corrupt_file_at_package_path_fails_clearly(content):
    (content / INNER_NAME).write_bytes(b"definitely not a zip archive")
    with pytest.raises(RuntimeError, match="invalid package"):
        NS["resolve_package_zip"](content)


def test_shipped_cell1_wires_the_resolver_and_keeps_the_contract():
    assert "resolve_package_zip(LOCAL_ROOT)" in CELL_1
    assert WRAPPER_NAME in CELL_1
    assert "tempfile" in CELL_1 and "os.replace" in CELL_1
    # product contract lines that must survive any Cell 1 edit:
    assert "drive mount skipped" in CELL_1
    assert 'glob("teledrive-v4.5*")' in CELL_1
    assert "requirements.lock" in CELL_1
