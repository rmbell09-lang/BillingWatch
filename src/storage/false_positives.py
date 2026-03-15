"""False Positive Store — tracks which alerts were marked as false positives.

Uses a SHARED connection to avoid file descriptor exhaustion.
"""
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional


_DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "billingwatch.db"


class FalsePositiveStore:
    """SQLite-backed false positive tracking for anomaly alerts.

    Reuses a single connection per instance to avoid FD exhaustion.
    """

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = str(db_path or _DEFAULT_DB_PATH)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL;")
        return self._conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS false_positives (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id   INTEGER NOT NULL UNIQUE,
                detector   TEXT    NOT NULL,
                severity   TEXT    NOT NULL DEFAULT 'unknown',
                marked_at  REAL    NOT NULL,
                reason     TEXT    NOT NULL DEFAULT ''
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fp_detector ON false_positives(detector);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fp_alert_id ON false_positives(alert_id);")
        conn.commit()

    def mark_false_positive(self, alert_id: int, detector: str,
                            severity: str = "unknown", reason: str = "") -> bool:
        try:
            conn = self._get_conn()
            conn.execute(
                "INSERT OR IGNORE INTO false_positives (alert_id, detector, severity, marked_at, reason) VALUES (?, ?, ?, ?, ?)",
                (alert_id, detector, severity, time.time(), reason),
            )
            conn.commit()
            return True
        except sqlite3.Error as exc:
            print(f"[FPStore] mark error: {exc}")
            return False

    def unmark_false_positive(self, alert_id: int) -> bool:
        try:
            conn = self._get_conn()
            cur = conn.execute("DELETE FROM false_positives WHERE alert_id = ?", (alert_id,))
            conn.commit()
            return cur.rowcount > 0
        except sqlite3.Error as exc:
            print(f"[FPStore] unmark error: {exc}")
            return False

    def is_false_positive(self, alert_id: int) -> bool:
        try:
            row = self._get_conn().execute(
                "SELECT 1 FROM false_positives WHERE alert_id = ?", (alert_id,)
            ).fetchone()
            return row is not None
        except sqlite3.Error:
            return False

    def get_fp_count_by_detector(self) -> Dict[str, int]:
        try:
            rows = self._get_conn().execute(
                "SELECT detector, COUNT(*) as cnt FROM false_positives GROUP BY detector"
            ).fetchall()
            return {row["detector"]: row["cnt"] for row in rows}
        except sqlite3.Error:
            return {}

    def get_total_fp_count(self) -> int:
        try:
            row = self._get_conn().execute("SELECT COUNT(*) FROM false_positives").fetchone()
            return row[0] if row else 0
        except sqlite3.Error:
            return 0

    def get_recent_fps(self, limit: int = 20) -> List[Dict]:
        try:
            rows = self._get_conn().execute(
                "SELECT * FROM false_positives ORDER BY marked_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error:
            return []
