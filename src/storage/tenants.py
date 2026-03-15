"""
BillingWatch TenantStore — multi-tenant API key management.

Schema:
  tenants(id, api_key_hash, api_key_prefix, tier, email, created_at,
          stripe_account_id, event_count_month, last_reset)

Usage:
    store = TenantStore()
    result = store.create_tenant("user@example.com", tier="free")
    # result["api_key"] — return ONCE, never stored in plaintext
    tenant = store.get_by_key("bw_live_<uuid>")
    tenant = store.get_by_id("ten_<uuid>")
"""

import hashlib
import secrets
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import bcrypt

_DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "billingwatch.db"

_CREATE_TENANTS_TABLE = """
CREATE TABLE IF NOT EXISTS tenants (
    id                  TEXT PRIMARY KEY,
    api_key_hash        TEXT UNIQUE NOT NULL,
    api_key_prefix      TEXT NOT NULL,
    tier                TEXT NOT NULL DEFAULT 'free',
    email               TEXT NOT NULL,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    stripe_account_id   TEXT,
    event_count_month   INTEGER NOT NULL DEFAULT 0,
    last_reset          TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

_CREATE_TENANT_INDEX = (
    "CREATE INDEX IF NOT EXISTS idx_tenants_email ON tenants(email);"
)

TIER_EVENT_LIMITS = {
    "free": 10_000,
    "pro": 100_000,
}


class TenantStore:
    """Thread-safe SQLite-backed store for BillingWatch tenants."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = str(db_path or _DEFAULT_DB_PATH)
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.Lock()
        self._init_db()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            self._conn = conn
        return self._conn

    def _execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            try:
                cur = self._get_conn().execute(sql, params)
                self._get_conn().commit()
                return cur
            except sqlite3.OperationalError:
                try:
                    if self._conn:
                        self._conn.close()
                except Exception:
                    pass
                self._conn = None
                cur = self._get_conn().execute(sql, params)
                self._get_conn().commit()
                return cur

    def _init_db(self) -> None:
        with self._lock:
            conn = self._get_conn()
            conn.execute(_CREATE_TENANTS_TABLE)
            conn.execute(_CREATE_TENANT_INDEX)
            conn.commit()

    # ------------------------------------------------------------------
    # Key helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_api_key() -> str:
        """Generate a bw_live_<32-hex> key."""
        token = secrets.token_hex(16)
        return f"bw_live_{token}"

    @staticmethod
    def _hash_key(raw_key: str) -> str:
        """bcrypt hash of the raw API key."""
        return bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt(rounds=12)).decode()

    @staticmethod
    def _verify_key(raw_key: str, key_hash: str) -> bool:
        """Constant-time bcrypt verify."""
        try:
            return bcrypt.checkpw(raw_key.encode(), key_hash.encode())
        except Exception:
            return False

    @staticmethod
    def _key_prefix(raw_key: str) -> str:
        """First 12 chars for safe display (e.g. 'bw_live_ab12')."""
        return raw_key[:12]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_tenant(
        self, email: str, tier: str = "free", stripe_account_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new tenant. Returns dict including the raw api_key — store it
        somewhere safe, it will NEVER be returned again.
        """
        if tier not in TIER_EVENT_LIMITS:
            raise ValueError(f"Unknown tier: {tier!r}")

        tenant_id = f"ten_{uuid.uuid4().hex[:12]}"
        raw_key = self._generate_api_key()
        key_hash = self._hash_key(raw_key)
        prefix = self._key_prefix(raw_key)
        now = datetime.utcnow().isoformat()

        self._execute(
            """
            INSERT INTO tenants
              (id, api_key_hash, api_key_prefix, tier, email,
               created_at, stripe_account_id, event_count_month, last_reset)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (tenant_id, key_hash, prefix, tier, email, now, stripe_account_id, now),
        )

        return {
            "tenant_id": tenant_id,
            "api_key": raw_key,  # plaintext — return once, never stored
            "api_key_prefix": prefix,
            "tier": tier,
            "email": email,
            "created_at": now,
            "webhook_url": f"/webhook/{tenant_id}",
        }

    def get_by_id(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a tenant by ID (no key material returned)."""
        cur = self._execute(
            "SELECT id, api_key_prefix, tier, email, created_at, "
            "stripe_account_id, event_count_month, last_reset "
            "FROM tenants WHERE id = ?",
            (tenant_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def get_by_key(self, raw_key: str) -> Optional[Dict[str, Any]]:
        """
        Verify raw_key against all stored hashes and return the tenant if valid.
        NOTE: This iterates all rows — fine for small tenant counts (<1000).
              For scale, switch to prefix-based lookup.
        """
        if not raw_key.startswith("bw_"):
            return None
        prefix = self._key_prefix(raw_key)
        cur = self._execute(
            "SELECT id, api_key_hash, api_key_prefix, tier, email, created_at, "
            "stripe_account_id, event_count_month, last_reset "
            "FROM tenants WHERE api_key_prefix = ?",
            (prefix,),
        )
        rows = cur.fetchall()
        for row in rows:
            if self._verify_key(raw_key, row["api_key_hash"]):
                return {
                    "id": row["id"],
                    "api_key_prefix": row["api_key_prefix"],
                    "tier": row["tier"],
                    "email": row["email"],
                    "created_at": row["created_at"],
                    "stripe_account_id": row["stripe_account_id"],
                    "event_count_month": row["event_count_month"],
                    "last_reset": row["last_reset"],
                }
        return None

    def increment_event_count(self, tenant_id: str) -> None:
        """Increment monthly event counter for a tenant."""
        self._execute(
            "UPDATE tenants SET event_count_month = event_count_month + 1 WHERE id = ?",
            (tenant_id,),
        )

    def check_quota(self, tenant: Dict[str, Any]) -> bool:
        """Return True if tenant is under their monthly event quota."""
        limit = TIER_EVENT_LIMITS.get(tenant["tier"], 0)
        return tenant["event_count_month"] < limit

    def reset_monthly_counts(self) -> int:
        """Reset event_count_month for all tenants. Called by cron on 1st of month."""
        now = datetime.utcnow().isoformat()
        cur = self._execute(
            "UPDATE tenants SET event_count_month = 0, last_reset = ?", (now,)
        )
        return cur.rowcount

    def list_tenants(self, limit: int = 100) -> list:
        """Admin: list tenants (no key hashes)."""
        cur = self._execute(
            "SELECT id, api_key_prefix, tier, email, created_at, "
            "event_count_month FROM tenants LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]
