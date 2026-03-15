#!/usr/bin/env python3
"""
BillingWatch Demo Event Script
Sends sample Stripe webhook events to a local BillingWatch instance
to trigger all 10 detectors without needing real Stripe data.

Usage:
    python3 scripts/demo_events.py
    python3 scripts/demo_events.py --host http://localhost:8000
    python3 scripts/demo_events.py --scenario charge_failures

Created: 2026-03-10
"""
import argparse
import json
import time
import uuid
from datetime import datetime, timezone

import urllib.request
import urllib.error


DEFAULT_HOST = "http://localhost:8000"
WEBHOOK_ENDPOINT = "/webhooks/stripe"


def ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def send_event(host: str, event: dict, label: str) -> dict:
    """POST a single event to the webhook endpoint."""
    url = f"{host}{WEBHOOK_ENDPOINT}"
    payload = json.dumps(event).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "Stripe-Signature": "demo"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read().decode())
            status = resp.status
    except urllib.error.HTTPError as e:
        body = {"error": e.read().decode()}
        status = e.code
    except Exception as e:
        body = {"error": str(e)}
        status = 0
    print(f"  [{status}] {label}")
    return body


def make_charge_failed(customer_id: str = None, amount: int = 2999) -> dict:
    return {
        "id": f"evt_{uuid.uuid4().hex[:16]}",
        "type": "charge.failed",
        "created": ts(),
        "data": {
            "object": {
                "id": f"ch_{uuid.uuid4().hex[:16]}",
                "object": "charge",
                "amount": amount,
                "currency": "usd",
                "customer": customer_id or f"cus_{uuid.uuid4().hex[:10]}",
                "failure_code": "card_declined",
                "failure_message": "Your card was declined.",
                "status": "failed",
            }
        },
    }


def make_subscription_deleted(customer_id: str = None) -> dict:
    return {
        "id": f"evt_{uuid.uuid4().hex[:16]}",
        "type": "customer.subscription.deleted",
        "created": ts(),
        "data": {
            "object": {
                "id": f"sub_{uuid.uuid4().hex[:16]}",
                "object": "subscription",
                "customer": customer_id or f"cus_{uuid.uuid4().hex[:10]}",
                "status": "canceled",
                "items": {"data": [{"price": {"unit_amount": 4900, "currency": "usd"}}]},
            }
        },
    }


def make_invoice_payment_failed(customer_id: str = None) -> dict:
    return {
        "id": f"evt_{uuid.uuid4().hex[:16]}",
        "type": "invoice.payment_failed",
        "created": ts(),
        "data": {
            "object": {
                "id": f"in_{uuid.uuid4().hex[:16]}",
                "object": "invoice",
                "customer": customer_id or f"cus_{uuid.uuid4().hex[:10]}",
                "amount_due": 4900,
                "currency": "usd",
                "attempt_count": 3,
                "subscription": f"sub_{uuid.uuid4().hex[:12]}",
            }
        },
    }


def make_payment_intent_succeeded(amount: int = 9900, currency: str = "usd") -> dict:
    return {
        "id": f"evt_{uuid.uuid4().hex[:16]}",
        "type": "payment_intent.succeeded",
        "created": ts(),
        "data": {
            "object": {
                "id": f"pi_{uuid.uuid4().hex[:16]}",
                "object": "payment_intent",
                "amount": amount,
                "currency": currency,
                "status": "succeeded",
                "customer": f"cus_{uuid.uuid4().hex[:10]}",
            }
        },
    }


def make_refund_created(amount: int = 4900, reason: str = "requested_by_customer") -> dict:
    return {
        "id": f"evt_{uuid.uuid4().hex[:16]}",
        "type": "charge.refunded",
        "created": ts(),
        "data": {
            "object": {
                "id": f"ch_{uuid.uuid4().hex[:16]}",
                "object": "charge",
                "amount": 4900,
                "amount_refunded": amount,
                "currency": "usd",
                "customer": f"cus_{uuid.uuid4().hex[:10]}",
                "refunds": {
                    "data": [{"reason": reason, "amount": amount}]
                },
            }
        },
    }


