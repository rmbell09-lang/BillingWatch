# BillingWatch — Multi-Tenant Architecture Spec (v2)
*Drafted: 2026-03-10. For Ray review before coding begins.*
*Addresses NEXT_TASKS.md #7 — required for paid revenue model.*

---

## Goal
Enable multiple customers to run BillingWatch from a single hosted instance — each with isolated data, their own Stripe webhook endpoint, and configurable alert channels. Unlock Free/Pro pricing tiers.

---

## Pricing Tiers

| Feature | Free | Pro ($9/mo) |
|---------|------|-------------|
| Stripe accounts | 1 | Unlimited |
| Events/month | 10,000 | 100,000 |
| Alert channels | Email only | Email + Slack + Discord |
| Detectors | All 10 | All 10 |
| False positive marking | ✓ | ✓ |
| Threshold tuning | ✗ | ✓ |
| Dashboard access | ✓ | ✓ |
| Data retention | 30 days | 90 days |
| Support | GitHub issues | Priority email |

---

## API Key Auth Schema

### New SQLite Table: `tenants`
```sql
CREATE TABLE tenants (
    id          TEXT PRIMARY KEY,          -- UUID, e.g. "ten_abc123"
    api_key     TEXT UNIQUE NOT NULL,      -- "bw_live_<uuid4>", hashed w/ bcrypt
    api_key_prefix TEXT NOT NULL,          -- "bw_live_abc1" for display
    tier        TEXT DEFAULT 'free',       -- 'free' | 'pro'
    email       TEXT NOT NULL,
    created_at  TEXT DEFAULT (datetime('now')),
    stripe_account_id TEXT,               -- optional, for validation
    event_count_month INT DEFAULT 0,      -- reset monthly via cron
    last_reset  TEXT DEFAULT (datetime('now'))
);
```

### Auth Middleware (FastAPI dependency)
```python
# src/api/deps.py
from fastapi import Header, HTTPException
from .storage.tenants import TenantStore

async def get_current_tenant(authorization: str = Header(...)):
    if not authorization.startswith("Bearer bw_"):
        raise HTTPException(401, "Invalid API key format")
    key = authorization.removeprefix("Bearer ")
    tenant = TenantStore.get_by_key(key)  # bcrypt verify
    if not tenant:
        raise HTTPException(401, "Invalid API key")
    return tenant
```

### Protected Routes Pattern
```python
@router.get("/metrics")
async def get_metrics(tenant = Depends(get_current_tenant)):
    return MetricsStore(tenant_id=tenant.id).get_all()
```

### Public Endpoints (no auth)
- `POST /webhook/{tenant_id}` — webhook receiver (Stripe HMAC validates instead)
- `GET /health`
- `POST /tenants/register` — sign-up

---

## Per-Tenant Storage Strategy

**Approach: Single DB, tenant_id column (simpler than separate DBs)**

Migrate existing tables to add `tenant_id TEXT NOT NULL`:
- `events` → add `tenant_id`
- `anomalies` → add `tenant_id`
- `false_positives` → add `tenant_id`
- `thresholds` → add `tenant_id`
- `beta_feedback` → add `tenant_id`

All queries get `WHERE tenant_id = ?` filter. Indexes on `tenant_id` + existing columns.

**Alternative (if isolation is critical):** One SQLite file per tenant at `data/{tenant_id}.db`. More complex but total isolation. Not recommended for v2.

---

## Webhook Endpoint Change

Current: `POST /webhook` (single global endpoint)
v2: `POST /webhook/{tenant_id}` (tenant-scoped)

Stripe webhook URL becomes: `https://billingwatch.io/webhook/ten_abc123`

Stripe HMAC verified with tenant's webhook secret (stored in `tenants` table, encrypted at rest).

---

## Tenant Registration Flow

1. `POST /tenants/register` → `{email, tier}` → returns `{api_key, webhook_url, tenant_id}`
2. Ray (or self-serve UI) sends welcome email with QUICKSTART.md instructions
3. Tenant adds `webhook_url` to Stripe dashboard
4. First webhook event auto-confirms setup

---

## Event Quota Enforcement

```python
# In webhook handler, before processing:
if tenant.event_count_month >= TIER_LIMITS[tenant.tier]:
    return {"status": "quota_exceeded"}
tenant.increment_event_count()
```

Cron resets `event_count_month = 0` on 1st of each month.

---

## Migration Path (Single → Multi-Tenant)

1. **Phase 1**: Add `tenants` table + auth middleware (non-breaking — wrap existing routes)
2. **Phase 2**: Add `tenant_id` columns to all tables + backfill with `tenant_id = 'default'`
3. **Phase 3**: Migrate webhook endpoint from `/webhook` → `/webhook/{tenant_id}`
4. **Phase 4**: Add `POST /tenants/register` + `GET /tenants/me`
5. **Phase 5**: Wire Stripe billing (Stripe Checkout → Pro tier upgrade)

**Estimated effort:** ~10-12 hours across 5 phases. Phases 1-4 can ship without Stripe billing (manual Pro upgrades by Ray). Phase 5 = revenue unlock.

---

## Open Questions for Ray

1. **Hosted vs self-hosted SaaS?** Self-hosted users won't have a shared instance — do we want a hosted option in parallel?
2. **bcrypt or argon2** for key hashing? (bcrypt is already in Python stdlib-ish, argon2 is stronger)
3. **Stripe billing integration**: use Stripe Checkout (fastest) or build custom? Checkout recommended.
4. **Domain**: billingwatch.io or billingwatch.pages.dev for the hosted instance?

---

## Next Steps (after Ray reviews)
- [ ] Ray approves approach
- [ ] Lucky implements Phase 1 (tenants table + auth middleware)
- [ ] Lucky implements Phase 2-4 (tenant isolation + registration)
- [ ] Ray wires Stripe billing for Phase 5
