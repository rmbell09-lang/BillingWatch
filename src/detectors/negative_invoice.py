"""Negative Invoice / Credit Reversal Detector.

Detects unusually large credit notes, refunds, or negative invoices that may
indicate a billing error, abuse, or runaway coupon application.

Listens to:
  - credit_note.created          → credit note applied against an invoice
  - charge.refunded              → full or partial refund issued
  - invoice.payment_succeeded    → catches negative-total invoices (edge case)

Triggers when:
  1. A single refund/credit exceeds LARGE_REFUND_THRESHOLD
  2. Total refunds to one customer in 24h exceed CUSTOMER_DAILY_THRESHOLD
  3. Platform-wide refund rate (refund_amount / revenue) exceeds RATE_THRESHOLD
"""
import time
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional

from .base import Alert, BaseDetector

# Single refund/credit thresholds
LARGE_REFUND_THRESHOLD_CENTS = 50_000   # $500 — single large refund
CUSTOMER_DAILY_THRESHOLD_CENTS = 100_000  # $1,000 — total per customer in 24h

# Platform-wide refund rate threshold (rolling 24h)
REVENUE_WINDOW_SECONDS = 86400
REFUND_RATE_THRESHOLD = 0.10  # 10% of revenue being refunded is abnormal
MIN_REVENUE_FOR_RATE = 10_000  # Only compute rate if > $100 revenue

COOLDOWN_SECONDS = 3600  # 1 hr between alerts of the same type


