import os
from teledrive.config import redact


def test_redaction():
    os.environ["TELEGRAM_API_HASH"] = "supersecret"
    txt = "hash=supersecret in log"
    assert "supersecret" not in redact(txt)
    del os.environ["TELEGRAM_API_HASH"]


def test_default_root_falls_back_when_content_is_not_writable(monkeypatch, tmp_path):
    """CI runners have no writable /content; the default must degrade, not crash."""
    import importlib

    from teledrive import config

    monkeypatch.delenv("TELEDRIVE_ROOT", raising=False)
    monkeypatch.setattr(config.os.path, "isdir", lambda p: False, raising=False)
    monkeypatch.setattr(config.Path, "is_dir", lambda self: False)
    monkeypatch.setattr(config.tempfile, "gettempdir", lambda: str(tmp_path))

    root = config._default_root()
    assert root == tmp_path / "teledrive_runtime"
    assert not str(root).startswith("/content")
    importlib.reload(config)


def test_explicit_teledrive_root_always_wins(monkeypatch, tmp_path):
    from teledrive import config

    monkeypatch.setenv("TELEDRIVE_ROOT", str(tmp_path / "explicit"))
    assert config._default_root() == tmp_path / "explicit"
