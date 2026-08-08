"""Configuration and paths. No secrets ever live here."""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


# Mounted Google Drive / FUSE roots. SQLite on a FUSE mount corrupts under WAL,
# so the runtime refuses to place a database (or its runtime root) inside one.
MOUNTED_PREFIXES = (
    "/content/drive",
    "/content/gdrive",
    "/gdrive",
    "/mnt/gdrive",
    "/mnt/google_drive",
)


class MountedRootError(RuntimeError):
    """Raised when a runtime path resolves inside a mounted Drive/FUSE tree."""


def is_mounted_drive(path: "str | Path") -> bool:
    p = str(Path(path)).rstrip("/")
    return any(p == pre or p.startswith(pre + "/") for pre in MOUNTED_PREFIXES)


def assert_local_path(path: "str | Path", *, what: str = "runtime path") -> Path:
    """Reject any path inside a mounted Drive/FUSE tree."""
    p = Path(path)
    if is_mounted_drive(p):
        raise MountedRootError(
            f"{what} must stay on local disk: {p} is inside a mounted Drive/FUSE tree "
            f"({', '.join(MOUNTED_PREFIXES)}). SQLite/WAL is unsafe there."
        )
    return p


def _fallback_root() -> Path:
    return Path(tempfile.gettempdir()) / "teledrive_runtime"


def _default_root(env: "dict[str, str] | None" = None) -> Path:
    """Resolve the runtime root without any import side effects.

    Order: explicit ``TELEDRIVE_ROOT`` -> writable ``/content`` (Colab) ->
    ``tempfile.gettempdir()/teledrive_runtime``. CI runners and desktops have no
    writable ``/content``, so the default degrades instead of raising. Mounted
    Drive is never selected automatically and is rejected when requested.
    """
    environ = os.environ if env is None else env
    explicit = environ.get("TELEDRIVE_ROOT")
    if explicit:
        return assert_local_path(explicit, what="TELEDRIVE_ROOT")
    content = Path("/content")
    if content.is_dir() and os.access(content, os.W_OK):
        return content / "teledrive_runtime"
    return _fallback_root()


ROOT = _default_root().resolve()


DATA_DIR = ROOT / "data"
LOGS_DIR = ROOT / "logs"
TEMP_DIR = ROOT / "temp"
CHECKPOINTS_DIR = ROOT / "checkpoints"
SESSION_DIR = ROOT / "session"
QUARANTINE_DIR = TEMP_DIR / "_quarantine"

RUNTIME_DIRS = (DATA_DIR, LOGS_DIR, TEMP_DIR, CHECKPOINTS_DIR, SESSION_DIR, QUARANTINE_DIR)

DB_PATH = assert_local_path(DATA_DIR / "teledrive.db", what="SQLite database")
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
    version: str = "4.5.0"
    spec_version: str = "4.5.0"
    extra: dict = field(default_factory=dict)

    def concurrency_value(self) -> int:
        if self.manual_concurrency is not None:
            return max(1, min(self.manual_concurrency, HARD_CONCURRENCY_CAP))
        return CONCURRENCY_LEVELS.get(self.concurrency, 2)


CONFIG = RuntimeConfig()


def all_dirs() -> list[Path]:
    """Every directory bootstrap creates, quarantine included."""
    return list(RUNTIME_DIRS)



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
