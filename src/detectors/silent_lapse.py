"""Silent Subscription Lapse Detector.

Detects subscriptions that are marked 'active' by Stripe but have not had
a successful charge in longer than their billing interval + 3-day grace period.

Listens to:
  - customer.subscription.updated  → tracks active subs and billing intervals
  - invoice.payment_succeeded      → records last successful payment per customer
  
Scheduled check (runs every 15 min via scheduler) to catch lapses
that may not generate a new event.
"""
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import Alert, BaseDetector

# Grace period on top of billing interval
GRACE_DAYS = 3
GRACE_SECONDS = GRACE_DAYS * 86400

# Billing interval → seconds mapping
INTERVAL_SECONDS = {
    "day": 86400,
    "week": 604800,
    "month": 2592000,   # 30 days
    "year": 31536000,   # 365 days
}


class SilentLapseDetector(BaseDetector):
    """Detects subscriptions with no successful charge past their billing interval."""

    name = "silent_subscription_lapse"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        # customer_id → {"subscription_id": str, "interval_seconds": int, "status": str}
        self._subscriptions: Dict[str, Dict[str, Any]] = {}
        # customer_id → last successful payment timestamp (unix)
        self._last_payment: Dict[str, float] = {}
        # customer_id → timestamp we last alerted (to avoid repeat noise)
        self._last_alerted: Dict[str, float] = {}
        self._alert_cooldown = self.config.get("alert_cooldown_seconds", 3600)  # 1hr

    def process_event(self, event: Dict[str, Any]) -> List[Alert]:
        event_type = event.get("type", "")
        obj = event.get("data", {}).get("object", {})

        if event_type in ("customer.subscription.created", "customer.subscription.updated"):
            return self._handle_subscription(obj)
        elif event_type == "customer.subscription.deleted":
            return self._handle_subscription_deleted(obj)
        elif event_type == "invoice.payment_succeeded":
            return self._handle_payment(obj)
        return []

    def _handle_subscription(self, sub: Dict[str, Any]) -> List[Alert]:
        customer_id = sub.get("customer")
        status = sub.get("status", "")
        sub_id = sub.get("id", "")

        if not customer_id:
            return []

        # Parse billing interval
        plan = sub.get("plan") or {}
        items_data = sub.get("items", {}).get("data", [])
        if items_data:
            plan = items_data[0].get("plan") or items_data[0].get("price", {})

        interval = plan.get("interval", "month")
        interval_seconds = INTERVAL_SECONDS.get(interval, INTERVAL_SECONDS["month"])
        interval_count = plan.get("interval_count", 1)

        self._subscriptions[customer_id] = {
            "subscription_id": sub_id,
            "interval_seconds": interval_seconds * interval_count,
            "status": status,
        }
        return []

    def _handle_subscription_deleted(self, sub: Dict[str, Any]) -> List[Alert]:
        """Stop tracking a cancelled/deleted subscription."""
        customer_id = sub.get("customer")
        if customer_id and customer_id in self._subscriptions:
            del self._subscriptions[customer_id]
            self._log(f"Subscription deleted for customer {customer_id} — removed from tracking")
        return []

    def _handle_payment(self, invoice: Dict[str, Any]) -> List[Alert]:
        customer_id = invoice.get("customer")
        if not customer_id:
            return []
        paid_at = invoice.get("status_transitions", {}).get("paid_at") or time.time()
        self._last_payment[customer_id] = float(paid_at)
        return []

    def check(self) -> List[Alert]:
        """Scheduled check — scan all known active subscriptions for lapses."""
        now = time.time()
        alerts = []

        for customer_id, sub_info in self._subscriptions.items():
            if sub_info.get("status") != "active":
                continue

            interval_s = sub_info["interval_seconds"]
            last_paid = self._last_payment.get(customer_id)

            if last_paid is None:
                # Never seen a payment — flag if subscription is older than interval + grace
                continue  # Skip: we may have just started tracking

            overdue_by = now - last_paid - interval_s - GRACE_SECONDS
            if overdue_by <= 0:
                continue  # Not overdue yet

            # Cooldown check
            last_alert = self._last_alerted.get(customer_id, 0)
            if (now - last_alert) < self._alert_cooldown:
                continue

            self._last_alerted[customer_id] = now
            overdue_days = overdue_by / 86400
            days_since_payment = (now - last_paid) / 86400

            alert = Alert(
                detector=self.name,
                severity="high",
                title="Silent Subscription Lapse",
                message=(
                    f"Customer {customer_id} subscription {sub_info['subscription_id']} "
                    f"is active but has no payment in {days_since_payment:.1f} days "
                    f"(overdue by {overdue_days:.1f} days past billing interval + {GRACE_DAYS}d grace)."
                ),
                metadata={
                    "customer_id": customer_id,
                    "subscription_id": sub_info["subscription_id"],
                    "days_since_payment": round(days_since_payment, 1),
                    "overdue_days": round(overdue_days, 1),
                    "interval_seconds": interval_s,
                },
            )
            self._log(f"ALERT: {alert.message}")
            alerts.append(alert)

        return alerts
