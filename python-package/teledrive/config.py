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
    # Use as_posix(): str(Path) backslash-normalizes on Windows, which would
    # defeat the mounted-Drive guard entirely outside POSIX systems.
    p = Path(path).as_posix().rstrip("/")
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
# Owner-authorized session resume (ADR-004): an obfuscated Telethon session
# blob may be stored under Drive AppData. Never a raw api_hash / phone / OTP.
SESSION_VAULT_NAME = "td_telegram.session.vault"
SESSION_VAULT_MAX_BYTES = 8 * 1024 * 1024

DRIVE_APPDATA_FOLDER = "TeleDrive_AppData"

# ---------------------------------------------------------------------------
# Concurrency (ADR-0001, owner override of the v4.5 cap of 4).
#
# The owner explicitly raised the hard cap to 100. This is a deliberate,
# recorded deviation from Constitution 12.8 and it is NOT a safety claim:
# Colab RAM, local disk and Telegram/Drive rate limits are the real ceiling.
# Anything above CONCURRENCY_WARN_ABOVE is surfaced to the user as a warning
# in the UI instead of being silently clamped.
# ---------------------------------------------------------------------------
CONCURRENCY_LEVELS = {"safe": 1, "balanced": 2, "fast": 3, "turbo": 16, "max": 100}
CONCURRENCY_MIN = 1
HARD_CONCURRENCY_CAP = 100
DEFAULT_CONCURRENCY = 2
CONCURRENCY_WARN_ABOVE = 8

# ---------------------------------------------------------------------------
# React live-progress heartbeat (persisted user preference).
#
# The browser polls the Gradio bridge while a transfer is in flight. The poll
# is useful, but on a slow Colab proxy a 1-second repaint can make the page
# feel busy. The owner asked for an explicit off switch; 0 means "no automatic
# polling" and the manual queue.refresh button stays available. The default is
# unchanged (1000 ms) so existing behaviour is preserved.
# ---------------------------------------------------------------------------
AUTO_REFRESH_DEFAULT_MS = 1000
AUTO_REFRESH_OPTIONS = (0, 1000, 2000, 5000)

# ---------------------------------------------------------------------------
# Telegram download throughput and connection health (M45-T01).
#
# One Telethon client multiplexes every upload.getFile over a SINGLE MTProto
# TCP connection. Each request is latency-bound: roughly
#     per-stream throughput = 512 KiB / round-trip time.
# That is why a sequential 512 KiB reader plateaus around 1 MB/s on Colab and
# why flooding the same socket with one request per queued row produced
# "Request was unsuccessful 6 time(s)".
#
# Three independent, bounded knobs fix both sides of that problem:
#   TG_INFLIGHT_REQUESTS        requests in flight across ALL files
#   PARALLEL_DOWNLOAD_STREAMS   striped readers for ONE large file
#   MAX_CONCURRENT_TG_DOWNLOADS whole files downloading at the same time
#
# They are overridable per runtime so a slow Colab VM can be tuned down (and a
# fast one up) without rebuilding the package.
# ---------------------------------------------------------------------------
DOWNLOAD_REQUEST_SIZE = 512 * 1024


def _bounded_env_int(name: str, default: int, low: int, high: int) -> int:
    """Read a bounded integer override; never raise on a bad environment."""
    try:
        value = int(os.environ.get(name, default))
    except (TypeError, ValueError):
        value = default
    return max(low, min(value, high))


# Keep ordinary media on the simple sequential path; a second MTProto reader is
# only worthwhile for larger files where request latency dominates.
FAST_DOWNLOAD_MIN_BYTES = 1024 * 1024
PARALLEL_DOWNLOAD_MIN_BYTES = 2 * 1024 * 1024
# Favor many independent files in a batch. Large single-file transfers can opt into
# striped readers with TELEDRIVE_TG_STREAMS; the global request budget is shared.
PARALLEL_DOWNLOAD_STREAMS = _bounded_env_int("TELEDRIVE_TG_STREAMS", 1, 1, 16)
TG_INFLIGHT_REQUESTS = _bounded_env_int("TELEDRIVE_TG_INFLIGHT", 72, 1, 100)
MAX_CONCURRENT_TG_DOWNLOADS = _bounded_env_int("TELEDRIVE_TG_FILES", 100, 1, 100)
# M45-T04: large sliding reorder window (72 chunks = 36 MiB) for 12 independent
# FastTelethon MTProtoSender TCP connections so fast sockets never barrier-stall.
PARALLEL_DOWNLOAD_WINDOW_CHUNKS = max(PARALLEL_DOWNLOAD_STREAMS * 6, 64)
# Completed files allowed to wait for the single Drive uploader. This is the
# disk backpressure of the download/upload pipeline: downloads pause instead of
# filling local disk with finished .part files.
MAX_PENDING_UPLOADS = _bounded_env_int("TELEDRIVE_UPLOAD_BUFFER", 100, 1, 100)

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
    version: str = "5.0.0"
    spec_version: str = "5.0.0"
    extra: dict = field(default_factory=dict)

    def concurrency_value(self) -> int:
        if self.manual_concurrency is not None:
            return max(CONCURRENCY_MIN, min(self.manual_concurrency, HARD_CONCURRENCY_CAP))
        return CONCURRENCY_LEVELS.get(self.concurrency, DEFAULT_CONCURRENCY)


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
