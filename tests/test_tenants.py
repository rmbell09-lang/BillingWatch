"""
Tests for multi-tenant API key auth — TenantStore + /tenants endpoints.
"""
import pytest
import tempfile
import os

from fastapi.testclient import TestClient


# ------------------------------------------------------------------
# TenantStore unit tests
# ------------------------------------------------------------------

class TestTenantStore:
    def setup_method(self):
        from src.storage.tenants import TenantStore
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.store = TenantStore(db_path=self.tmp.name)

    def teardown_method(self):
        try:
            if self.store._conn:
                self.store._conn.close()
        except Exception:
            pass
        os.unlink(self.tmp.name)

    def test_create_tenant_returns_api_key(self):
        result = self.store.create_tenant("alice@example.com", tier="free")
        assert result["api_key"].startswith("bw_live_")
        assert result["tenant_id"].startswith("ten_")
        assert result["tier"] == "free"
        assert result["email"] == "alice@example.com"
        assert "/webhook/" in result["webhook_url"]

    def test_api_key_not_stored_in_plaintext(self):
        """The raw API key must not appear in the DB."""
        result = self.store.create_tenant("bob@example.com")
        raw_key = result["api_key"]
        # Read the raw DB row
        import sqlite3
        conn = sqlite3.connect(self.tmp.name)
        row = conn.execute("SELECT api_key_hash FROM tenants WHERE id=?", (result["tenant_id"],)).fetchone()
        conn.close()
        assert raw_key not in row[0], "Raw key found in DB — must be hashed"
        assert row[0].startswith("$2b$"), "Hash should be bcrypt"

    def test_get_by_key_valid(self):
        result = self.store.create_tenant("carol@example.com")
        tenant = self.store.get_by_key(result["api_key"])
        assert tenant is not None
        assert tenant["id"] == result["tenant_id"]
        assert tenant["email"] == "carol@example.com"

    def test_get_by_key_invalid(self):
        self.store.create_tenant("dave@example.com")
        tenant = self.store.get_by_key("bw_live_" + "x" * 32)
        assert tenant is None

    def test_get_by_key_wrong_format(self):
        tenant = self.store.get_by_key("not_a_valid_key")
        assert tenant is None

    def test_get_by_id(self):
        result = self.store.create_tenant("eve@example.com")
        tenant = self.store.get_by_id(result["tenant_id"])
        assert tenant is not None
        assert tenant["email"] == "eve@example.com"

    def test_get_by_id_missing(self):
        tenant = self.store.get_by_id("ten_doesnotexist")
        assert tenant is None

    def test_pro_tier(self):
        result = self.store.create_tenant("frank@example.com", tier="pro")
        assert result["tier"] == "pro"
        tenant = self.store.get_by_key(result["api_key"])
        assert tenant["tier"] == "pro"

    def test_invalid_tier_raises(self):
        with pytest.raises(ValueError, match="Unknown tier"):
            self.store.create_tenant("bad@example.com", tier="enterprise")

    def test_quota_free_tier(self):
        from src.storage.tenants import TIER_EVENT_LIMITS
        result = self.store.create_tenant("grace@example.com", tier="free")
        tenant = self.store.get_by_key(result["api_key"])
        assert self.store.check_quota(tenant) is True
        # Simulate hitting limit
        import sqlite3
        conn = sqlite3.connect(self.tmp.name)
        conn.execute(
            "UPDATE tenants SET event_count_month=? WHERE id=?",
            (TIER_EVENT_LIMITS["free"], result["tenant_id"])
        )
        conn.commit()
        conn.close()
        # Re-fetch
        tenant2 = self.store.get_by_key(result["api_key"])
        assert self.store.check_quota(tenant2) is False

    def test_increment_event_count(self):
        result = self.store.create_tenant("hank@example.com")
        tid = result["tenant_id"]
        self.store.increment_event_count(tid)
        self.store.increment_event_count(tid)
        tenant = self.store.get_by_id(tid)
        assert tenant["event_count_month"] == 2

    def test_reset_monthly_counts(self):
        result = self.store.create_tenant("ivy@example.com")
        tid = result["tenant_id"]
        self.store.increment_event_count(tid)
        self.store.increment_event_count(tid)
        self.store.reset_monthly_counts()
        tenant = self.store.get_by_id(tid)
        assert tenant["event_count_month"] == 0

    def test_multiple_tenants_dont_cross(self):
        r1 = self.store.create_tenant("j@example.com")
        r2 = self.store.create_tenant("k@example.com")
        t1 = self.store.get_by_key(r1["api_key"])
        t2 = self.store.get_by_key(r2["api_key"])
        assert t1["id"] != t2["id"]
        # Key1 doesn't match tenant 2
        assert self.store.get_by_key(r1["api_key"])["id"] == r1["tenant_id"]
        assert self.store.get_by_key(r2["api_key"])["id"] == r2["tenant_id"]


# ------------------------------------------------------------------
# API endpoint integration tests
# ------------------------------------------------------------------

@pytest.fixture
def client(tmp_path):
    """TestClient with a fresh DB for each test."""
    from src.storage.tenants import TenantStore
    import src.api.routes.tenants as tenants_module
    import src.api.deps as deps_module

    db_file = str(tmp_path / "test.db")
    store = TenantStore(db_path=db_file)
    tenants_module._store = store
    deps_module._store = store

    from src.api.main import create_app
    app = create_app()
    # Re-register tenants router with fresh store
    from src.api.routes import tenants as tenants_route
    tenants_route._store = store

    with TestClient(app) as c:
        yield c, store


class TestTenantsAPI:
    def test_register_success(self, client):
        c, store = client
        resp = c.post("/tenants/register", json={"email": "new@test.com", "tier": "free"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["api_key"].startswith("bw_live_")
        assert data["tenant_id"].startswith("ten_")
        assert "webhook_url" in data
        assert "Save your api_key" in data["message"]

    def test_register_pro_tier(self, client):
        c, store = client
        resp = c.post("/tenants/register", json={"email": "pro@test.com", "tier": "pro"})
        assert resp.status_code == 201
        assert resp.json()["tier"] == "pro"

    def test_register_invalid_tier(self, client):
        c, store = client
        resp = c.post("/tenants/register", json={"email": "x@test.com", "tier": "ultra"})
        assert resp.status_code == 400

    def test_me_authenticated(self, client):
        c, store = client
        reg = c.post("/tenants/register", json={"email": "me@test.com"}).json()
        resp = c.get("/tenants/me", headers={"Authorization": f"Bearer {reg['api_key']}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "me@test.com"
        assert data["event_limit_month"] == 10_000
        assert data["quota_remaining"] == 10_000

    def test_me_no_auth(self, client):
        c, _ = client
        resp = c.get("/tenants/me")
        assert resp.status_code == 422  # missing required header

    def test_me_bad_key(self, client):
        c, _ = client
        resp = c.get("/tenants/me", headers={"Authorization": "Bearer bw_live_badkey000000000000000000000000"})
        assert resp.status_code == 401

    def test_me_wrong_format(self, client):
        c, _ = client
        resp = c.get("/tenants/me", headers={"Authorization": "Bearer not_a_bw_key"})
        assert resp.status_code == 401
