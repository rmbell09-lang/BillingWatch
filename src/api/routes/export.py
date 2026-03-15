"""CSV export endpoints for BillingWatch anomaly data."""
import csv
import io
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from ...storage.false_positives import FalsePositiveStore
from ..routes.webhooks import _alert_log

router = APIRouter(prefix="/export", tags=["export"])

_fp_store = FalsePositiveStore()

CSV_COLUMNS = [
    "alert_id",
    "detector",
    "severity",
    "title",
    "message",
    "triggered_at",
    "stripe_event_id",
    "false_positive",
]


@router.get("/anomalies")
async def export_anomalies_csv(
    limit: int = Query(default=500, ge=1, le=5000),
    hide_fp: bool = Query(default=False, description="Exclude false positives"),
    severity: Optional[str] = Query(default=None, description="Filter by severity (low|medium|high|critical)"),
    detector: Optional[str] = Query(default=None, description="Filter by detector name"),
):
    """
    Export anomaly alerts as a downloadable CSV file.

    Query params:
        limit: max rows (default 500, max 5000)
        hide_fp: exclude false positives (default false)
        severity: filter by severity level
        detector: filter by detector name

    Example:
        curl -o anomalies.csv http://localhost:8000/export/anomalies
        curl -o high.csv 'http://localhost:8000/export/anomalies?severity=high&hide_fp=true'
    """
    all_alerts = list(reversed(_alert_log[-5000:]))

    rows = []
    for a in all_alerts:
        aid = a.get("alert_id")
        is_fp = _fp_store.is_false_positive(aid) if aid is not None else False

        if hide_fp and is_fp:
            continue
        if severity and a.get("severity") != severity:
            continue
        if detector and a.get("detector") != detector:
            continue

        rows.append({
            "alert_id": aid,
            "detector": a.get("detector", ""),
            "severity": a.get("severity", ""),
            "title": a.get("title", ""),
            "message": a.get("message", ""),
            "triggered_at": a.get("triggered_at", ""),
            "stripe_event_id": a.get("stripe_event_id", ""),
            "false_positive": is_fp,
        })

        if len(rows) >= limit:
            break

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    writer.writerows(rows)

    output = buf.getvalue()
    buf.close()

    return StreamingResponse(
        iter([output]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=billingwatch-anomalies.csv",
            "X-Total-Rows": str(len(rows)),
        },
    )
