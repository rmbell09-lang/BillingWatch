"""Anomalies API — query alerts from in-memory store and EventStore stats."""
from fastapi import APIRouter, Query

from ...storage.event_store import EventStore
from ..routes.webhooks import _alert_log  # shared in-memory alert log

router = APIRouter(prefix="/anomalies", tags=["anomalies"])

_store = EventStore()


@router.get("/")
async def list_anomalies(limit: int = Query(default=50, ge=1, le=500)):
    """
    Return recent anomaly alerts (newest first).
    Sourced from the in-memory alert log populated by all detectors.
    """
    recent = list(reversed(_alert_log[-limit:]))
    return {
        "anomalies": recent,
        "total": len(_alert_log),
        "shown": len(recent),
    }


@router.get("/summary")
async def anomaly_summary():
    """High-level anomaly summary with event context."""
    window_sec = 3600  # last hour
    charge_failed = _store.get_event_count(window_sec, event_type="charge.failed")
    charge_total = _store.get_event_count(window_sec)
    failure_rate = (charge_failed / (charge_total or 1))

    high_alerts = [a for a in _alert_log if a.get("severity") == "high"]
    critical_alerts = [a for a in _alert_log if a.get("severity") == "critical"]

    return {
        "status": "alert" if (high_alerts or critical_alerts) else "ok",
        "alerts_total": len(_alert_log),
        "alerts_high": len(high_alerts),
        "alerts_critical": len(critical_alerts),
        "last_hour": {
            "charge_failed": charge_failed,
            "charge_total": charge_total,
            "failure_rate_pct": f"{failure_rate:.1%}",
        },
    }
