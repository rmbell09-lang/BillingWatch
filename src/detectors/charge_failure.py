"""Charge Failure Spike Detector.

Triggers when charge failure rate exceeds 15% over a rolling 1-hour window.
Listens to: charge.failed, charge.succeeded
"""
import time
from collections import deque
from typing import Any, Dict, List, Optional

from .base import Alert, BaseDetector

# Rolling window: 1 hour in seconds
WINDOW_SECONDS = 3600
FAILURE_THRESHOLD = 0.15  # 15%
MIN_EVENTS = 10  # Need at least 10 events to avoid noise on low-volume accounts


class ChargeFailureDetector(BaseDetector):
    """Detects spike in charge failures over a rolling 1-hour window."""

    name = "charge_failure_spike"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        # Each entry: (timestamp, success: bool)
        self._events: deque = deque()
        self._threshold = self.config.get("failure_threshold", FAILURE_THRESHOLD)
        self._window = self.config.get("window_seconds", WINDOW_SECONDS)
        self._min_events = self.config.get("min_events", MIN_EVENTS)
        self._last_alerted_at: Optional[float] = None
        self._alert_cooldown = self.config.get("alert_cooldown_seconds", 900)  # 15 min

    def _prune(self):
        """Remove events older than the rolling window."""
        cutoff = time.time() - self._window
        while self._events and self._events[0][0] < cutoff:
            self._events.popleft()

    def _failure_rate(self) -> float:
        """Return current failure rate (0.0–1.0) from the rolling window."""
        self._prune()
        if not self._events:
            return 0.0
        failures = sum(1 for _, success in self._events if not success)
        return failures / len(self._events)

    def process_event(self, event: Dict[str, Any]) -> List[Alert]:
        """Handle charge.failed and charge.succeeded events."""
        event_type = event.get("type", "")
        now = time.time()

        if event_type == "charge.succeeded":
            self._events.append((now, True))
        elif event_type == "charge.failed":
            self._events.append((now, False))
        else:
            return []

        self._prune()
        return self._evaluate()

    def check(self) -> List[Alert]:
        """Scheduled check — re-evaluate current window without a new event."""
        self._prune()
        return self._evaluate()

    def _evaluate(self) -> List[Alert]:
        """Check whether an alert should fire."""
        if len(self._events) < self._min_events:
            return []

        rate = self._failure_rate()
        if rate < self._threshold:
            return []

        # Cooldown: don't spam alerts
        now = time.time()
        if self._last_alerted_at and (now - self._last_alerted_at) < self._alert_cooldown:
            return []

        self._last_alerted_at = now
        failures = sum(1 for _, s in self._events if not s)
        total = len(self._events)

        alert = Alert(
            detector=self.name,
            severity="high",
            title="Charge Failure Spike Detected",
            message=(
                f"Charge failure rate is {rate:.1%} ({failures}/{total} charges failed) "
                f"over the past hour — threshold is {self._threshold:.0%}."
            ),
            metadata={
                "failure_rate": round(rate, 4),
                "failures": failures,
                "total": total,
                "window_seconds": self._window,
                "threshold": self._threshold,
            },
        )
        self._log(f"ALERT: {alert.message}")
        return [alert]
