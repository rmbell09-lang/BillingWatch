"""
FastAPI dependency: per-request tenant authentication.

Usage in route:
    from src.api.deps import get_current_tenant

    @router.get("/metrics")
    async def get_metrics(tenant = Depends(get_current_tenant)):
        ...

Public endpoints (no auth):
    GET  /health
    GET  /
    POST /webhook/{tenant_id}
    POST /tenants/register
"""

from typing import Any, Dict

from fastapi import Header, HTTPException, status

from src.storage.tenants import TenantStore

# Shared store instance (lazy-init, reused across requests)
_store: TenantStore = None  # type: ignore


def _get_store() -> TenantStore:
    global _store
    if _store is None:
        _store = TenantStore()
    return _store


async def get_current_tenant(
    authorization: str = Header(..., description="Bearer bw_live_<key>")
) -> Dict[str, Any]:
    """
    Validate Bearer API key and return the tenant dict.
    Raises 401 on missing/invalid key.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected: Bearer bw_live_<key>",
        )
    raw_key = authorization.removeprefix("Bearer ").strip()
    if not raw_key.startswith("bw_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format. Keys begin with 'bw_live_'.",
        )
    tenant = _get_store().get_by_key(raw_key)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )
    return tenant
