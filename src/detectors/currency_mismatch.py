"""Currency Mismatch Detector.

Detects when a customer is charged in a currency that differs from their
established billing currency — a strong signal of misconfigured locale
settings, multi-currency rollout bugs, or accidental default-currency
fallbacks.

Listens to:
  - charge.succeeded
  - invoice.payment_succeeded

Detection logic:
  - Each customer's first BASELINE_EVENTS charges establish their
    "home currency."
  - Any subsequent charge in a different currency fires an alert.
  - Cooldown prevents repeated alerts for the same (customer, mismatch) pair.
"""
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from .base import Alert, BaseDetector

# How many charges to observe before locking in the customer's home currency
BASELINE_EVENTS = 3
# Cooldown per (customer_id, mismatched_currency) pair (1 hour)
PAIR_COOLDOWN_SECONDS = 3600


class CurrencyMismatchDetector(BaseDetector):
    """Detects charges in an unexpected currency for a customer."""

    name = "currency_mismatch"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._baseline = self.config.get("baseline_events", BASELINE_EVENTS)
        self._cooldown = self.config.get("pair_cooldown_seconds", PAIR_COOLDOWN_SECONDS)

        # customer_id → list of observed currencies (up to baseline_events)
        self._customer_currencies: Dict[str, List[str]] = defaultdict(list)
        # (customer_id, mismatched_currency) → last alert timestamp
        self._last_alerted: Dict[Tuple[str, str], float] = {}

    def _extract_charge_info(
        self, event: Dict[str, Any]
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Return (event_id, customer_id, currency) or (None, None, None)."""
        event_type = event.get("type", "")
        obj = event.get("data", {}).get("object", {})

        if event_type == "charge.succeeded":
            return (
                obj.get("id") or event.get("id"),
                obj.get("customer"),
                obj.get("currency"),
            )
        if event_type == "invoice.payment_succeeded":
            return (
                obj.get("charge") or event.get("id"),
                obj.get("customer"),
                obj.get("currency"),
            )
        return None, None, None

    def process_event(self, event: Dict[str, Any]) -> List[Alert]:
        _, customer_id, currency = self._extract_charge_info(event)

        if not customer_id or not currency:
            return []

        currency = currency.upper()
        history = self._customer_currencies[customer_id]

        # Still building baseline
        if len(history) < self._baseline:
            history.append(currency)
            return []

        # Determine home currency (most common in baseline)
        home_currency = max(set(history), key=history.count)

        if currency == home_currency:
            return []

        # Currency mismatch detected
        key = (customer_id, currency)
        now = time.time()
        last = self._last_alerted.get(key)
        if last and (now - last) < self._cooldown:
            return []
        self._last_alerted[key] = now

        alert = Alert(
            detector=self.name,
            severity="high",
            title="Currency Mismatch Detected",
            message=(
                f"Customer {customer_id} was charged in {currency} but their "
                f"established billing currency is {home_currency}. "
                f"This may indicate a locale misconfiguration or currency-fallback bug."
            ),
            metadata={
                "customer_id": customer_id,
                "expected_currency": home_currency,
                "actual_currency": currency,
                "baseline_history": history,
            },
        )
        self._log(f"ALERT: {alert.message}")
        return [alert]

    def check(self) -> List[Alert]:
        """No scheduled check — purely event-driven."""
        return []