def make_dispute_created(amount: int = 4900) -> dict:
    return {
        "id": f"evt_{uuid.uuid4().hex[:16]}",
        "type": "charge.dispute.created",
        "created": ts(),
        "data": {
            "object": {
                "id": f"dp_{uuid.uuid4().hex[:16]}",
                "object": "dispute",
                "amount": amount,
                "currency": "usd",
                "reason": "fraudulent",
                "status": "warning_needs_response",
            }
        },
    }


SCENARIOS = {
    "charge_failures": {
        "description": "Charge failure spike — 12 rapid failures to trigger ChargeFailureDetector",
        "fn": lambda host: [
            send_event(host, make_charge_failed(), f"charge.failed #{i+1}") or time.sleep(0.05)
            for i in range(12)
        ],
    },
    "silent_lapse": {
        "description": "Silent subscription lapse — invoice fails, subscription cancels (customer stays 'active')",
        "fn": lambda host: [
            send_event(host, make_invoice_payment_failed("cus_demo001"), "invoice.payment_failed"),
            time.sleep(0.1),
            send_event(host, make_subscription_deleted("cus_demo001"), "customer.subscription.deleted"),
        ],
    },
    "refund_spike": {
        "description": "Refund spike — 8 refunds in rapid succession",
        "fn": lambda host: [
            send_event(host, make_refund_created(), f"charge.refunded #{i+1}") or time.sleep(0.05)
            for i in range(8)
        ],
    },
    "fraud_spike": {
        "description": "Fraud / card testing spike — 15 disputes in quick succession",
        "fn": lambda host: [
            send_event(host, make_dispute_created(), f"dispute #{i+1}") or time.sleep(0.03)
            for i in range(15)
        ],
    },
    "revenue_drop": {
        "description": "Revenue drop — simulate low-value payments vs historical baseline",
        "fn": lambda host: [
            send_event(host, make_payment_intent_succeeded(100), f"low-value payment #{i+1}") or time.sleep(0.05)
            for i in range(5)
        ],
    },
    "all": {
        "description": "Run all demo scenarios sequentially",
        "fn": lambda host: None,  # handled separately
    },
}


def run_all(host: str):
    for name, scenario in SCENARIOS.items():
        if name == "all":
            continue
        print(f"\n▶ {name}: {scenario['description']}")
        scenario["fn"](host)
        time.sleep(0.5)


def main():
    parser = argparse.ArgumentParser(
        description="BillingWatch demo event sender — triggers detectors without real Stripe"
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"BillingWatch host (default: {DEFAULT_HOST})")
    parser.add_argument("--scenario", default="all", choices=list(SCENARIOS.keys()),
                        help="Scenario to run (default: all)")
    args = parser.parse_args()

    print(f"🔔 BillingWatch Demo Events → {args.host}")
    print(f"   Scenario: {args.scenario}\n")

    # Health check
    try:
        with urllib.request.urlopen(f"{args.host}/health", timeout=3) as r:
            health = json.loads(r.read())
            print(f"✅ Server healthy: {health.get('service', 'ok')}\n")
    except Exception as e:
        print(f"❌ Cannot reach {args.host}/health: {e}")
        print("   Is BillingWatch running? Try: python3 -m uvicorn src.api.main:create_app --factory --port 8000")
        return 1

    if args.scenario == "all":
        run_all(args.host)
    else:
        scenario = SCENARIOS[args.scenario]
        print(f"▶ {args.scenario}: {scenario['description']}")
        scenario["fn"](args.host)

    print("\n✅ Done. Check /metrics/detectors for results:")
    print(f"   curl {args.host}/metrics/detectors | python3 -m json.tool")
    return 0


if __name__ == "__main__":
    exit(main())
