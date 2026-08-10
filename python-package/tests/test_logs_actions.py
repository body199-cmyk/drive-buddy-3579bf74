"""M17-T03: logs.* actions tail/filter/export redacted logs, no secrets leak."""
from __future__ import annotations

from pathlib import Path

import teledrive.services as services
from teledrive import action_registry
from teledrive.config import LOG_PATH
from teledrive.redaction import redact

PROVES = ("logs.refresh", "logs.search", "logs.download")

SECRET_LINES = [
    "api_hash=abc123SECRETVAL rest",
    "phone=+971500000000 connected",
    "token=ya29.abcdef0123456789secretXYZ1234 downloaded",
    "email=user@secret.example.com sent",
    "path=/home/user/.telegram/session.session opened",
]
SAFE_LINE = "queue enqueued id=42"


def _seed(tmp_path: Path) -> Path:
    log_file = tmp_path / "teledrive.log"
    log_file.write_text("\n".join(SECRET_LINES + [SAFE_LINE]), encoding="utf-8")
    return log_file


def test_refresh_returns_redacted_text_and_status(monkeypatch, ctx, tmp_path):
    log_file = _seed(tmp_path)
    monkeypatch.setattr(services, "tail_log", lambda lines: log_file.read_text("utf-8"))
    text_update, status = ctx.handlers.h_logs_refresh("ALL")
    text = text_update["value"]
    assert SAFE_LINE in text
    # Secrets must be redacted
    assert "abc123SECRETVAL" not in text
    assert "+971500000000" not in text
    assert "secretXYZ" not in text
    assert "user@secret.example.com" not in text
    assert "✅" in status


def test_search_filters_by_needle_and_redacts(monkeypatch, ctx, tmp_path):
    log_file = _seed(tmp_path)
    monkeypatch.setattr(services, "tail_log", lambda lines: log_file.read_text("utf-8"))
    # searching for "queue" returns only the safe line — secrets never appear
    text_update, _ = ctx.handlers.h_logs_search("queue", "ALL")
    text = text_update["value"]
    assert "queue enqueued" in text
    assert "SECRETVAL" not in text
    assert "+9715" not in text
    assert "secret.example" not in text


def test_download_writes_redacted_file(monkeypatch, ctx, tmp_path, monkeypatch_class=None):
    # Override LOGS_DIR to a temp path
    import teledrive.config as cfg
    monkeypatch.setattr(cfg, "LOGS_DIR", tmp_path)
    log_file = _seed(tmp_path)
    monkeypatch.setattr(services, "tail_log", lambda lines: log_file.read_text("utf-8"))
    file_update, _status = ctx.handlers.h_logs_download("ALL")
    out_path = Path(file_update["value"])
    assert out_path.exists()
    body = out_path.read_text("utf-8")
    assert "SECRETVAL" not in body
    assert "abc123SECRETVAL" not in body
    assert "+971500000000" not in body
    assert "secretXYZ" not in body
    assert SAFE_LINE in body


def test_level_filter_includes_level_only(monkeypatch, ctx, tmp_path):
    log_file = tmp_path / "teledrive.log"
    log_file.write_text(
        "2026-08-10 [INFO] engine start\n"
        "2026-08-10 [WARNING] slow transfer\n"
        "2026-08-10 [ERROR] transfer failed\n"
        "2026-08-10 [INFO] done\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(services, "tail_log", lambda lines: log_file.read_text("utf-8"))
    text_update, _ = ctx.handlers.h_logs_refresh("ERROR")
    text = text_update["value"]
    assert "[ERROR]" in text
    assert "[WARNING]" not in text