class NegativeInvoiceDetector(BaseDetector):
    """Detects abnormally large refunds, credits, or negative billing events."""

    name = "negative_invoice"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._large_threshold = self.config.get("large_refund_threshold_cents", LARGE_REFUND_THRESHOLD_CENTS)
        self._customer_daily = self.config.get("customer_daily_threshold_cents", CUSTOMER_DAILY_THRESHOLD_CENTS)
        self._rate_threshold = self.config.get("refund_rate_threshold", REFUND_RATE_THRESHOLD)
        self._min_revenue = self.config.get("min_revenue_for_rate", MIN_REVENUE_FOR_RATE)
        self._cooldown = self.config.get("cooldown_seconds", COOLDOWN_SECONDS)

        # Rolling 24h windows
        # (timestamp, amount_cents)
        self._refunds: deque = deque()
        self._revenue: deque = deque()

        # Per-customer 24h refund totals: customer_id → deque of (ts, cents)
        self._customer_refunds: Dict[str, deque] = defaultdict(deque)

        # Alert cooldowns
        self._last_large_alert: Dict[str, float] = {}  # keyed by charge/credit ID
        self._last_rate_alert_at: Optional[float] = None
        self._last_customer_alert: Dict[str, float] = {}

    def _prune(self):
        cutoff = time.time() - REVENUE_WINDOW_SECONDS
        for q in (self._refunds, self._revenue):
            while q and q[0][0] < cutoff:
                q.popleft()

    def _prune_customer(self, customer_id: str):
        cutoff = time.time() - REVENUE_WINDOW_SECONDS
        q = self._customer_refunds[customer_id]
        while q and q[0][0] < cutoff:
            q.popleft()

    def process_event(self, event: Dict[str, Any]) -> List[Alert]:
        event_type = event.get("type", "")
        data_obj = event.get("data", {}).get("object", {})
        alerts: List[Alert] = []
        now = time.time()

        if event_type == "charge.refunded":
            # amount_refunded is in cents
            amount = data_obj.get("amount_refunded", 0)
            charge_id = data_obj.get("id", event.get("id", "unknown"))
            customer_id = str(data_obj.get("customer", "unknown"))

            if amount > 0:
                self._refunds.append((now, amount))
                self._customer_refunds[customer_id].append((now, amount))
                alerts.extend(self._check_large_refund(amount, charge_id, customer_id, "refund"))
                alerts.extend(self._check_customer_total(customer_id))

        elif event_type == "credit_note.created":
            amount = data_obj.get("total", 0)  # credit note total in cents (positive = credit)
            credit_id = data_obj.get("id", event.get("id", "unknown"))
            customer_id = str(data_obj.get("customer", "unknown"))

            if amount > 0:
                self._refunds.append((now, amount))
                self._customer_refunds[customer_id].append((now, amount))
                alerts.extend(self._check_large_refund(amount, credit_id, customer_id, "credit note"))
                alerts.extend(self._check_customer_total(customer_id))

        elif event_type == "invoice.payment_succeeded":
            amount_paid = data_obj.get("amount_paid", 0)
            if amount_paid < 0:
                # Negative invoice — unusual, always alert
                invoice_id = data_obj.get("id", event.get("id", "unknown"))
                customer_id = str(data_obj.get("customer", "unknown"))
                alert = Alert(
                    detector=self.name,
                    severity="high",
                    title="Negative Invoice Detected",
                    message=(
                        f"Invoice {invoice_id} for customer {customer_id} has a negative total: "
                        f"${abs(amount_paid) / 100:.2f}. This typically indicates a billing configuration error."
                    ),
                    metadata={"invoice_id": invoice_id, "customer_id": customer_id, "amount_cents": amount_paid},
                )
                alerts.append(alert)
            elif amount_paid > 0:
                self._revenue.append((now, amount_paid))

        self._prune()
        alerts.extend(self._check_refund_rate())
        return alerts

    def check(self) -> List[Alert]:
        self._prune()
        return self._check_refund_rate()

    def _check_large_refund(
        self, amount_cents: int, event_id: str, customer_id: str, kind: str
    ) -> List[Alert]:
        if amount_cents < self._large_threshold:
            return []
        now = time.time()
        last = self._last_large_alert.get(event_id)
        if last and (now - last) < self._cooldown:
            return []
        self._last_large_alert[event_id] = now

        amount_dollars = amount_cents / 100
        threshold_dollars = self._large_threshold / 100
        alert = Alert(
            detector=self.name,
            severity="high",
            title=f"Large {kind.title()} Issued: ${amount_dollars:.2f}",
            message=(
                f"A {kind} of ${amount_dollars:.2f} was issued for customer {customer_id}. "
                f"This exceeds the alert threshold of ${threshold_dollars:.2f}. "
                f"Event ID: {event_id}."
            ),
            metadata={
                "amount_cents": amount_cents,
                "amount_dollars": amount_dollars,
                "customer_id": customer_id,
                "event_id": event_id,
                "kind": kind,
                "threshold_cents": self._large_threshold,
            },
        )
        self._log(f"ALERT: {alert.message}")
        return [alert]

    def _check_customer_total(self, customer_id: str) -> List[Alert]:
        self._prune_customer(customer_id)
        total = sum(a for _, a in self._customer_refunds[customer_id])
        if total < self._customer_daily:
            return []
        now = time.time()
        last = self._last_customer_alert.get(customer_id)
        if last and (now - last) < self._cooldown:
            return []
        self._last_customer_alert[customer_id] = now

        total_dollars = total / 100
        threshold_dollars = self._customer_daily / 100
        alert = Alert(
            detector=self.name,
            severity="critical",
            title=f"High Refund Volume for Customer {customer_id}",
            message=(
                f"Customer {customer_id} has received ${total_dollars:.2f} in refunds/credits "
                f"in the past 24 hours — exceeds threshold of ${threshold_dollars:.2f}. "
                f"Possible abuse, chargeback farming, or billing error."
            ),
            metadata={
                "customer_id": customer_id,
                "total_refunded_cents": total,
                "total_refunded_dollars": total_dollars,
                "threshold_cents": self._customer_daily,
                "window_seconds": REVENUE_WINDOW_SECONDS,
            },
        )
        self._log(f"ALERT: {alert.message}")
        return [alert]

    def _check_refund_rate(self) -> List[Alert]:
        total_revenue = sum(a for _, a in self._revenue)
        total_refunds = sum(a for _, a in self._refunds)

        if total_revenue < self._min_revenue or total_refunds == 0:
            return []

        rate = total_refunds / total_revenue
        if rate < self._rate_threshold:
            return []

        now = time.time()
        if self._last_rate_alert_at and (now - self._last_rate_alert_at) < self._cooldown:
            return []
        self._last_rate_alert_at = now

        alert = Alert(
            detector=self.name,
            severity="high",
            title=f"High Refund Rate: {rate:.1%}",
            message=(
                f"Refunds are {rate:.1%} of revenue over the past 24 hours "
                f"(${total_refunds/100:.2f} refunded of ${total_revenue/100:.2f} revenue). "
                f"Threshold is {self._rate_threshold:.0%}."
            ),
            metadata={
                "refund_rate": round(rate, 4),
                "total_refunds_cents": total_refunds,
                "total_revenue_cents": total_revenue,
                "threshold": self._rate_threshold,
                "window_seconds": REVENUE_WINDOW_SECONDS,
            },
        )
        self._log(f"ALERT: {alert.message}")
        return [alert]
