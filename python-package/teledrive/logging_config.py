"""Logging configuration with redaction and file-only application diagnostics."""
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from .config import LOG_PATH, LOGS_DIR, redact


class RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.msg = redact(str(record.msg))
            if record.args:
                record.args = tuple(
                    redact(str(a)) if isinstance(a, str) else a
                    for a in record.args
                )
        except Exception:
            pass
        return True


_configured = False


def setup(level: int = logging.INFO) -> logging.Logger:
    """Write redacted TeleDrive/Telethon diagnostics to a rotating file.

    Avoid propagating application logs to the root logger, which commonly
    has a notebook stream handler in Colab. WARNING/ERROR records remain in
    the rotating log for troubleshooting.
    """
    global _configured
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("teledrive")
    if _configured:
        return logger

    logger.setLevel(level)
    logger.handlers.clear()
    logger.propagate = False

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_PATH, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    file_handler.addFilter(RedactionFilter())
    logger.addHandler(file_handler)

    # Telethon has its own logger namespace; route WARNING+ to the same file.
    telethon_logger = logging.getLogger("telethon")
    telethon_logger.setLevel(logging.WARNING)
    telethon_logger.handlers.clear()
    telethon_logger.propagate = False
    telethon_logger.addHandler(file_handler)

    _configured = True
    return logger


def get_logger(name: str = "teledrive") -> logging.Logger:
    return logging.getLogger(name)


def tail(path: Path = LOG_PATH, lines: int = 200) -> str:
    """Return the last lines from the log without loading the whole file."""
    if lines <= 0 or not path.exists():
        return ""
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            block = 8192
            data = b""
            while size > 0 and data.count(b"\n") <= lines:
                read = min(block, size)
                size -= read
                f.seek(size)
                data = f.read(read) + data
            return "\n".join(
                data.decode("utf-8", errors="replace").splitlines()[-lines:]
            )
    except Exception:
        return ""
