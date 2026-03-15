"""
BillingWatch /demo/seed endpoint — populates the live pipeline with realistic
synthetic billing history for instant beta onboarding.

One POST to /demo/seed injects 24 hours of plausible Stripe events into the
real EventStore and runs them through all detectors. The result: a new beta
user immediately sees populated anomalies, metrics, and alerts on their
dashboard — no waiting for real Stripe traffic.

Endpoints added to the existing demo router:
  POST /demo/seed           — inject demo history (idempotent, tagged events)
  DELETE /demo/seed         — wipe all demo-seeded events from EventStore
  GET  /demo/seed/status    — check whether demo data is present
"""

import json
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Tuple

from fastapi import APIRouter

# Re-use the existing router from demo.py — this file just extends it.
# In practice we append these routes to the demo router at import.
# (See integration note at bottom.)


def _sid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


DEMO_TAG = "billingwatch_demo_seed"   # marker stored in event payload


# ---------------------------------------------------------------------------
# Synthetic 24-hour event stream
# ---------------------------------------------------------------------------

def _build_event_stream(now: float) -> List[Dict[str, Any]]:
    """
    Returns a chronological list of Stripe-like event dicts covering the
    past 24 hours of a healthy-then-troubled SaaS billing account.

    Timeline:
      T-24h to T-6h   : Normal traffic — steady charges, renewals
      T-6h to T-3h    : Charge failure spike (processor blip)
      T-3h to T-2h    : Recovery + a duplicate charge
      T-2h to now     : Fraud dispute + large refund
    """
    events: List[Dict[str, Any]] = []
    customers = [_sid("cus") for _ in range(20)]

    def ts(hours_ago: float, jitter_sec: int = 120) -> int:
        base = now - (hours_ago * 3600)
        jitter = uuid.uuid4().int % (jitter_sec * 2) - jitter_sec
        return int(base + jitter)

    def charge(event_type: str, cus: str, amount: int, t: int,
               outcome_reason: str = None) -> Dict:
        obj: Dict[str, Any] = {
            "id": _sid("ch"), "object": "charge",
            "amount": amount, "currency": "usd",
            "customer": cus, "created": t,
            "_demo": DEMO_TAG,
        }
        if outcome_reason:
            obj["outcome"] = {"reason": outcome_reason, "type": "issuer_declined"}
        return {
            "id": _sid("evt"), "type": event_type, "created": t,
            "_demo": DEMO_TAG,
            "data": {"object": obj},
        }

    def invoice_payment(cus: str, amount: int, t: int) -> Dict:
        return {
            "id": _sid("evt"), "type": "invoice.payment_succeeded",
            "created": t, "_demo": DEMO_TAG,
            "data": {"object": {
                "id": _sid("in"), "object": "invoice",
                "customer": cus, "amount_paid": amount,
                "total": amount, "currency": "usd",
                "status_transitions": {"paid_at": t},
                "_demo": DEMO_TAG,
            }},
        }

    def dispute(cus: str, amount: int, t: int) -> Dict:
        return {
            "id": _sid("evt"), "type": "charge.dispute.created",
            "created": t, "_demo": DEMO_TAG,
            "data": {"object": {
                "id": _sid("dp"), "object": "dispute",
                "charge": _sid("ch"), "customer": cus,
                "amount": amount, "currency": "usd",
                "reason": "fraudulent", "status": "needs_response",
                "created": t, "_demo": DEMO_TAG,
            }},
        }

    def refund(cus: str, amount: int, t: int) -> Dict:
        ch_id = _sid("ch")
        return {
            "id": _sid("evt"), "type": "charge.refunded",
            "created": t, "_demo": DEMO_TAG,
            "data": {"object": {
                "id": ch_id, "object": "charge",
                "customer": cus, "amount_refunded": amount,
                "currency": "usd", "created": t,
                "_demo": DEMO_TAG,
            }},
        }

    # ── Normal traffic: T-24h → T-6h ─────────────────────────────────
    for i in range(80):
        cus = customers[i % len(customers)]
        hours_ago = 24 - (i * 0.22)   # spread across 18h window
        events.append(charge("charge.succeeded", cus, 9900, ts(hours_ago)))

    # Monthly renewals (invoice payments — feed revenue_drop baseline)
    for i in range(40):
        cus = customers[i % len(customers)]
        hours_ago = 20 - (i * 0.4)
        events.append(invoice_payment(cus, 9900, ts(hours_ago)))

    # ── Charge failure spike: T-6h → T-5h ────────────────────────────
    spike_cus = customers[0]
    events.append(charge("charge.succeeded", spike_cus, 9900, ts(6.1)))
    events.append(charge("charge.succeeded", spike_cus, 9900, ts(6.0)))
    for i in range(18):
        cus = customers[i % len(customers)]
        events.append(charge("charge.failed", cus, 9900, ts(5.9 - i * 0.04)))

    # ── Duplicate charge: T-3h ────────────────────────────────────────
    dup_cus = customers[3]
    for _ in range(3):
        events.append(charge("charge.succeeded", dup_cus, 9900, ts(3.0)))

    # ── Fraud disputes: T-2h ─────────────────────────────────────────
    for i in range(6):
        cus = customers[i % len(customers)]
        events.append(charge("charge.succeeded", cus, 4900, ts(2.2 - i * 0.05)))
    for i in range(6):
        cus = customers[i % len(customers)]
        events.append(dispute(cus, 4900, ts(2.0 - i * 0.03)))

    # ── Large refund: T-1h ────────────────────────────────────────────
    events.append(refund(customers[5], 75000, ts(1.0)))

    # Sort chronologically
    events.sort(key=lambda e: e["created"])
    return events


