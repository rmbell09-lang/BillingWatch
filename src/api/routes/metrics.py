"""Metrics API — live event stats from EventStore (SQLite)."""
from fastapi import APIRouter, Query

from ...storage.event_store import EventStore

router = APIRouter(prefix="/metrics", tags=["metrics"])

_store = EventStore()


@router.get("/")
async def get_metrics(window_hours: float = Query(default=1.0, ge=0.1, le=168.0)):
    """
    Live event metrics from EventStore.

    Returns event counts for the requested rolling window.
    Default: last 1 hour.
    """
    window_sec = window_hours * 3600

    charge_failed = _store.get_event_count(window_sec, event_type="charge.failed")
    charge_succeeded = _store.get_event_count(window_sec, event_type="charge.succeeded")
    total_charges = charge_failed + charge_succeeded
    failure_rate = (charge_failed / total_charges) if total_charges else 0.0

    all_events = _store.get_event_count(window_sec)

    return {
        "window_hours": window_hours,
        "total_events": all_events,
        "charges": {
            "succeeded": charge_succeeded,
            "failed": charge_failed,
            "total": total_charges,
            "failure_rate": round(failure_rate, 4),
            "failure_rate_pct": f"{failure_rate:.1%}",
        },
        "all_time_total": _store.total_count(),
        "status": "live" if all_events > 0 else "no_data",
    }


@router.get("/recent-events")
async def recent_events(limit: int = Query(default=20, ge=1, le=200)):
    """Return the most recent webhook events (newest first)."""
    events = _store.get_recent(limit)
    return {
        "events": [
            {
                "id": e.get("id"),
                "type": e.get("type"),
                "object_id": e.get("data", {}).get("object", {}).get("id"),
                "amount": e.get("data", {}).get("object", {}).get("amount"),
                "currency": e.get("data", {}).get("object", {}).get("currency"),
            }
            for e in events
        ],
        "count": len(events),
    }
