"""Metrics API — live event stats from EventStore (SQLite) + per-detector alert counts."""
import time as _time
from collections import Counter
from typing import Any, Dict, Optional

from fastapi import APIRouter, Query

from ...storage.event_store import EventStore
from ...storage.false_positives import FalsePositiveStore

router = APIRouter(prefix="/metrics", tags=["metrics"])

_store = EventStore()
_fp_store = FalsePositiveStore()
_METRICS_START = _time.time()  # module-load uptime tracking

# Known detectors — used for zero-filling absent counters
_ALL_DETECTORS = [
    "charge_failure_spike",
    "duplicate_charge",
    "fraud_spike",
    "negative_invoice",
    "revenue_drop",
    "silent_lapse",
    "webhook_lag",
    "currency_mismatch",
    "timezone_billing_error",
    "plan_downgrade_data_loss",
]


def _detector_stats(alert_log: list, window_hours: Optional[float] = None) -> Dict[str, Any]:
    """
    Compute per-detector hit counts and severity breakdown from the alert log.

    Args:
        alert_log: The shared _alert_log list from the webhooks module.
        window_hours: If provided, only count alerts from the last N hours.

    Returns:
        Dict with per-detector counts and severity breakdown.
    """
    import time as _time

    cutoff = None
    if window_hours is not None:
        cutoff = _time.time() - window_hours * 3600

    hits: Counter = Counter()
    by_severity: Dict[str, Counter] = {}

    for alert in alert_log:
        # Optionally filter by time window using triggered_at ISO string
        if cutoff is not None:
            ts_str = alert.get("triggered_at", "")
            if ts_str:
                try:
                    from datetime import datetime, timezone
                    ts = datetime.fromisoformat(ts_str)
                    # Treat naive datetimes as UTC
                    if ts.tzinfo is None:
                        ts_epoch = ts.timestamp()
                    else:
                        ts_epoch = ts.timestamp()
                    if ts_epoch < cutoff:
                        continue
                except (ValueError, AttributeError):
                    pass  # unparseable timestamp — include it

        detector = alert.get("detector", "unknown")
        severity = alert.get("severity", "unknown")

        hits[detector] += 1
        if detector not in by_severity:
            by_severity[detector] = Counter()
        by_severity[detector][severity] += 1

    # Build output — zero-fill known detectors
    result = {}
    all_detectors = set(_ALL_DETECTORS) | set(hits.keys())
    for det in sorted(all_detectors):
        sev = by_severity.get(det, Counter())
        result[det] = {
            "total_alerts": hits.get(det, 0),
            "by_severity": {
                "critical": sev.get("critical", 0),
                "high": sev.get("high", 0),
                "medium": sev.get("medium", 0),
                "low": sev.get("low", 0),
            },
        }
    return result


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

    events_by_type = _store.get_counts_by_type(window_sec)

    return {
        "window_hours": window_hours,
        "total_events": all_events,
        "events_by_type": events_by_type,
        "uptime_seconds": int(_time.time() - _METRICS_START),
        "detector_count": len(_ALL_DETECTORS),
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


@router.get("/detectors")
async def detector_metrics(window_hours: float = Query(default=24.0, ge=0.1, le=720.0)):
    """
    Per-detector alert hit counts and severity breakdown.

    Reads from the shared in-memory alert log.
    Default window: last 24 hours.

    Returns:
        - detectors: per-detector total_alerts + by_severity breakdown
        - alert_log_total: total alerts in the in-memory log (all time)
        - window_hours: the requested window
        - note: false_positive_rate is manual (mark via PATCH /anomalies/{id}/false-positive in v2)
    """
    try:
        from .webhooks import _alert_log
        stats = _detector_stats(_alert_log, window_hours=window_hours)
        log_total = len(_alert_log)
    except ImportError:
        stats = {det: {"total_alerts": 0, "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0}} for det in _ALL_DETECTORS}
        log_total = 0

    # False positive rates from DB
    fp_counts = _fp_store.get_fp_count_by_detector()
    fp_rates = {}
    for det in sorted(set(_ALL_DETECTORS) | set(fp_counts.keys())):
        total = stats.get(det, {}).get("total_alerts", 0)
        fps = fp_counts.get(det, 0)
        rate = (fps / total) if total > 0 else 0.0
        fp_rates[det] = {"false_positives": fps, "rate": round(rate, 4), "rate_pct": f"{rate:.1%}"}

    # Summary counts
    total_alerts = sum(d["total_alerts"] for d in stats.values())
    total_critical = sum(d["by_severity"]["critical"] for d in stats.values())
    total_high = sum(d["by_severity"]["high"] for d in stats.values())

    return {
        "window_hours": window_hours,
        "alert_log_total": log_total,
        "summary": {
            "total_alerts_in_window": total_alerts,
            "critical": total_critical,
            "high": total_high,
            "medium": sum(d["by_severity"]["medium"] for d in stats.values()),
            "low": sum(d["by_severity"]["low"] for d in stats.values()),
        },
        "detectors": stats,
        "false_positive_rates": fp_rates,
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
