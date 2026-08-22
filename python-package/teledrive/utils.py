"""Generic helpers used across the package."""
from __future__ import annotations

import hashlib
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


_INVALID_CHARS = re.compile(r'[\x00-\x1f<>:"/\\|?*]')


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id() -> str:
    return str(uuid.uuid4())


def sanitize_filename(name: str, fallback: str = "file", max_len: int = 120) -> str:
    """Strip control chars/path separators, keep unicode (Arabic ok), cap length preserving ext."""
    if not name or not name.strip():
        name = fallback
    name = _INVALID_CHARS.sub("_", name)
    name = name.strip().strip(".")
    if not name:
        name = fallback
    if len(name) <= max_len:
        return name
    root, dot, ext = name.rpartition(".")
    if dot and 0 < len(ext) <= 10:
        keep = max_len - len(ext) - 1
        return f"{root[:keep]}.{ext}"
    return name[:max_len]


def slugify(text: str, max_len: int = 40) -> str:
    text = re.sub(r"\s+", "_", (text or "").strip())
    text = re.sub(r"[^\w\-]+", "", text, flags=re.UNICODE)
    return (text or "chat")[:max_len]


def human_bytes(n: int | float | None) -> str:
    if n is None:
        return "—"
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "—"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} PB"


def human_duration(seconds: float | None) -> str:
    if seconds is None or seconds < 0 or seconds != seconds:
        return "—"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def source_key(chat_id: int | str, message_id: int | str, file_unique_id: str) -> str:
    return f"tg:{chat_id}:{message_id}:{file_unique_id}"


def sha256_file(path: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def monotonic() -> float:
    return time.monotonic()


def safe_disk_free(path: Path) -> int:
    # shutil.disk_usage works on every platform (POSIX and Windows);
    # os.statvfs is POSIX-only and silently reported 0 free bytes on Windows.
    try:
        if hasattr(os, "statvfs"):
            st = os.statvfs(path)
            return st.f_bavail * st.f_frsize
        import shutil
        return shutil.disk_usage(str(path)).free
    except Exception:
        return 0


def chunks(seq: Iterable[Any], n: int) -> Iterable[list[Any]]:
    buf: list[Any] = []
    for x in seq:
        buf.append(x)
        if len(buf) >= n:
            yield buf
            buf = []
    if buf:
        yield buf
