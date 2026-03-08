"""
BillingWatch webhook_handler.py

Standalone utility for:
  1. Validating Stripe webhook signatures (or bypassing in dev mode)
  2. Parsing Stripe event payloads
  3. Routing events to all registered detectors
  4. Logging results

This is the core processing unit. The FastAPI route at
src/api/routes/webhooks.py delegates to this module.

Usage (dev testing without Stripe CLI):
    python3 webhook_handler.py --test charge.failed
    python3 webhook_handler.py --test charge.succeeded --count 20
"""

import json
import os
import sys
import time
import hmac
import hashlib
import argparse
from typing import Any, Dict, List, Optional

try:
    from src.storage.event_store import EventStore as _EventStore
    _STORE_AVAILABLE = True
except ImportError:
    _STORE_AVAILABLE = False

# Module-level singleton EventStore (lazy-init)
_store: Any = None

def get_event_store() -> Any:
    """Return the module-level EventStore, initialising it on first call."""
    global _store
    if _store is None and _STORE_AVAILABLE:
        _store = _EventStore()
    return _store

# ---------------------------------------------------------------------------
# Signature validation
# ---------------------------------------------------------------------------

def validate_stripe_signature(
    payload: bytes,
    sig_header: str,
    secret: str,
    tolerance: int = 300,
) -> Dict[str, Any]:
    """
    Validate a Stripe-Signature header.

    Returns the parsed event dict on success.
    Raises ValueError on failure.

    In dev mode (secret == 'dev' or empty), skips validation and parses JSON directly.
    """
    if not secret or secret == "dev":
        # Dev mode — no signature check
        return json.loads(payload)

    # Parse the Stripe-Signature header
    # Format: t=<timestamp>,v1=<signature>[,v1=<sig2>...]
    parts: Dict[str, List[str]] = {}
    for item in sig_header.split(","):
        k, _, v = item.partition("=")
        parts.setdefault(k.strip(), []).append(v.strip())

    timestamp_strs = parts.get("t", [])
    signatures = parts.get("v1", [])

    if not timestamp_strs or not signatures:
        raise ValueError("Malformed Stripe-Signature header")

    timestamp = int(timestamp_strs[0])

    # Replay attack protection
    now = int(time.time())
    if abs(now - timestamp) > tolerance:
        raise ValueError(
            f"Webhook timestamp out of tolerance: {abs(now - timestamp)}s > {tolerance}s"
        )

    # Compute expected HMAC
    signed_payload = f"{timestamp}.".encode() + payload
    expected = hmac.new(
        secret.encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()

    # Constant-time comparison against all provided v1 signatures
    if not any(hmac.compare_digest(expected, sig) for sig in signatures):
        raise ValueError("Stripe signature verification failed")

    return json.loads(payload)


# ---------------------------------------------------------------------------
# Event logging
# ---------------------------------------------------------------------------

_event_log: List[Dict[str, Any]] = []


def log_event(event: Dict[str, Any], alerts: List[Any]) -> None:
    """Append a processed event + its alerts to the in-memory log."""
    entry = {
        "received_at": time.time(),
        "event_id": event.get("id", "unknown"),
        "event_type": event.get("type", "unknown"),
        "alerts": [a.to_dict() for a in alerts],
    }
    _event_log.append(entry)
    # Keep last 1000
    if len(_event_log) > 1000:
        _event_log.pop(0)
    print(
        f"[webhook_handler] {entry['event_type']} received — "
        f"{len(alerts)} alert(s) fired"
    )
    for alert in alerts:
        print(f"  🚨 [{alert.severity.upper()}] {alert.title}: {alert.message}")


def get_event_log() -> List[Dict[str, Any]]:
    return list(_event_log)


# ---------------------------------------------------------------------------
# Event processor
# ---------------------------------------------------------------------------

# Import detectors (relative import — run from project root with -m)
try:
    from src.detectors.charge_failure import ChargeFailureDetector
    from src.detectors.duplicate_charge import DuplicateChargeDetector
    from src.detectors.fraud_spike import FraudSpikeDetector
    from src.detectors.negative_invoice import NegativeInvoiceDetector
    from src.detectors.revenue_drop import RevenueDropDetector
    from src.detectors.silent_lapse import SilentLapseDetector
    from src.detectors.webhook_lag import WebhookLagDetector
    _DETECTORS_AVAILABLE = True
except ImportError:
    _DETECTORS_AVAILABLE = False

_detector_registry: Optional[Dict[str, Any]] = None


def _get_detectors() -> Dict[str, Any]:
    global _detector_registry
    if _detector_registry is None:
        if not _DETECTORS_AVAILABLE:
            raise RuntimeError("Detectors not importable — run from BillingWatch project root")
        _detector_registry = {
            "charge_failure": ChargeFailureDetector(),
            "duplicate_charge": DuplicateChargeDetector(),
            "fraud_spike": FraudSpikeDetector(),
            "negative_invoice": NegativeInvoiceDetector(),
            "revenue_drop": RevenueDropDetector(),
            "silent_lapse": SilentLapseDetector(),
            "webhook_lag": WebhookLagDetector(),
        }
    return _detector_registry


def process_webhook(
    payload: bytes,
    sig_header: str,
    webhook_secret: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Full webhook processing pipeline:
      1. Validate signature
      2. Parse event
      3. Route to detectors
      4. Log event
      5. Return result dict
    """
    secret = webhook_secret or os.getenv("STRIPE_WEBHOOK_SECRET", "dev")

    try:
        event = validate_stripe_signature(payload, sig_header, secret)
    except ValueError as exc:
        print(f"[webhook_handler] Signature validation failed: {exc}")
        return {"ok": False, "error": str(exc)}

    # Persist to EventStore for durability and processor replay
    _es = get_event_store()
    if _es is not None:
        try:
            _es.insert_event(event)
        except Exception as _es_exc:
            print(f"[webhook_handler] EventStore insert warning: {_es_exc}")

    detectors = _get_detectors()
    all_alerts = []
    for name, detector in detectors.items():
        try:
            fired = detector.process_event(event)
            all_alerts.extend(fired)
        except Exception as exc:
            print(f"[webhook_handler] Detector {name} error: {exc}")

    log_event(event, all_alerts)

    return {
        "ok": True,
        "event_id": event.get("id"),
        "event_type": event.get("type"),
        "alerts_fired": len(all_alerts),
        "detectors_checked": len(detectors),
    }


# ---------------------------------------------------------------------------
# CLI test harness
# ---------------------------------------------------------------------------

_TEST_EVENTS = {
    "charge.failed": {
        "id": "evt_test_{n}",
        "type": "charge.failed",
        "data": {
            "object": {
                "id": "ch_test_{n}",
                "amount": 2000,
                "currency": "usd",
                "failure_code": "card_declined",
                "failure_message": "Your card was declined.",
            }
        },
    },
    "charge.succeeded": {
        "id": "evt_test_{n}",
        "type": "charge.succeeded",
        "data": {
            "object": {
                "id": "ch_test_{n}",
                "amount": 2000,
                "currency": "usd",
            }
        },
    },
    "invoice.payment_failed": {
        "id": "evt_test_{n}",
        "type": "invoice.payment_failed",
        "data": {
            "object": {
                "id": "in_test_{n}",
                "amount_due": 5000,
                "currency": "usd",
                "customer": "cus_test",
            }
        },
    },
}


def _make_event(event_type: str, n: int) -> bytes:
    template = _TEST_EVENTS.get(event_type)
    if not template:
        print(f"Unknown test event type: {event_type}")
        print(f"Available: {list(_TEST_EVENTS.keys())}")
        sys.exit(1)
    raw = json.dumps(template).replace("{n}", str(n))
    return raw.encode()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BillingWatch webhook handler test CLI")
    parser.add_argument("--test", metavar="EVENT_TYPE", help="Stripe event type to simulate")
    parser.add_argument("--count", type=int, default=1, help="Number of events to send (default 1)")
    parser.add_argument("--secret", default="dev", help="Webhook secret (default: dev = no validation)")
    args = parser.parse_args()

    if not args.test:
        parser.print_help()
        sys.exit(0)

    print(f"[test] Simulating {args.count}x {args.test} event(s) in dev mode...")
    for i in range(1, args.count + 1):
        payload = _make_event(args.test, i)
        result = process_webhook(payload, "test-sig", args.secret)
        print(f"  [{i}/{args.count}] {result}")

    print(f"\n[test] Event log ({len(_event_log)} entries):")
    for entry in _event_log:
        print(f"  {entry['event_type']} — {len(entry['alerts'])} alert(s)")
