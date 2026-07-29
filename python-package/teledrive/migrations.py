"""Schema migrations for SQLite."""
from __future__ import annotations

from .database import cursor


SCHEMA = [
    # v1
    """
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY,
        applied_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS media_items (
        id TEXT PRIMARY KEY,
        source_key TEXT UNIQUE,
        chat_id INTEGER,
        chat_title TEXT,
        message_id INTEGER,
        file_unique_id TEXT,
        original_name TEXT,
        safe_name TEXT,
        media_type TEXT,
        extension TEXT,
        size_bytes INTEGER,
        message_date TEXT,
        state TEXT NOT NULL DEFAULT 'Pending',
        download_pct REAL DEFAULT 0,
        upload_pct REAL DEFAULT 0,
        temp_path TEXT,
        drive_file_id TEXT,
        drive_folder_id TEXT,
        attempts INTEGER DEFAULT 0,
        last_error_code TEXT,
        last_error_msg TEXT,
        priority INTEGER DEFAULT 100,
        created_at TEXT,
        updated_at TEXT
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_media_state ON media_items(state);",
    "CREATE INDEX IF NOT EXISTS idx_media_priority ON media_items(priority);",
    """
    CREATE TABLE IF NOT EXISTS transfer_jobs (
        id TEXT PRIMARY KEY,
        started_at TEXT,
        ended_at TEXT,
        note TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS events (
        id TEXT PRIMARY KEY,
        item_id TEXT,
        kind TEXT,
        message TEXT,
        at TEXT,
        data TEXT
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_events_at ON events(at);",
    """
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at TEXT
    );
    """,
]

CURRENT_VERSION = 1


def apply() -> int:
    from .utils import now_iso
    with cursor() as c:
        c.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);")
        r = c.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
        current = r["v"] if r and r["v"] is not None else 0
        if current >= CURRENT_VERSION:
            return current
        for stmt in SCHEMA:
            c.execute(stmt)
        c.execute("INSERT OR IGNORE INTO schema_version (version, applied_at) VALUES (?, ?)",
                  (CURRENT_VERSION, now_iso()))
        return CURRENT_VERSION
