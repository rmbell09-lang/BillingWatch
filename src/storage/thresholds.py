"""
BillingWatch ThresholdStore — SQLite-backed detector threshold configuration.

Stores user-tunable thresholds so detector sensitivity can be adjusted at runtime
without restarting the server.  All values fall back to coded defaults when no
DB row exists yet.

Usage:
    from src.storage.thresholds import ThresholdStore

    store = ThresholdStore()
    thresholds = store.get()           # dict with all thresholds + defaults
    store.patch({"charge_failure_rate": 0.20})  # update one or more
"""

import os
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, Optional

_DEFAULT_DB_PATH = Path(os.environ.get("DB_PATH", "") or str(Path(__file__).parent.parent.parent / "billingwatch.db"))

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS thresholds (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

# Coded defaults — sourced from each detector's module-level constants
DEFAULTS: Dict[str, Any] = {
    "charge_failure_rate":      0.15,   # ChargeFailureDetector: FAILURE_THRESHOLD
    "revenue_drop_pct":         0.15,   # RevenueDropDetector: DROP_THRESHOLD
    "webhook_lag_warning_s":    300,    # WebhookLagDetector: WARNING_LAG_SECONDS
    "webhook_lag_critical_s":   1800,   # WebhookLagDetector: CRITICAL_LAG_SECONDS
    "duplicate_threshold":      2,      # DuplicateChargeDetector: DUPLICATE_THRESHOLD
    "dispute_rate_threshold":   0.01,   # FraudSpikeDetector: DISPUTE_RATE_THRESHOLD
    "refund_rate_threshold":    0.10,   # NegativeInvoiceDetector: REFUND_RATE_THRESHOLD
    "large_refund_usd":         500.0,  # NegativeInvoiceDetector: LARGE_REFUND_THRESHOLD_CENTS / 100
}

# Map each key to (min, max) for basic validation
_BOUNDS: Dict[str, tuple] = {
    "charge_failure_rate":      (0.01, 1.0),
    "revenue_drop_pct":         (0.01, 1.0),
    "webhook_lag_warning_s":    (10,   86400),
    "webhook_lag_critical_s":   (10,   86400),
    "duplicate_threshold":      (2,    100),
    "dispute_rate_threshold":   (0.001, 1.0),
    "refund_rate_threshold":    (0.01, 1.0),
    "large_refund_usd":         (1.0,  1_000_000.0),
}


class ThresholdStore:
    """
    Thread-safe SQLite-backed threshold store (singleton-friendly).

    Uses a single shared connection (lazy-init) to avoid file descriptor
    exhaustion on macOS — the per-call sqlite3.connect() pattern leaks FDs.
    Same pattern as EventStore and FalsePositiveStore.
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
        with self._lock:
            conn = self._get_conn()
            conn.execute(_CREATE_TABLE)
            conn.commit()

    def get(self) -> Dict[str, Any]:
        """Return all thresholds, filling missing keys from defaults."""
        rows = self._execute("SELECT key, value FROM thresholds").fetchall()
        stored = {r["key"]: r["value"] for r in rows}
        result: Dict[str, Any] = {}
        for key, default in DEFAULTS.items():
            raw = stored.get(key)
            if raw is None:
                result[key] = default
            else:
                result[key] = type(default)(raw)   # cast to same type as default
        return result

    def patch(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update one or more thresholds.  Returns the full updated threshold dict.
        Raises ValueError for unknown keys or out-of-bounds values.
        """
        for key, value in updates.items():
            if key not in DEFAULTS:
                raise ValueError(f"Unknown threshold key: '{key}'")
            lo, hi = _BOUNDS.get(key, (None, None))
            if lo is not None and not (lo <= float(value) <= hi):
                raise ValueError(f"'{key}' must be between {lo} and {hi}, got {value}")

        for key, value in updates.items():
            self._execute(
                "INSERT INTO thresholds(key, value) VALUES(?, ?)"
                " ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, str(value)),
            )
        self._commit()
        return self.get()