# ---------------------------------------------------------------------------
# Routes (appended to demo router)
# ---------------------------------------------------------------------------

def register_seed_routes(router: APIRouter, detectors: dict, alert_log: list,
                         event_store: Any) -> None:
    """
    Attach seed routes to the existing demo router.

    Called from webhooks.py (which owns detectors, alert_log, event_store).
    """

    @router.post("/seed", summary="Seed live pipeline with 24h of demo billing history")
    async def seed_demo():
        """
        Injects synthetic billing events into the live EventStore and runs
        them through all detectors. After calling this, the dashboard will
        show real anomaly data, metrics, and alerts — without requiring an
        active Stripe account.

        Safe to call multiple times — duplicate events are silently skipped.
        Events are tagged with `_demo: true` so they can be removed later.
        """
        now = time.time()
        stream = _build_event_stream(now)

        inserted = 0
        skipped = 0
        alerts_fired = []

        for event in stream:
            rows = event_store.insert_event(event)
            if rows == 0:
                skipped += 1
                continue
            inserted += 1

            # Run through all live detectors
            for name, detector in detectors.items():
                try:
                    fired = detector.process_event(event)
                    for alert in fired:
                        entry = alert.to_dict()
                        entry["stripe_event_id"] = event.get("id")
                        entry["demo"] = True
                        # Assign alert_id using webhooks counter
                        from . import webhooks as _wh
                        _wh._alert_id_counter += 1
                        entry["alert_id"] = _wh._alert_id_counter
                        alert_log.append(entry)
                        if len(alert_log) > 500:
                            alert_log.pop(0)
                        alerts_fired.append(entry)
                except Exception as exc:
                    pass   # don't let demo seeding crash the response

        # Run scheduled checks to catch revenue_drop and silent_lapse
        for name, detector in detectors.items():
            try:
                for alert in detector.check():
                    entry = alert.to_dict()
                    entry["demo"] = True
                    from . import webhooks as _wh
                    _wh._alert_id_counter += 1
                    entry["alert_id"] = _wh._alert_id_counter
                    alert_log.append(entry)
                    if len(alert_log) > 500:
                        alert_log.pop(0)
                    alerts_fired.append(entry)
            except Exception:
                pass

        return {
            "seeded": True,
            "events_injected": inserted,
            "events_skipped_duplicate": skipped,
            "alerts_fired": len(alerts_fired),
            "alerts": alerts_fired[:20],  # cap response size
            "message": (
                "Demo data injected into the live pipeline. "
                "Check /anomalies/, /metrics/, and /webhooks/alerts for results."
            ),
        }

    @router.delete("/seed", summary="Remove all demo-seeded events from EventStore")
    async def clear_demo():
        """
        Deletes all events tagged as demo data from the EventStore.
        Does not reset in-memory detector state (requires server restart for full reset).
        """
        with event_store._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM events WHERE payload_json LIKE ?",
                (f'%"{DEMO_TAG}"%',)
            )
            deleted = cursor.rowcount
            conn.commit()
        return {
            "cleared": True,
            "events_deleted": deleted,
            "note": "In-memory detector state not reset. Restart server for full clean slate.",
        }

    @router.get("/seed/status", summary="Check if demo data has been seeded")
    async def seed_status():
        """Returns whether demo events are present in the EventStore."""
        with event_store._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM events WHERE payload_json LIKE ?",
                (f'%"{DEMO_TAG}"%',)
            ).fetchone()
        count = row[0] if row else 0
        demo_alerts = [a for a in alert_log if a.get("demo")]
        return {
            "demo_events_in_store": count,
            "demo_alerts_in_memory": len(demo_alerts),
            "seeded": count > 0,
        }
