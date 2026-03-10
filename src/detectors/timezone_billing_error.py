"""Timezone Billing Error Detector.

Detects billing anomalies caused by timezone misconfiguration — the most
common class being a subscription invoiced twice within the same 26-hour
window (UTC vs local-time rollover) or a renewal that fires dramatically
earlier or later than its expected cadence.

Listens to:
  - invoice.created        → tracks invoice creation per subscription
  - invoice.payment_succeeded → secondary confirmation

Detection logic:
  1. Double-invoice: same subscription_id gets two invoices created within
     DOUBLE_INVOICE_WINDOW_HOURS hours. Likely cause: billing cycle anchor
     computed in local time while Stripe operates in UTC, causing two
     "start of month" triggers in the same rolling window.
  2. Cadence drift: monthly subscription renews more than CADENCE_TOLERANCE_HOURS
     early or late relative to expected (28–31 day cadence). Signals a timezone
     offset shifting the billing anchor by ~24 h each cycle.
"""
import time
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Tuple

from .base import Alert, BaseDetector

# Window within which two invoices for the same subscription = suspicious (hours)
DOUBLE_INVOICE_WINDOW_HOURS = 26
# For cadence drift: expected monthly window (days)
MONTHLY_MIN_DAYS = 27
MONTHLY_MAX_DAYS = 32
# Tolerance before flagging drift (hours beyond expected window)
CADENCE_TOLERANCE_HOURS = 25
# Cooldown per subscription alert (2 hours)
SUBSCRIPTION_COOLDOWN_SECONDS = 7200


class TimezoneBillingErrorDetector(BaseDetector):
    """Detects double-invoicing and cadence drift caused by timezone misconfiguration."""

    name = "timezone_billing_error"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._window_secs = self.config.get(
            "double_invoice_window_hours", DOUBLE_INVOICE_WINDOW_HOURS
        ) * 3600
        self._cadence_tolerance_secs = self.config.get(
            "cadence_tolerance_hours", CADENCE_TOLERANCE_HOURS
        ) * 3600
        self._cooldown = self.config.get(
            "subscription_cooldown_seconds", SUBSCRIPTION_COOLDOWN_SECONDS
        )
        self._monthly_min_secs = MONTHLY_MIN_DAYS * 86400
        self._monthly_max_secs = MONTHLY_MAX_DAYS * 86400

        # subscription_id → deque of invoice creation timestamps
        self._invoice_times: Dict[str, deque] = defaultdict(deque)
        # subscription_id → last alert timestamp
        self._last_alerted: Dict[str, float] = {}

    def _prune(self, sub_id: str):
        cutoff = time.time() - self._window_secs
        q = self._invoice_times[sub_id]
        while q and q[0] < cutoff:
            q.popleft()

    def _maybe_alert(self, sub_id: str, title: str, message: str, metadata: dict) -> List[Alert]:
        now = time.time()
        last = self._last_alerted.get(sub_id)
        if last and (now - last) < self._cooldown:
            return []
        self._last_alerted[sub_id] = now

        alert = Alert(
            detector=self.name,
            severity="high",
            title=title,
            message=message,
            metadata=metadata,
        )
        self._log(f"ALERT: {alert.message}")
        return [alert]

    def process_event(self, event: Dict[str, Any]) -> List[Alert]:
        event_type = event.get("type", "")
        if event_type not in ("invoice.created", "invoice.payment_succeeded"):
            return []

        obj = event.get("data", {}).get("object", {})
        sub_id = obj.get("subscription")
        if not sub_id:
            return []

        # Use Stripe's created timestamp if present, else wall clock
        created_ts = obj.get("created") or time.time()
        if isinstance(created_ts, int):
            now_ts = float(created_ts)
        else:
            now_ts = time.time()

        self._prune(sub_id)
        q = self._invoice_times[sub_id]
        alerts: List[Alert] = []

        # ── Check 1: Double-invoice within window ──────────────────────────
        if len(q) >= 1:
            prev_ts = q[-1]
            gap_hours = (now_ts - prev_ts) / 3600
            if gap_hours < (DOUBLE_INVOICE_WINDOW_HOURS):
                alerts += self._maybe_alert(
                    sub_id,
                    title="Double Invoice Detected (Timezone Suspect)",
                    message=(
                        f"Subscription {sub_id} received two invoices only "
                        f"{gap_hours:.1f}h apart — well inside the "
                        f"{DOUBLE_INVOICE_WINDOW_HOURS}h threshold. "
                        f"Common cause: billing anchor computed in local time "
                        f"while Stripe uses UTC, triggering a double-renewal at "
                        f"a timezone boundary."
                    ),
                    metadata={
                        "subscription_id": sub_id,
                        "gap_hours": round(gap_hours, 2),
                        "threshold_hours": DOUBLE_INVOICE_WINDOW_HOURS,
                    },
                )

        # ── Check 2: Monthly cadence drift ─────────────────────────────────
        if len(q) >= 1 and not alerts:
            prev_ts = q[-1]
            gap_secs = now_ts - prev_ts
            # Only evaluate monthly-ish cadences
            if self._monthly_min_secs * 0.5 < gap_secs < self._monthly_max_secs * 1.5:
                if gap_secs < self._monthly_min_secs - self._cadence_tolerance_secs:
                    drift_hours = (self._monthly_min_secs - gap_secs) / 3600
                    alerts += self._maybe_alert(
                        sub_id,
                        title="Billing Cadence Too Early (Timezone Drift)",
                        message=(
                            f"Subscription {sub_id} renewed {drift_hours:.1f}h "
                            f"earlier than the minimum monthly cadence of "
                            f"{MONTHLY_MIN_DAYS} days. Likely timezone offset "
                            f"is advancing the billing anchor each cycle."
                        ),
                        metadata={
                            "subscription_id": sub_id,
                            "gap_days": round(gap_secs / 86400, 2),
                            "expected_min_days": MONTHLY_MIN_DAYS,
                            "drift_hours": round(drift_hours, 1),
                        },
                    )
                elif gap_secs > self._monthly_max_secs + self._cadence_tolerance_secs:
                    drift_hours = (gap_secs - self._monthly_max_secs) / 3600
                    alerts += self._maybe_alert(
                        sub_id,
                        title="Billing Cadence Too Late (Timezone Drift)",
                        message=(
                            f"Subscription {sub_id} renewed {drift_hours:.1f}h "
                            f"later than the maximum monthly cadence of "
                            f"{MONTHLY_MAX_DAYS} days. Timezone offset may be "
                            f"delaying the billing anchor each cycle."
                        ),
                        metadata={
                            "subscription_id": sub_id,
                            "gap_days": round(gap_secs / 86400, 2),
                            "expected_max_days": MONTHLY_MAX_DAYS,
                            "drift_hours": round(drift_hours, 1),
                        },
                    )

        q.append(now_ts)
        return alerts

    def check(self) -> List[Alert]:
        """Prune stale data; no periodic alert needed — event-driven only."""
        for sub_id in list(self._invoice_times.keys()):
            self._prune(sub_id)
        return []
