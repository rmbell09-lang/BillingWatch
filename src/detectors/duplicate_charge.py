"""Duplicate Charge Detector.

Detects when the same customer is charged the same amount within a short
time window — a strong signal of billing loop bugs or retry misconfiguration.

Listens to: charge.succeeded, invoice.payment_succeeded

Detection logic:
  - If (customer_id, amount_cents) appears more than DUPLICATE_THRESHOLD times
    within WINDOW_SECONDS, fire an alert.
  - Deduplicates by Stripe charge ID to avoid counting the same event twice.
"""
import time
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Tuple

from .base import Alert, BaseDetector

# Window to check for duplicates (5 minutes)
WINDOW_SECONDS = 300
# How many same-amount charges from the same customer in the window = suspicious
DUPLICATE_THRESHOLD = 2
# Cooldown between alerts per (customer, amount) pair
PAIR_COOLDOWN_SECONDS = 600


class DuplicateChargeDetector(BaseDetector):
    """Detects repeated identical charges to the same customer."""

    name = "duplicate_charge"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._window = self.config.get("window_seconds", WINDOW_SECONDS)
        self._threshold = self.config.get("duplicate_threshold", DUPLICATE_THRESHOLD)
        self._cooldown = self.config.get("pair_cooldown_seconds", PAIR_COOLDOWN_SECONDS)

        # (customer_id, amount_cents) → deque of (timestamp, charge_id)
        self._charge_log: Dict[Tuple[str, int], deque] = defaultdict(deque)
        # (customer_id, amount_cents) → last alert timestamp
        self._last_alerted: Dict[Tuple[str, int], float] = {}
        # Seen charge IDs (prevent double-counting same event)
        self._seen_charge_ids: set = set()

    def _prune(self, key: Tuple[str, int]):
        cutoff = time.time() - self._window
        q = self._charge_log[key]
        while q and q[0][0] < cutoff:
            q.popleft()

    def process_event(self, event: Dict[str, Any]) -> List[Alert]:
        event_type = event.get("type", "")
        data_obj = event.get("data", {}).get("object", {})

        charge_id = None
        customer_id = None
        amount_cents = None

        if event_type == "charge.succeeded":
            charge_id = data_obj.get("id") or event.get("id")
            customer_id = data_obj.get("customer")
            amount_cents = data_obj.get("amount")

        elif event_type == "invoice.payment_succeeded":
            charge_id = data_obj.get("charge") or event.get("id")
            customer_id = data_obj.get("customer")
            amount_cents = data_obj.get("amount_paid")

        if not all([charge_id, customer_id, amount_cents]):
            return []

        if charge_id in self._seen_charge_ids:
            return []
        self._seen_charge_ids.add(charge_id)

        key = (str(customer_id), int(amount_cents))
        now = time.time()
        self._charge_log[key].append((now, charge_id))
        self._prune(key)

        count = len(self._charge_log[key])
        if count < self._threshold:
            return []

        # Cooldown
        last = self._last_alerted.get(key)
        if last and (now - last) < self._cooldown:
            return []
        self._last_alerted[key] = now

        charge_ids = [cid for _, cid in self._charge_log[key]]
        amount_dollars = int(amount_cents) / 100

        alert = Alert(
            detector=self.name,
            severity="high",
            title="Duplicate Charges Detected",
            message=(
                f"Customer {customer_id} was charged ${amount_dollars:.2f} "
                f"{count} times in {self._window // 60} minutes. "
                f"Possible double-billing or retry loop bug. Charge IDs: {', '.join(charge_ids[:5])}."
            ),
            metadata={
                "customer_id": customer_id,
                "amount_cents": int(amount_cents),
                "amount_dollars": amount_dollars,
                "charge_count": count,
                "charge_ids": charge_ids,
                "window_seconds": self._window,
                "threshold": self._threshold,
            },
        )
        self._log(f"ALERT: {alert.message}")
        return [alert]

    def check(self) -> List[Alert]:
        """Prune stale data; no scheduled alert for duplicate charges — event-driven only."""
        for key in list(self._charge_log.keys()):
            self._prune(key)
        return []
