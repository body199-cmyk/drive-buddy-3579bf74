import os
from teledrive.config import redact


def test_redaction():
    os.environ["TELEGRAM_API_HASH"] = "supersecret"
    txt = "hash=supersecret in log"
    assert "supersecret" not in redact(txt)
    del os.environ["TELEGRAM_API_HASH"]


# --- Phase 1: runtime root resolution and mounted-Drive guard -----------------

import pytest

from teledrive import config


def test_default_root_falls_back_when_content_is_not_writable(monkeypatch, tmp_path):
    """CI runners have no writable /content; the default must degrade, not crash."""
    monkeypatch.setattr(config.Path, "is_dir", lambda self: False)
    monkeypatch.setattr(config.tempfile, "gettempdir", lambda: str(tmp_path))

    root = config._default_root(env={})
    assert root == tmp_path / "teledrive_runtime"
    assert not str(root).startswith("/content")


def test_content_is_used_only_when_present_and_writable(monkeypatch, tmp_path):
    monkeypatch.setattr(config.Path, "is_dir", lambda self: True)
    monkeypatch.setattr(config.os, "access", lambda p, mode: True)
    assert config._default_root(env={}) == config.Path("/content/teledrive_runtime")

    monkeypatch.setattr(config.os, "access", lambda p, mode: False)
    monkeypatch.setattr(config.tempfile, "gettempdir", lambda: str(tmp_path))
    assert config._default_root(env={}) == tmp_path / "teledrive_runtime"


def test_explicit_teledrive_root_always_wins(tmp_path):
    explicit = tmp_path / "explicit"
    assert config._default_root(env={"TELEDRIVE_ROOT": str(explicit)}) == explicit


def test_mounted_drive_root_is_rejected():
    for bad in ("/content/drive/MyDrive/td", "/gdrive/td", "/content/gdrive/x"):
        with pytest.raises(config.MountedRootError):
            config._default_root(env={"TELEDRIVE_ROOT": bad})


def test_mounted_drive_is_never_selected_automatically(monkeypatch, tmp_path):
    monkeypatch.setattr(config.Path, "is_dir", lambda self: False)
    monkeypatch.setattr(config.tempfile, "gettempdir", lambda: str(tmp_path))
    assert not config.is_mounted_drive(config._default_root(env={}))


def test_sqlite_under_mounted_drive_is_refused():
    with pytest.raises(config.MountedRootError):
        config.assert_local_path("/content/drive/MyDrive/teledrive.db", what="SQLite database")
    # the real database path must already be local
    assert not config.is_mounted_drive(config.DB_PATH)


def test_quarantine_directory_is_part_of_bootstrap():
    dirs = config.all_dirs()
    assert config.QUARANTINE_DIR in dirs
    assert config.QUARANTINE_DIR == config.TEMP_DIR / "_quarantine"


def test_bootstrap_creates_every_runtime_dir_including_quarantine(tmp_path, monkeypatch):
    created = [tmp_path / d.name for d in config.all_dirs()]
    for d in created:
        d.mkdir(parents=True, exist_ok=True)
    assert all(d.is_dir() for d in created)
    assert (tmp_path / "_quarantine").is_dir()
