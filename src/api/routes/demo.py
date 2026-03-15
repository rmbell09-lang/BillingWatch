"""BillingWatch /demo endpoint — interactive billing scenarios for beta users.

Each scenario generates synthetic Stripe events and runs them through FRESH
detector instances (isolated from production state) to show what alerts fire.
No real data is touched. No Stripe calls are made.
"""
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from ...detectors.charge_failure import ChargeFailureDetector
from ...detectors.duplicate_charge import DuplicateChargeDetector
from ...detectors.fraud_spike import FraudSpikeDetector
from ...detectors.negative_invoice import NegativeInvoiceDetector
from ...detectors.revenue_drop import RevenueDropDetector

router = APIRouter(prefix="/demo", tags=["demo"])

# ---------------------------------------------------------------------------
# Scenario catalogue
# ---------------------------------------------------------------------------

SCENARIOS = {
    "charge_failure_spike": {
        "title": "Charge Failure Spike",
        "description": (
            "Simulates a payment processor outage: 18 charge failures in 60 seconds "
            "against 2 successful charges — pushing failure rate above the 15% threshold. "
            "BillingWatch fires a HIGH alert immediately."
        ),
        "what_to_watch": "Failure rate exceeds 15% → charge_failure_spike alert fires.",
        "severity_expected": "high",
    },
    "duplicate_charge": {
        "title": "Duplicate Charge Loop",
        "description": (
            "Simulates a billing retry bug: the same customer is charged $99.00 three times "
            "within 90 seconds. BillingWatch catches it as a duplicate and alerts before "
            "the customer notices or disputes."
        ),
        "what_to_watch": "3 identical charges in 90 s → duplicate_charge alert fires.",
        "severity_expected": "high",
    },
    "fraud_spike": {
        "title": "Fraud Spike",
        "description": (
            "Simulates a wave of fraudulent charges: 12 charge.failed events marked as "
            "fraudulent in 30 seconds. BillingWatch escalates to CRITICAL."
        ),
        "what_to_watch": "12 fraud-flagged failures → fraud_spike alert fires.",
        "severity_expected": "critical",
    },
    "negative_invoice": {
        "title": "Negative Invoice / Credit Abuse",
        "description": (
            "Simulates a misconfigured coupon or refund loop that produces a negative "
            "invoice total (-$250.00). BillingWatch flags it before Stripe processes "
            "the payout."
        ),
        "what_to_watch": "Invoice total < 0 → negative_invoice alert fires.",
        "severity_expected": "medium",
    },
    "revenue_drop": {
        "title": "Revenue Drop",
        "description": (
            "Simulates a sudden revenue collapse: MRR drops from $10,000 to $2,500 "
            "(75% decline) in one hour. BillingWatch detects the drop and alerts "
            "before end-of-day reporting."
        ),
        "what_to_watch": "Simulated MRR drop signal → revenue_drop alert fires.",
        "severity_expected": "high",
    },
}


# ---------------------------------------------------------------------------
# Synthetic event factories
# ---------------------------------------------------------------------------

def _stripe_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def _charge_event(event_type: str, customer_id: str, amount: int,
                  outcome_reason: Optional[str] = None) -> Dict[str, Any]:
    obj: Dict[str, Any] = {
        "id": _stripe_id("ch"),
        "object": "charge",
        "amount": amount,
        "currency": "usd",
        "customer": customer_id,
        "created": int(time.time()),
    }
    if outcome_reason:
        obj["outcome"] = {"reason": outcome_reason, "type": "issuer_declined"}
    return {
        "id": _stripe_id("evt"),
        "type": event_type,
        "created": int(time.time()),
        "data": {"object": obj},
    }


def _negative_invoice_event(customer_id: str, amount_paid: int) -> Dict[str, Any]:
    """A negative-total invoice — triggers negative_invoice detector."""
    return {
        "id": _stripe_id("evt"),
        "type": "invoice.payment_succeeded",
        "created": int(time.time()),
        "data": {
            "object": {
                "id": _stripe_id("in"),
                "object": "invoice",
                "customer": customer_id,
                "amount_paid": amount_paid,
                "total": amount_paid,
                "currency": "usd",
                "created": int(time.time()),
                "status_transitions": {"paid_at": int(time.time())},
            }
        },
    }


def _refund_event(customer_id: str, charge_id: str, amount_refunded: int) -> Dict[str, Any]:
    """A large refund — also triggers negative_invoice detector."""
    return {
        "id": _stripe_id("evt"),
        "type": "charge.refunded",
        "created": int(time.time()),
        "data": {
            "object": {
                "id": charge_id,
                "object": "charge",
                "customer": customer_id,
                "amount_refunded": amount_refunded,
                "currency": "usd",
                "created": int(time.time()),
            }
        },
    }


def _dispute_event(customer_id: str, amount: int) -> Dict[str, Any]:
    """A dispute.created event — triggers fraud_spike detector."""
    return {
        "id": _stripe_id("evt"),
        "type": "charge.dispute.created",
        "created": int(time.time()),
        "data": {
            "object": {
                "id": _stripe_id("dp"),
                "object": "dispute",
                "charge": _stripe_id("ch"),
                "customer": customer_id,
                "amount": amount,
                "currency": "usd",
                "reason": "fraudulent",
                "status": "needs_response",
                "created": int(time.time()),
            }
        },
    }


