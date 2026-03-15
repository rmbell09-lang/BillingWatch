"""
Tenant management routes.

  POST /tenants/register  — create a new tenant, returns API key (ONCE)
  GET  /tenants/me        — authenticated: return current tenant info
  GET  /tenants           — admin: list all tenants (no key hashes)
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from src.api.deps import get_current_tenant
from src.storage.tenants import TenantStore, TIER_EVENT_LIMITS

router = APIRouter(prefix="/tenants", tags=["tenants"])

_store: Optional[TenantStore] = None


def _get_store() -> TenantStore:
    global _store
    if _store is None:
        _store = TenantStore()
    return _store


# ------------------------------------------------------------------
# Request/Response models
# ------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: str
    tier: str = "free"


class RegisterResponse(BaseModel):
    tenant_id: str
    api_key: str
    api_key_prefix: str
    tier: str
    email: str
    webhook_url: str
    message: str


class TenantInfo(BaseModel):
    tenant_id: str
    api_key_prefix: str
    tier: str
    email: str
    created_at: str
    event_count_month: int
    event_limit_month: int
    quota_remaining: int


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register_tenant(body: RegisterRequest) -> RegisterResponse:
    """
    Create a new BillingWatch tenant. Returns API key **once** — store it safely.

    - `tier`: "free" (10k events/mo) or "pro" (100k events/mo)
    - The returned `api_key` is never stored in plaintext and cannot be recovered.
    - Use `webhook_url` as your Stripe webhook endpoint.
    """
    if body.tier not in TIER_EVENT_LIMITS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier '{body.tier}'. Valid tiers: {list(TIER_EVENT_LIMITS.keys())}",
        )

    result = _get_store().create_tenant(email=body.email, tier=body.tier)

    return RegisterResponse(
        tenant_id=result["tenant_id"],
        api_key=result["api_key"],
        api_key_prefix=result["api_key_prefix"],
        tier=result["tier"],
        email=result["email"],
        webhook_url=result["webhook_url"],
        message=(
            "Registration successful. Save your api_key — it will not be shown again. "
            f"Add your Stripe webhook to: {result['webhook_url']}"
        ),
    )


@router.get("/me", response_model=TenantInfo)
async def get_me(tenant: Dict[str, Any] = Depends(get_current_tenant)) -> TenantInfo:
    """Return info for the authenticated tenant."""
    limit = TIER_EVENT_LIMITS.get(tenant["tier"], 0)
    used = tenant["event_count_month"]
    return TenantInfo(
        tenant_id=tenant["id"],
        api_key_prefix=tenant["api_key_prefix"],
        tier=tenant["tier"],
        email=tenant["email"],
        created_at=tenant["created_at"],
        event_count_month=used,
        event_limit_month=limit,
        quota_remaining=max(0, limit - used),
    )


@router.get("", include_in_schema=False)
async def list_tenants_admin() -> Dict[str, Any]:
    """Admin: list all tenants (no auth for now — add IP restriction before launch)."""
    tenants = _get_store().list_tenants()
    return {"count": len(tenants), "tenants": tenants}
