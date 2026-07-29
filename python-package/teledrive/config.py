"""Configuration and paths. No secrets ever live here."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(os.environ.get("TELEDRIVE_ROOT", "/content/teledrive_runtime")).resolve()

DATA_DIR = ROOT / "data"
LOGS_DIR = ROOT / "logs"
TEMP_DIR = ROOT / "temp"
CHECKPOINTS_DIR = ROOT / "checkpoints"
SESSION_DIR = ROOT / "session"

DB_PATH = DATA_DIR / "teledrive.db"
LOG_PATH = LOGS_DIR / "teledrive.log"
TELEGRAM_SESSION = SESSION_DIR / "telegram.session"
# No Drive token file: Colab-native auth only (Constitution Section 6).

DRIVE_APPDATA_FOLDER = "TeleDrive_AppData"

CONCURRENCY_LEVELS = {"safe": 1, "balanced": 2, "fast": 3}
HARD_CONCURRENCY_CAP = 4

RETRY_MAX_ATTEMPTS = 5
RETRY_BASE_SECONDS = 2.0
RETRY_MULTIPLIER = 2.0
RETRY_CAP_SECONDS = 60.0

DOWNLOAD_CHUNK = 1024 * 1024
UPLOAD_CHUNK = 8 * 1024 * 1024  # 8 MiB — Drive requires multiple of 256 KiB

DRIVE_QUOTA_WARN_RATIO = 0.90

SUPPORTED_LANGUAGES = ("ar", "en")
DEFAULT_LANGUAGE = os.environ.get("TELEDRIVE_LANG", "ar")

SECRET_KEYS = (
    "TELEGRAM_API_ID",
    "TELEGRAM_API_HASH",
    "api_id",
    "api_hash",
    "token",
    "refresh_token",
    "client_secret",
    "phone",
    "code",
    "password",
)


@dataclass
class RuntimeConfig:
    language: str = DEFAULT_LANGUAGE
    concurrency: str = os.environ.get("TELEDRIVE_CONCURRENCY", "balanced")
    debug: bool = os.environ.get("TELEDRIVE_DEBUG", "").lower() in ("1", "true", "yes")
    share_public: bool = False
    manual_concurrency: int | None = None
    drive_folder_id: str | None = None
    version: str = "3.1.0"
    spec_version: str = "3.1.0"
    extra: dict = field(default_factory=dict)

    def concurrency_value(self) -> int:
        if self.manual_concurrency is not None:
            return max(1, min(self.manual_concurrency, HARD_CONCURRENCY_CAP))
        return CONCURRENCY_LEVELS.get(self.concurrency, 2)


CONFIG = RuntimeConfig()


def all_dirs() -> list[Path]:
    return [DATA_DIR, LOGS_DIR, TEMP_DIR, CHECKPOINTS_DIR, SESSION_DIR]


def redact(text: str) -> str:
    """Replace any known secret token or env value with <redacted>."""
    if not text:
        return text
    out = text
    for key in SECRET_KEYS:
        val = os.environ.get(key.upper()) or os.environ.get(key)
        if val and val in out:
            out = out.replace(val, "<redacted>")
    return out
