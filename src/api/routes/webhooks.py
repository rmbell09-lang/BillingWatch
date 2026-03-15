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
from slowapi import Limiter
from slowapi.util import get_remote_address

from ...detectors.charge_failure import ChargeFailureDetector
from ...detectors.duplicate_charge import DuplicateChargeDetector
from ...detectors.fraud_spike import FraudSpikeDetector
from ...detectors.negative_invoice import NegativeInvoiceDetector
from ...detectors.revenue_drop import RevenueDropDetector
from ...detectors.silent_lapse import SilentLapseDetector
from ...detectors.webhook_lag import WebhookLagDetector
from ...storage.event_store import EventStore
from ...alerting.webhook import AlertDispatcherV2 as AlertDispatcher

# Persistent SQLite event store
_event_store = EventStore()

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
limiter = Limiter(key_func=get_remote_address)

from ...storage.thresholds import ThresholdStore as _ThresholdStore

_threshold_store = _ThresholdStore()


def _build_detectors(t: dict) -> dict:
    """Instantiate all detectors with the given threshold config."""
    return {
        "charge_failure": ChargeFailureDetector(config={
            "failure_threshold": t.get("charge_failure_rate", 0.15),
        }),
        "duplicate_charge": DuplicateChargeDetector(config={
            "duplicate_threshold": t.get("duplicate_threshold", 2),
        }),
        "fraud_spike": FraudSpikeDetector(config={
            "dispute_rate_threshold": t.get("dispute_rate_threshold", 0.01),
        }),
        "negative_invoice": NegativeInvoiceDetector(config={
            "refund_rate_threshold": t.get("refund_rate_threshold", 0.10),
            "large_refund_threshold_cents": int(t.get("large_refund_usd", 500.0) * 100),
        }),
        "revenue_drop": RevenueDropDetector(config={
            "drop_threshold": t.get("revenue_drop_pct", 0.15),
        }),
        "silent_lapse": SilentLapseDetector(),
        "webhook_lag": WebhookLagDetector(config={
            "warning_lag_seconds": t.get("webhook_lag_warning_s", 300),
            "critical_lag_seconds": t.get("webhook_lag_critical_s", 1800),
        }),
    }


# All detectors registered — single source of truth; initialized from persisted thresholds
_detectors = _build_detectors(_threshold_store.get())


def reload_detectors(thresholds: dict) -> None:
    """Re-initialize all detectors with updated thresholds (called by config route)."""
    global _detectors
    _detectors = _build_detectors(thresholds)

# In-memory alert log (last 500 alerts); replace with DB in v2
_alert_log: List[Dict[str, Any]] = []
_alert_id_counter: int = 0

# Alert dispatcher — reads ALERT_EMAIL_* and ALERT_WEBHOOK_URL from env at first use
_dispatcher = AlertDispatcher()


def _get_webhook_secret() -> str:
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if not secret:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET env var is not set")
    return secret


@router.post("/stripe", status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
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
        global _alert_id_counter
        _alert_id_counter += 1
        entry["alert_id"] = _alert_id_counter
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


# ---------------------------------------------------------------------------
# Wire demo seed routes onto the demo router (must happen after module load)
# ---------------------------------------------------------------------------
from . import demo as _demo_module
from .demo_seed import register_seed_routes as _register_seed_routes

_register_seed_routes(
    router=_demo_module.router,
    detectors=_detectors,
    alert_log=_alert_log,
    event_store=_event_store,
)