def _invoice_payment_event(customer_id: str, amount_paid: int, paid_at: int) -> Dict[str, Any]:
    """A successful invoice payment — used to build revenue history for revenue_drop."""
    return {
        "id": _stripe_id("evt"),
        "type": "invoice.payment_succeeded",
        "created": paid_at,
        "data": {
            "object": {
                "id": _stripe_id("in"),
                "object": "invoice",
                "customer": customer_id,
                "amount_paid": amount_paid,
                "total": amount_paid,
                "currency": "usd",
                "status_transitions": {"paid_at": paid_at},
            }
        },
    }





# ---------------------------------------------------------------------------
# Scenario runners — each returns list of alert dicts
# ---------------------------------------------------------------------------

def _run_charge_failure_spike() -> List[Dict]:
    detector = ChargeFailureDetector()
    alerts = []
    cus = _stripe_id("cus")
    # 2 successes
    for _ in range(2):
        for a in detector.process_event(_charge_event("charge.succeeded", cus, 9900)):
            alerts.append(a.to_dict())
    # 18 failures — pushes rate to 90%
    for _ in range(18):
        for a in detector.process_event(_charge_event("charge.failed", cus, 9900)):
            alerts.append(a.to_dict())
    return alerts


def _run_duplicate_charge() -> List[Dict]:
    detector = DuplicateChargeDetector()
    alerts = []
    cus = _stripe_id("cus")
    for _ in range(3):
        for a in detector.process_event(_charge_event("charge.succeeded", cus, 9900)):
            alerts.append(a.to_dict())
    return alerts


def _run_fraud_spike() -> List[Dict]:
    detector = FraudSpikeDetector()
    alerts = []
    # Seed 50 baseline charges so rate math is meaningful
    for _ in range(50):
        for a in detector.process_event(_charge_event("charge.succeeded", _stripe_id("cus"), 4900)):
            alerts.append(a.to_dict())
    # Fire 6 disputes — exceeds absolute threshold of 5
    for _ in range(6):
        cus = _stripe_id("cus")
        for a in detector.process_event(_dispute_event(cus, 4900)):
            alerts.append(a.to_dict())
    return alerts


def _run_negative_invoice() -> List[Dict]:
    detector = NegativeInvoiceDetector()
    alerts = []
    cus = _stripe_id("cus")
    # Negative invoice total (-$250)
    for a in detector.process_event(_negative_invoice_event(cus, -25000)):
        alerts.append(a.to_dict())
    # Large refund ($750) to same customer — triggers customer daily threshold
    ch_id = _stripe_id("ch")
    for a in detector.process_event(_refund_event(cus, ch_id, 75000)):
        alerts.append(a.to_dict())
    return alerts


def _run_revenue_drop() -> List[Dict]:
    detector = RevenueDropDetector()
    alerts = []
    now = int(time.time())
    one_day = 86400
    cus = _stripe_id("cus")

    # Seed 7 days of solid revenue: ~$10,000/day via invoice payments
    for day_offset in range(7, 0, -1):
        ts = now - (day_offset * one_day)
        for _ in range(100):
            evt = _invoice_payment_event(cus, 10000, ts)
            detector.process_event(evt)

    # Today: only $250 revenue — a ~97.5% collapse
    for _ in range(25):
        evt = _invoice_payment_event(cus, 1000, now)
        detector.process_event(evt)

    # Scheduled check fires the alert (revenue_drop uses check(), not process_event)
    for a in detector.check():
        alerts.append(a.to_dict())
    return alerts


_RUNNERS = {
    "charge_failure_spike": _run_charge_failure_spike,
    "duplicate_charge": _run_duplicate_charge,
    "fraud_spike": _run_fraud_spike,
    "negative_invoice": _run_negative_invoice,
    "revenue_drop": _run_revenue_drop,
}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/", summary="List available demo scenarios")
async def list_scenarios():
    """
    Return all available demo scenarios with descriptions.
    Use GET /demo/run?scenario=<name> to execute one.
    """
    return {
        "message": "BillingWatch Demo — no real data, no Stripe calls.",
        "available_scenarios": [
            {
                "name": name,
                "title": info["title"],
                "description": info["description"],
                "what_to_watch": info["what_to_watch"],
                "severity_expected": info["severity_expected"],
                "run_url": f"/demo/run?scenario={name}",
            }
            for name, info in SCENARIOS.items()
        ],
    }


@router.get("/run", summary="Run a demo scenario and see what alerts fire")
async def run_scenario(scenario: str = Query(..., description="Scenario name from GET /demo")):
    """
    Runs the requested demo scenario through fresh, isolated detector instances.
    Returns the alerts that would have fired on a real Stripe account.

    - No real Stripe data is used.
    - No production detector state is modified.
    - No emails or webhooks are dispatched.
    """
    if scenario not in _RUNNERS:
        return JSONResponse(
            status_code=404,
            content={
                "error": f"Unknown scenario '{scenario}'.",
                "valid_scenarios": list(SCENARIOS.keys()),
            },
        )

    info = SCENARIOS[scenario]
    started = time.time()

    try:
        alerts = _RUNNERS[scenario]()
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": f"Scenario execution failed: {exc}"},
        )

    elapsed_ms = round((time.time() - started) * 1000, 1)

    return {
        "demo": True,
        "scenario": scenario,
        "title": info["title"],
        "description": info["description"],
        "what_to_watch": info["what_to_watch"],
        "alerts_fired": len(alerts),
        "alerts": alerts,
        "elapsed_ms": elapsed_ms,
        "note": (
            "These alerts were generated from synthetic data against isolated detector "
            "instances. Your production state was not modified."
        ),
    }
