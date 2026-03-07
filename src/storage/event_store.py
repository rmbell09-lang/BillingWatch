"""
BillingWatch EventStore — SQLite persistence layer.

Schema:
  events(id, event_id, event_type, payload_json, received_at, processed)

Usage:
    from src.storage.event_store import EventStore

    store = EventStore()                          # defaults to billingwatch.db
    store.insert_event(event_dict)
    recent = store.get_events_since(3600)         # last hour
    store.mark_processed("evt_xxx")
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


_DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "billingwatch.db"

_CREATE_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id     TEXT    NOT NULL UNIQUE,
    event_type   TEXT    NOT NULL,
    payload_json TEXT    NOT NULL,
    received_at  REAL    NOT NULL,
    processed    INTEGER NOT NULL DEFAULT 0
);
"""

_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);",
    "CREATE INDEX IF NOT EXISTS idx_events_received_at ON events(received_at);",
    "CREATE INDEX IF NOT EXISTS idx_events_processed ON events(processed);",
]


class EventStore:
    """Thread-safe SQLite-backed event store for Stripe webhook events."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = str(db_path or _DEFAULT_DB_PATH)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")  # concurrent reads + writes
        return conn

    def _init_db(self) -> None:
        """Create tables and indexes if they don't exist."""
        with self._connect() as conn:
            conn.execute(_CREATE_EVENTS_TABLE)
            for idx_sql in _CREATE_INDEXES:
                conn.execute(idx_sql)
            conn.commit()

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def insert_event(self, event: Dict[str, Any]) -> int:
        """
        Persist a Stripe event dict.

        Returns the row id on insert, or 0 if the event_id already exists
        (idempotent — safe to call multiple times for the same event).
        """
        event_id = event.get("id", f"unknown_{int(time.time())}")
        event_type = event.get("type", "unknown")
        payload_json = json.dumps(event)
        received_at = time.time()

        try:
            with self._connect() as conn:
                cur = conn.execute(
                    """
                    INSERT OR IGNORE INTO events
                        (event_id, event_type, payload_json, received_at, processed)
                    VALUES (?, ?, ?, ?, 0)
                    """,
                    (event_id, event_type, payload_json, received_at),
                )
                conn.commit()
                return cur.lastrowid or 0
        except sqlite3.Error as exc:
            print(f"[EventStore] insert_event error: {exc}")
            return 0

    def mark_processed(self, event_id: str) -> bool:
        """
        Mark an event as processed by its Stripe event ID.

        Returns True if a row was updated.
        """
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    "UPDATE events SET processed = 1 WHERE event_id = ?",
                    (event_id,),
                )
                conn.commit()
                return cur.rowcount > 0
        except sqlite3.Error as exc:
            print(f"[EventStore] mark_processed error: {exc}")
            return False

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_events_since(
        self,
        seconds: float,
        event_type: Optional[str] = None,
        unprocessed_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Return events received within the past `seconds` seconds.

        Args:
            seconds: Rolling window size in seconds.
            event_type: Optional filter by event type (e.g. 'charge.failed').
            unprocessed_only: If True, return only events not yet marked processed.

        Returns list of parsed event dicts (full Stripe payload).
        """
        cutoff = time.time() - seconds
        query = "SELECT payload_json FROM events WHERE received_at >= ?"
        params: List[Any] = [cutoff]

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        if unprocessed_only:
            query += " AND processed = 0"

        query += " ORDER BY received_at ASC"

        try:
            with self._connect() as conn:
                rows = conn.execute(query, params).fetchall()
                return [json.loads(row["payload_json"]) for row in rows]
        except sqlite3.Error as exc:
            print(f"[EventStore] get_events_since error: {exc}")
            return []

    def get_event_count(
        self,
        seconds: float,
        event_type: Optional[str] = None,
    ) -> int:
        """Return count of events in the rolling window (lightweight)."""
        cutoff = time.time() - seconds
        query = "SELECT COUNT(*) FROM events WHERE received_at >= ?"
        params: List[Any] = [cutoff]
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        try:
            with self._connect() as conn:
                row = conn.execute(query, params).fetchone()
                return row[0] if row else 0
        except sqlite3.Error as exc:
            print(f"[EventStore] get_event_count error: {exc}")
            return 0

    def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return the most recent N events (full payload dicts)."""
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT payload_json FROM events ORDER BY received_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
                return [json.loads(row["payload_json"]) for row in rows]
        except sqlite3.Error as exc:
            print(f"[EventStore] get_recent error: {exc}")
            return []

    def total_count(self) -> int:
        """Total number of stored events."""
        try:
            with self._connect() as conn:
                row = conn.execute("SELECT COUNT(*) FROM events").fetchone()
                return row[0] if row else 0
        except sqlite3.Error as exc:
            return 0
