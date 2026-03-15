"""
BillingWatch /config/thresholds API.

GET  /config/thresholds        → return current thresholds (with defaults)
PATCH /config/thresholds       → update one or more thresholds, persist to SQLite,
                                  and reload live detectors immediately.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, model_validator

from ...storage.thresholds import ThresholdStore, DEFAULTS

router = APIRouter(prefix="/config", tags=["config"])

_store = ThresholdStore()


class ThresholdPatch(BaseModel):
    """All fields optional — only send the ones you want to change."""
    charge_failure_rate:    Optional[float] = None
    revenue_drop_pct:       Optional[float] = None
    webhook_lag_warning_s:  Optional[int]   = None
    webhook_lag_critical_s: Optional[int]   = None
    duplicate_threshold:    Optional[int]   = None
    dispute_rate_threshold: Optional[float] = None
    refund_rate_threshold:  Optional[float] = None
    large_refund_usd:       Optional[float] = None

    @model_validator(mode="before")
    @classmethod
    def reject_unknown_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        known = set(DEFAULTS.keys())
        unknown = set(values.keys()) - known
        if unknown:
            raise ValueError(f"Unknown threshold keys: {', '.join(sorted(unknown))}")
        return values


@router.get("/thresholds")
async def get_thresholds():
    """
    Return all current detector thresholds.

    Values reflect the last PATCH (persisted in SQLite), falling back to coded
    defaults for any key that has never been set.
    """
    return {
        "thresholds": _store.get(),
        "defaults":   DEFAULTS,
    }


@router.patch("/thresholds")
async def patch_thresholds(body: ThresholdPatch):
    """
    Update one or more detector thresholds at runtime.

    Changes are persisted to SQLite and take effect on the **next webhook event**
    processed — no restart required.

    Example body:
        { "charge_failure_rate": 0.20, "duplicate_threshold": 3 }
    """
    updates = {k: v for k, v in body.model_dump().items() if v is not None}

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update — send at least one threshold key.")

    try:
        new_thresholds = _store.patch(updates)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Signal the webhook module to reload detectors with the new thresholds
    try:
        from .webhooks import reload_detectors
        reload_detectors(new_thresholds)
        reloaded = True
    except Exception:
        reloaded = False

    return {
        "updated": list(updates.keys()),
        "thresholds": new_thresholds,
        "detectors_reloaded": reloaded,
    }
