"""Anomalies API — query alerts from in-memory store, false positive marking."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ...storage.event_store import EventStore
from ...storage.false_positives import FalsePositiveStore
from ..routes.webhooks import _alert_log  # shared in-memory alert log

router = APIRouter(prefix="/anomalies", tags=["anomalies"])

_store = EventStore()
_fp_store = FalsePositiveStore()


class FalsePositiveBody(BaseModel):
    reason: Optional[str] = None


@router.get("/")
async def list_anomalies(
    limit: int = Query(default=50, ge=1, le=500),
    hide_fp: bool = Query(default=False, description="Exclude false positives from results"),
):
    """
    Return recent anomaly alerts (newest first).
    Sourced from the in-memory alert log populated by all detectors.
    Each entry includes a false_positive flag.
    """
    all_alerts = list(reversed(_alert_log[-500:]))
    result = []
    for a in all_alerts:
        entry = dict(a)
        aid = a.get("alert_id")
        entry["false_positive"] = _fp_store.is_false_positive(aid) if aid is not None else False
        if hide_fp and entry["false_positive"]:
            continue
        result.append(entry)

    result = result[:limit]
    return {
        "anomalies": result,
        "total": len(_alert_log),
        "shown": len(result),
    }


@router.patch("/{alert_id}/false-positive")
async def mark_false_positive(alert_id: int, body: FalsePositiveBody = FalsePositiveBody()):
    """
    Mark an alert as a false positive.

    Example:
        curl -X PATCH http://localhost:8000/anomalies/3/false-positive \\
             -H 'Content-Type: application/json' \\
             -d '{"reason": "scheduled maintenance window"}'

    After marking, false_positive_rate in /metrics/detectors updates automatically.
    """
    alert = next((a for a in _alert_log if a.get("alert_id") == alert_id), None)
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found in log")

    detector = alert.get("detector", "unknown")
    severity = alert.get("severity", "unknown")
    reason = body.reason or ""

    ok = _fp_store.mark_false_positive(
        alert_id=alert_id,
        detector=detector,
        severity=severity,
        reason=reason,
    )
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to save false positive")

    from datetime import datetime, timezone, date as _date
    import time
    return {
        "alert_id": alert_id,
        "detector": detector,
        "false_positive": True,
        "reason": reason or None,
        "message": "Alert marked as false positive. FP rate updated in /metrics/detectors.",
    }


@router.delete("/{alert_id}/false-positive")
async def unmark_false_positive(alert_id: int):
    """Remove false positive marking from an alert."""
    removed = _fp_store.unmark_false_positive(alert_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"No false positive record for alert {alert_id}")
    return {"alert_id": alert_id, "false_positive": False, "message": "False positive removed."}


@router.get("/summary")
async def anomaly_summary():
    """High-level anomaly summary with event context and FP stats."""
    window_sec = 3600  # last hour
    charge_failed = _store.get_event_count(window_sec, event_type="charge.failed")
    charge_total = _store.get_event_count(window_sec)
    failure_rate = (charge_failed / (charge_total or 1))

    high_alerts = [a for a in _alert_log if a.get("severity") == "high"]
    critical_alerts = [a for a in _alert_log if a.get("severity") == "critical"]

    fp_by_detector = _fp_store.get_fp_count_by_detector()
    total_fp = _fp_store.get_total_fp_count()

    return {
        "status": "alert" if (high_alerts or critical_alerts) else "ok",
        "alerts_total": len(_alert_log),
        "alerts_high": len(high_alerts),
        "alerts_critical": len(critical_alerts),
        "false_positives": {
            "total": total_fp,
            "by_detector": fp_by_detector,
        },
        "last_hour": {
            "charge_failed": charge_failed,
            "charge_total": charge_total,
            "failure_rate_pct": f"{failure_rate:.1%}",
        },
    }
