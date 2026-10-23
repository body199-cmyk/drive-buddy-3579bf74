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


def _ensure_writable_db_paths() -> None:
    import os
    assert_local_path(DB_PATH, what="SQLite database")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(DB_PATH.parent, 0o755)
    except OSError:
        pass
    for suffix in ("", "-wal", "-shm"):
        candidate = DB_PATH.with_name(DB_PATH.name + suffix)
        if candidate.exists():
            try:
                os.chmod(candidate, 0o644)
            except OSError:
                pass


def _connect() -> sqlite3.Connection:
    """Return a fully initialized connection; never cache a partial one.

    SQLite can fail while applying a PRAGMA (notably journal_mode=WAL) when
    the database, its directory, or the runtime mount has become readonly.
    Keep the new connection local until every initialization step succeeds so
    later calls cannot accidentally reuse a half-configured connection.
    """
    global _conn
    if _conn is None:
        _ensure_writable_db_paths()
        conn: sqlite3.Connection | None = None
        try:
            conn = sqlite3.connect(
                str(DB_PATH),
                timeout=30.0,
                check_same_thread=False,
                isolation_level=None,
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout=30000")
            mode_row = conn.execute("PRAGMA journal_mode=WAL").fetchone()
            mode = str(mode_row[0]).lower() if mode_row else ""
            if mode != "wal":
                raise sqlite3.OperationalError(
                    f"SQLite WAL initialization failed (reported mode: {mode or 'unknown'})"
                )
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA foreign_keys=ON")
        except Exception:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
            # Explicitly leave the singleton empty so the next attempt must
            # create and initialize a fresh connection.
            _conn = None
            raise
        _conn = conn
    return _conn


def _reconnect() -> sqlite3.Connection:
    global _conn
    if _conn is not None:
        try:
            _conn.close()
        except Exception:
            pass
        _conn = None
    return _connect()


class _RecoveringCursor:
    """Cursor wrapper that heals once if SQLite reports a stale readonly handle."""

    def __init__(self, raw_cursor: sqlite3.Cursor):
        self._cur = raw_cursor

    def execute(self, sql: str, parameters: Any = ()):
        try:
            return self._cur.execute(sql, parameters)
        except sqlite3.OperationalError as exc:
            msg = str(exc).lower()
            if any(k in msg for k in ("readonly", "locked", "disk i/o")):
                try:
                    self._cur.close()
                except Exception:
                    pass
                self._cur = _reconnect().cursor()
                return self._cur.execute(sql, parameters)
            raise

    def __getattr__(self, name: str) -> Any:
        return getattr(self._cur, name)

    def close(self) -> None:
        try:
            self._cur.close()
        except Exception:
            pass


@contextmanager
def cursor():
    with _lock:
        c = _RecoveringCursor(_connect().cursor())
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
