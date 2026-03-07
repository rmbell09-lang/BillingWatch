"""Fraud Spike Detector.

Triggers when the rate of disputed/fraudulent charges exceeds threshold
over a rolling 24-hour window.

Listens to:
  - charge.dispute.created       → new dispute opened (high-confidence fraud signal)
  - charge.dispute.closed        → dispute resolved (track outcome)
  - radar.early_fraud_warning    → Stripe Radar early warning (pre-dispute fraud)

Scheduled check (every 15 min) re-evaluates the current window.
"""
import time
from collections import deque
from typing import Any, Dict, List, Optional

from .base import Alert, BaseDetector

# Rolling window: 24 hours
WINDOW_SECONDS = 86400

# Alert if dispute rate exceeds this fraction of total charges
DISPUTE_RATE_THRESHOLD = 0.01   # 1% — Stripe's threshold for high-risk accounts
EFW_RATE_THRESHOLD = 0.005      # 0.5% for early fraud warnings

# Minimum charges before we consider the rate meaningful
MIN_CHARGE_VOLUME = 20

# Absolute dispute count that always triggers regardless of rate
ABSOLUTE_DISPUTE_THRESHOLD = 5


class FraudSpikeDetector(BaseDetector):
    """Detects spike in disputes and early fraud warnings over a rolling 24-hour window."""

    name = "fraud_spike"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        # Timestamps of dispute.created events in the window
        self._disputes: deque = deque()
        # Timestamps of radar.early_fraud_warning events
        self._efws: deque = deque()
        # Timestamps of all charges (succeeded + failed) for rate denominator
        self._charges: deque = deque()
        # Cooldowns
        self._last_dispute_alert_at: Optional[float] = None
        self._last_efw_alert_at: Optional[float] = None
        self._alert_cooldown = self.config.get("alert_cooldown_seconds", 3600)  # 1 hr
        self._window = self.config.get("window_seconds", WINDOW_SECONDS)
        self._dispute_threshold = self.config.get("dispute_rate_threshold", DISPUTE_RATE_THRESHOLD)
        self._efw_threshold = self.config.get("efw_rate_threshold", EFW_RATE_THRESHOLD)
        self._min_volume = self.config.get("min_charge_volume", MIN_CHARGE_VOLUME)
        self._abs_threshold = self.config.get("absolute_dispute_threshold", ABSOLUTE_DISPUTE_THRESHOLD)

    def _prune_all(self):
        """Remove entries outside the rolling window."""
        cutoff = time.time() - self._window
        for q in (self._disputes, self._efws, self._charges):
            while q and q[0] < cutoff:
                q.popleft()

    def process_event(self, event: Dict[str, Any]) -> List[Alert]:
        """Handle dispute and charge events."""
        event_type = event.get("type", "")
        now = time.time()
        alerts: List[Alert] = []

        if event_type in ("charge.succeeded", "charge.failed"):
            self._charges.append(now)

        elif event_type == "charge.dispute.created":
            self._disputes.append(now)
            self._charges.append(now)  # dispute implies a charge existed
            self._prune_all()
            alerts.extend(self._evaluate_disputes())

        elif event_type == "radar.early_fraud_warning":
            self._efws.append(now)
            self._prune_all()
            alerts.extend(self._evaluate_efws())

        elif event_type == "charge.dispute.closed":
            # Outcome is informational; re-evaluate rates
            self._prune_all()
            alerts.extend(self._evaluate_disputes())

        self._prune_all()
        return alerts

    def check(self) -> List[Alert]:
        """Scheduled evaluation — re-check without a triggering event."""
        self._prune_all()
        alerts = self._evaluate_disputes()
        alerts += self._evaluate_efws()
        return alerts

    def _evaluate_disputes(self) -> List[Alert]:
        """Fire if dispute rate or absolute count exceeds threshold."""
        dispute_count = len(self._disputes)
        charge_count = max(len(self._charges), 1)

        # Absolute threshold — always alert regardless of volume
        if dispute_count >= self._abs_threshold:
            return self._maybe_alert_dispute(dispute_count, charge_count, absolute=True)

        if charge_count < self._min_volume:
            return []

        rate = dispute_count / charge_count
        if rate >= self._dispute_threshold:
            return self._maybe_alert_dispute(dispute_count, charge_count, absolute=False, rate=rate)

        return []

    def _maybe_alert_dispute(
        self,
        dispute_count: int,
        charge_count: int,
        absolute: bool,
        rate: float = 0.0,
    ) -> List[Alert]:
        now = time.time()
        if self._last_dispute_alert_at and (now - self._last_dispute_alert_at) < self._alert_cooldown:
            return []
        self._last_dispute_alert_at = now

        if absolute:
            title = f"Fraud Alert: {dispute_count} Disputes in 24 Hours"
            message = (
                f"{dispute_count} disputes opened in the past 24 hours — "
                f"exceeds absolute threshold of {self._abs_threshold}. "
                f"Stripe may flag your account as high-risk."
            )
            severity = "critical"
        else:
            title = "Fraud Spike: Dispute Rate Elevated"
            message = (
                f"Dispute rate is {rate:.2%} ({dispute_count}/{charge_count} charges) "
                f"in the past 24 hours — threshold is {self._dispute_threshold:.1%}. "
                f"Stripe's high-risk threshold is 1%."
            )
            severity = "high"

        alert = Alert(
            detector=self.name,
            severity=severity,
            title=title,
            message=message,
            metadata={
                "dispute_count": dispute_count,
                "charge_count": charge_count,
                "dispute_rate": round(dispute_count / max(charge_count, 1), 4),
                "window_seconds": self._window,
                "threshold": self._dispute_threshold,
            },
        )
        self._log(f"ALERT: {alert.message}")
        return [alert]

    def _evaluate_efws(self) -> List[Alert]:
        """Fire if early fraud warning rate exceeds threshold."""
        efw_count = len(self._efws)
        if efw_count == 0:
            return []

        charge_count = max(len(self._charges), 1)
        if charge_count < self._min_volume:
            if efw_count >= 3:  # Absolute minimum for EFWs
                return self._maybe_alert_efw(efw_count, charge_count)
            return []

        rate = efw_count / charge_count
        if rate >= self._efw_threshold:
            return self._maybe_alert_efw(efw_count, charge_count, rate=rate)

        return []

    def _maybe_alert_efw(
        self, efw_count: int, charge_count: int, rate: float = 0.0
    ) -> List[Alert]:
        now = time.time()
        if self._last_efw_alert_at and (now - self._last_efw_alert_at) < self._alert_cooldown:
            return []
        self._last_efw_alert_at = now

        alert = Alert(
            detector=self.name,
            severity="high",
            title="Early Fraud Warnings Elevated",
            message=(
                f"{efw_count} Stripe Radar early fraud warnings in the past 24 hours "
                f"({rate:.2%} of charges). These predict disputes before they're filed."
            ),
            metadata={
                "efw_count": efw_count,
                "charge_count": charge_count,
                "efw_rate": round(efw_count / max(charge_count, 1), 4),
                "window_seconds": self._window,
            },
        )
        self._log(f"ALERT: {alert.message}")
        return [alert]
