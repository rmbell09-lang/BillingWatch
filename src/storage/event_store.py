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
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


_DEFAULT_DB_PATH = Path(os.environ.get("DB_PATH", "") or str(Path(__file__).parent.parent.parent / "billingwatch.db"))

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
    """
    Thread-safe SQLite-backed event store for Stripe webhook events.

    Uses a single shared connection (lazy-init) to avoid file descriptor
    exhaustion on macOS — the per-call sqlite3.connect() pattern leaks FDs
    because the context manager commits but doesn't reliably close.
    """

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = str(db_path or _DEFAULT_DB_PATH)
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.Lock()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Return the shared connection, creating it if needed."""
        if self._conn is None:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            self._conn = conn
        return self._conn

    def _execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a single statement, reconnecting once on OperationalError."""
        with self._lock:
            try:
                return self._get_conn().execute(sql, params)
            except sqlite3.OperationalError:
                # Connection may have gone stale — reset and retry once
                try:
                    if self._conn:
                        self._conn.close()
                except Exception:
                    pass
                self._conn = None
                return self._get_conn().execute(sql, params)

    def _commit(self) -> None:
        with self._lock:
            if self._conn:
                self._conn.commit()

    def _init_db(self) -> None:
        """Create tables and indexes if they don't exist."""
        with self._lock:
            conn = self._get_conn()
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
            cur = self._execute(
                """
                INSERT OR IGNORE INTO events
                    (event_id, event_type, payload_json, received_at, processed)
                VALUES (?, ?, ?, ?, 0)
                """,
                (event_id, event_type, payload_json, received_at),
            )
            self._commit()
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
            cur = self._execute(
                "UPDATE events SET processed = 1 WHERE event_id = ?",
                (event_id,),
            )
            self._commit()
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
        params: list = [cutoff]

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        if unprocessed_only:
            query += " AND processed = 0"

        query += " ORDER BY received_at ASC"

        try:
            rows = self._execute(query, tuple(params)).fetchall()
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
        params: list = [cutoff]
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        try:
            row = self._execute(query, tuple(params)).fetchone()
            return row[0] if row else 0
        except sqlite3.Error as exc:
            print(f"[EventStore] get_event_count error: {exc}")
            return 0

    def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return the most recent N events (full payload dicts)."""
        try:
            rows = self._execute(
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
            row = self._execute("SELECT COUNT(*) FROM events").fetchone()
            return row[0] if row else 0
        except sqlite3.Error as exc:
            return 0

    def get_counts_by_type(self, window_sec: Optional[float] = None) -> dict:
        """
        Return a dict of {event_type: count} for events in the given window.
        If window_sec is None, counts all events.
        """
        try:
            if window_sec is not None:
                cutoff = time.time() - window_sec
                rows = self._execute(
                    "SELECT event_type, COUNT(*) FROM events WHERE received_at >= ? GROUP BY event_type ORDER BY COUNT(*) DESC",
                    (cutoff,),
                ).fetchall()
            else:
                rows = self._execute(
                    "SELECT event_type, COUNT(*) FROM events GROUP BY event_type ORDER BY COUNT(*) DESC"
                ).fetchall()
            return {row[0]: row[1] for row in rows}
        except Exception:
            return {}
