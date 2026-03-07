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
from ...detectors.duplicate_charge import DuplicateChargeDetector
from ...detectors.fraud_spike import FraudSpikeDetector
from ...detectors.negative_invoice import NegativeInvoiceDetector
from ...detectors.revenue_drop import RevenueDropDetector
from ...detectors.silent_lapse import SilentLapseDetector
from ...detectors.webhook_lag import WebhookLagDetector
from ...storage.event_store import EventStore
from ...alerting.webhook import AlertDispatcher

# Persistent SQLite event store
_event_store = EventStore()

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# All detectors registered — single source of truth
_detectors = {
    "charge_failure": ChargeFailureDetector(),
    "duplicate_charge": DuplicateChargeDetector(),
    "fraud_spike": FraudSpikeDetector(),
    "negative_invoice": NegativeInvoiceDetector(),
    "revenue_drop": RevenueDropDetector(),
    "silent_lapse": SilentLapseDetector(),
    "webhook_lag": WebhookLagDetector(),
}

# In-memory alert log (last 500 alerts); replace with DB in v2
_alert_log: List[Dict[str, Any]] = []

# Alert dispatcher — reads ALERT_EMAIL_* and ALERT_WEBHOOK_URL from env at first use
_dispatcher = AlertDispatcher()


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

    - Verifies the Stripe-Signature header (skip in dev/test mode if secret is 'dev')
    - Deserializes the event payload
    - Routes to all registered detectors
    - Returns 200 immediately (Stripe requires fast ACK)
    """
    payload = await request.body()

    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe-Signature header",
        )

    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    # Dev mode: bypass signature check when secret is 'dev' or unset
    if webhook_secret and webhook_secret != "dev":
        try:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=stripe_signature,
                secret=webhook_secret,
            )
            event_dict = dict(event)
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
    else:
        # Dev/test mode — parse raw JSON directly
        try:
            event_dict = json.loads(payload)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON payload: {exc}",
            )

    alerts = []

    # Persist event to SQLite
    _event_store.insert_event(event_dict)

    # Route event to every detector; collect alerts
    for name, detector in _detectors.items():
        try:
            fired = detector.process_event(event_dict)
            alerts.extend(fired)
        except Exception as exc:
            # Don't let a bad detector kill the webhook response
            print(f"[webhooks] Detector {name} raised: {exc}")

    # Store alerts
    for alert in alerts:
        entry = alert.to_dict()
        entry["stripe_event_id"] = event_dict.get("id")
        _alert_log.append(entry)
        # Trim to last 500
        if len(_alert_log) > 500:
            _alert_log.pop(0)
        # Dispatch to configured alert channels (email / webhook)
        try:
            _dispatcher.dispatch(alert)
        except Exception as exc:
            print(f"[webhooks] Alert dispatch failed for '{alert.title}': {exc}")

    # Mark event as processed in EventStore
    _event_store.mark_processed(event_dict.get("id", ""))

    return {
        "received": True,
        "event_type": event_dict.get("type"),
        "alerts_fired": len(alerts),
        "detectors_active": len(_detectors),
    }


@router.get("/alerts", tags=["alerts"])
async def list_alerts(limit: int = 50):
    """Return the most recent alerts (newest first)."""
    return {
        "alerts": list(reversed(_alert_log[-limit:])),
        "total": len(_alert_log),
    }


@router.get("/detectors", tags=["detectors"])
async def list_detectors():
    """List all registered detectors and their names."""
    return {
        "detectors": list(_detectors.keys()),
        "count": len(_detectors),
    }
