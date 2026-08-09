"""M15-T07 — the distributable archive is a reproducible release object.

The release manifest pins sha256, so CI must be able to prove that the
artifact it produced is the same object the update gate serves. That proof is
only possible if ``build_archive`` does not stamp volatile metadata (checkout
mtimes, filesystem iteration order) into the zip.
"""
from __future__ import annotations

import hashlib
import zipfile

from teledrive.package_service import PackageService


def _build(tmp_path, name):
    return PackageService().build_archive(tmp_path / name)


def test_same_tree_produces_byte_identical_archive(tmp_path):
    first = _build(tmp_path, "a.zip")
    second = _build(tmp_path, "b.zip")
    assert hashlib.sha256(first.read_bytes()).hexdigest() == hashlib.sha256(
        second.read_bytes()
    ).hexdigest()


def test_entries_are_sorted_with_fixed_metadata_and_root_prefix(tmp_path):
    first = _build(tmp_path, "c.zip")
    with zipfile.ZipFile(first) as archive:
        infos = archive.infolist()
    names = [info.filename for info in infos]
    assert names == sorted(names)
    assert all(info.date_time == (2020, 1, 1, 0, 0, 0) for info in infos)
    assert all(name.startswith("teledrive-v4.5/") for name in names)
    assert "teledrive-v4.5/requirements.lock" in names
