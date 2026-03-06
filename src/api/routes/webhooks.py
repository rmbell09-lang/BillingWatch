"""Stripe webhook ingestion endpoint.

Verifies Stripe-Signature header, parses the event, and routes it
to the appropriate detector(s).
"""
import json
import os
import time
from typing import Any, Dict, List

import stripe
from fastapi import APIRouter, Header, HTTPException, Request, status

from ...detectors.charge_failure import ChargeFailureDetector

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Global detector instances (in-process state; swap for Redis-backed in v2)
_detectors = {
    "charge_failure": ChargeFailureDetector(),
}

# In-memory alert log (last 500 alerts); replace with DB in v2
_alert_log: List[Dict[str, Any]] = []


def _get_webhook_secret() -> str:
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if not secret:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET env var is not set")
    return secret


@router.post("/stripe", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
):
    """
    Receive and process Stripe webhook events.

    - Verifies the Stripe-Signature header
    - Deserializes the event payload
    - Routes to registered detectors
    - Returns 200 immediately (Stripe requires fast ACK)
    """
    payload = await request.body()

    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe-Signature header",
        )

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=_get_webhook_secret(),
        )
    except stripe.error.SignatureVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook signature verification failed: {exc}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payload: {exc}",
        )

    event_dict = dict(event)
    alerts = []

    # Route event to every detector; collect alerts
    for detector in _detectors.values():
        try:
            fired = detector.process_event(event_dict)
            alerts.extend(fired)
        except Exception as exc:
            # Don't let a bad detector kill the webhook response
            print(f"[webhooks] Detector {detector.name} raised: {exc}")

    # Store alerts
    for alert in alerts:
        entry = alert.to_dict()
        entry["stripe_event_id"] = event_dict.get("id")
        _alert_log.append(entry)
        # Trim to last 500
        if len(_alert_log) > 500:
            _alert_log.pop(0)

    return {
        "received": True,
        "event_type": event_dict.get("type"),
        "alerts_fired": len(alerts),
    }


@router.get("/alerts", tags=["alerts"])
async def list_alerts(limit: int = 50):
    """Return the most recent alerts (newest first)."""
    return {"alerts": list(reversed(_alert_log[-limit:]))}
