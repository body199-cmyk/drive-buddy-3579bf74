"""SQLite persistence (WAL). Local runtime state; Drive holds durable state."""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from typing import Any, Iterable, Optional

from .config import DB_PATH, assert_local_path
from .models import MediaItem
from .utils import now_iso, new_id


_lock = threading.RLock()
_conn: sqlite3.Connection | None = None


def _connect() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        assert_local_path(DB_PATH, what="SQLite database")
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, isolation_level=None)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA synchronous=NORMAL")
        _conn.execute("PRAGMA foreign_keys=ON")
    return _conn


@contextmanager
def cursor():
    with _lock:
        c = _connect().cursor()
        try:
            yield c
        finally:
            c.close()


def journal_mode() -> str:
    """Return the active SQLite journal mode (expected: ``wal``)."""
    with cursor() as c:
        row = c.execute("PRAGMA journal_mode").fetchone()
    return str(row[0]).lower() if row else ""


def close() -> None:
    global _conn
    with _lock:
        if _conn is not None:
            _conn.close()
            _conn = None


# ---------- MediaItem CRUD ----------

MEDIA_COLS = [f.name for f in MediaItem.__dataclass_fields__.values()]  # type: ignore


def upsert_item(item: MediaItem) -> None:
    item.updated_at = now_iso()
    cols = ",".join(MEDIA_COLS)
    ph = ",".join("?" for _ in MEDIA_COLS)
    setters = ",".join(f"{c}=excluded.{c}" for c in MEDIA_COLS if c != "id")
    with cursor() as c:
        c.execute(
            f"INSERT INTO media_items ({cols}) VALUES ({ph}) "
            f"ON CONFLICT(id) DO UPDATE SET {setters}",
            [getattr(item, k) for k in MEDIA_COLS],
        )


def get_item(item_id: str) -> Optional[MediaItem]:
    with cursor() as c:
        r = c.execute("SELECT * FROM media_items WHERE id=?", (item_id,)).fetchone()
        return _row_to_item(r) if r else None


def find_by_source_key(source_key: str) -> Optional[MediaItem]:
    with cursor() as c:
        r = c.execute("SELECT * FROM media_items WHERE source_key=?", (source_key,)).fetchone()
        return _row_to_item(r) if r else None


def list_items(state: str | None = None, limit: int = 500) -> list[MediaItem]:
    with cursor() as c:
        if state:
            rows = c.execute(
                "SELECT * FROM media_items WHERE state=? ORDER BY priority, created_at LIMIT ?",
                (state, limit),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM media_items ORDER BY priority, created_at LIMIT ?", (limit,)
            ).fetchall()
        return [_row_to_item(r) for r in rows]


def items_in_states(states: Iterable[str]) -> list[MediaItem]:
    states = list(states)
    if not states:
        return []
    marks = ",".join("?" for _ in states)
    with cursor() as c:
        rows = c.execute(
            f"SELECT * FROM media_items WHERE state IN ({marks}) ORDER BY priority, created_at",
            states,
        ).fetchall()
        return [_row_to_item(r) for r in rows]


def delete_item(item_id: str) -> None:
    """Delete a queue ROW. Never touches a file already uploaded to Drive."""
    with cursor() as c:
        c.execute("DELETE FROM media_items WHERE id=?", (item_id,))
        c.execute("DELETE FROM events WHERE item_id=?", (item_id,))


def counts_by_state() -> dict[str, int]:
    with cursor() as c:
        rows = c.execute("SELECT state, COUNT(*) FROM media_items GROUP BY state").fetchall()
        return {r[0]: r[1] for r in rows}


def _row_to_item(row: sqlite3.Row) -> MediaItem:
    return MediaItem(**{k: row[k] for k in row.keys() if k in MediaItem.__dataclass_fields__})


# ---------- Events ----------

def add_event(item_id: str, kind: str, message: str, data: dict[str, Any] | None = None) -> None:
    with cursor() as c:
        c.execute(
            "INSERT INTO events (id, item_id, kind, message, at, data) VALUES (?,?,?,?,?,?)",
            (new_id(), item_id, kind, message, now_iso(), json.dumps(data or {}, ensure_ascii=False)),
        )


def recent_events(limit: int = 200) -> list[dict[str, Any]]:
    with cursor() as c:
        rows = c.execute(
            "SELECT * FROM events ORDER BY at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# ---------- Settings ----------

def set_setting(key: str, value: str) -> None:
    with cursor() as c:
        c.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, value, now_iso()),
        )


def get_setting(key: str, default: str = "") -> str:
    with cursor() as c:
        r = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return r["value"] if r else default
