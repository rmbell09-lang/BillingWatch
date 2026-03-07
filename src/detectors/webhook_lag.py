"""Webhook Lag Detector.

Detects when Stripe webhook events are being delivered with significant delay,
or when events stop arriving entirely (dead webhook endpoint).

Two detection modes:
  1. Event-level lag: Stripe sends a created timestamp in the event payload.
     If (time.time() - event.created) > threshold, the event is stale.
  2. Heartbeat gap: If no event arrives within a configurable window during
     expected business hours, something may have broken (endpoint down, webhook
     disabled, network issue).

Listens to: ALL events (uses created timestamp on every incoming event).
Scheduled check: Detects prolonged silence (heartbeat gap).
"""
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import Alert, BaseDetector

# Lag thresholds (seconds)
WARNING_LAG_SECONDS = 300    # 5 min — unusual but possibly OK
CRITICAL_LAG_SECONDS = 1800  # 30 min — definitely a problem

# Heartbeat gap: alert if no event received in this window during active hours
SILENCE_THRESHOLD_SECONDS = 3600  # 1 hour of silence is suspicious

# Active hours (UTC, 24h) — only check silence during likely-active periods
ACTIVE_HOURS_UTC_START = 12  # 8 AM ET
ACTIVE_HOURS_UTC_END = 4     # midnight ET (next day)

# Cooldowns
LAG_ALERT_COOLDOWN = 900    # 15 min between lag alerts
SILENCE_ALERT_COOLDOWN = 3600  # 1 hr between silence alerts

# Rolling window for lag stats
STATS_WINDOW_SECONDS = 3600


class WebhookLagDetector(BaseDetector):
    """Detects delayed or missing webhook delivery from Stripe."""

    name = "webhook_lag"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._warning_lag = self.config.get("warning_lag_seconds", WARNING_LAG_SECONDS)
        self._critical_lag = self.config.get("critical_lag_seconds", CRITICAL_LAG_SECONDS)
        self._silence_threshold = self.config.get("silence_threshold_seconds", SILENCE_THRESHOLD_SECONDS)
        self._lag_cooldown = self.config.get("lag_alert_cooldown", LAG_ALERT_COOLDOWN)
        self._silence_cooldown = self.config.get("silence_alert_cooldown", SILENCE_ALERT_COOLDOWN)

        # Tracking
        self._last_event_received_at: Optional[float] = None
        self._last_lag_alert_at: Optional[float] = None
        self._last_silence_alert_at: Optional[float] = None

        # Rolling lag samples: (received_at, lag_seconds)
        self._lag_samples: deque = deque()

    def _prune_samples(self):
        cutoff = time.time() - STATS_WINDOW_SECONDS
        while self._lag_samples and self._lag_samples[0][0] < cutoff:
            self._lag_samples.popleft()

    def _in_active_hours(self) -> bool:
        """Return True if current UTC time is within expected active hours."""
        hour_utc = datetime.now(timezone.utc).hour
        # Active hours wrap midnight: 12 UTC → 04 UTC next day
        if ACTIVE_HOURS_UTC_START > ACTIVE_HOURS_UTC_END:
            return hour_utc >= ACTIVE_HOURS_UTC_START or hour_utc < ACTIVE_HOURS_UTC_END
        return ACTIVE_HOURS_UTC_START <= hour_utc < ACTIVE_HOURS_UTC_END

    def process_event(self, event: Dict[str, Any]) -> List[Alert]:
        """Process any incoming Stripe event — measure delivery lag."""
        now = time.time()
        self._last_event_received_at = now

        # Extract Stripe's event creation timestamp
        stripe_created = event.get("created")
        if not isinstance(stripe_created, (int, float)):
            return []  # Not a standard Stripe event shape

        lag_seconds = now - float(stripe_created)

        # Record the sample
        self._lag_samples.append((now, lag_seconds))
        self._prune_samples()

        # Only alert on significant lag
        if lag_seconds < self._warning_lag:
            return []

        severity = "critical" if lag_seconds >= self._critical_lag else "warning"
        return self._maybe_alert_lag(lag_seconds, severity, event)

    def check(self) -> List[Alert]:
        """Scheduled check — detect prolonged silence during active hours."""
        alerts: List[Alert] = []

        # Silence check
        if self._in_active_hours() and self._last_event_received_at is not None:
            silence = time.time() - self._last_event_received_at
            if silence >= self._silence_threshold:
                alerts.extend(self._maybe_alert_silence(silence))

        return alerts

    def _maybe_alert_lag(
        self, lag_seconds: float, severity: str, event: Dict[str, Any]
    ) -> List[Alert]:
        now = time.time()
        if self._last_lag_alert_at and (now - self._last_lag_alert_at) < self._lag_cooldown:
            return []
        self._last_lag_alert_at = now

        self._prune_samples()
        samples = [s for _, s in self._lag_samples]
        avg_lag = sum(samples) / len(samples) if samples else lag_seconds
        max_lag = max(samples) if samples else lag_seconds

        lag_str = self._format_duration(lag_seconds)
        avg_str = self._format_duration(avg_lag)
        event_type = event.get("type", "unknown")
        event_id = event.get("id", "unknown")

        alert = Alert(
            detector=self.name,
            severity=severity,
            title=f"Webhook Delivery Lag: {lag_str}",
            message=(
                f"Event `{event_type}` ({event_id}) arrived {lag_str} after it was created on Stripe. "
                f"Avg lag over last hour: {avg_str}. "
                + (
                    "This is critical — webhooks may be backed up or your endpoint was unreachable."
                    if severity == "critical"
                    else "Webhooks may be delayed — check endpoint health and Stripe dashboard."
                )
            ),
            metadata={
                "event_type": event_type,
                "event_id": event_id,
                "lag_seconds": round(lag_seconds, 1),
                "avg_lag_seconds": round(avg_lag, 1),
                "max_lag_seconds": round(max_lag, 1),
                "sample_count": len(samples),
                "threshold_warning": self._warning_lag,
                "threshold_critical": self._critical_lag,
            },
        )
        self._log(f"ALERT [{severity.upper()}]: {alert.message}")
        return [alert]

    def _maybe_alert_silence(self, silence_seconds: float) -> List[Alert]:
        now = time.time()
        if self._last_silence_alert_at and (now - self._last_silence_alert_at) < self._silence_cooldown:
            return []
        self._last_silence_alert_at = now

        silence_str = self._format_duration(silence_seconds)
        last_seen = (
            datetime.fromtimestamp(self._last_event_received_at, tz=timezone.utc).strftime("%H:%M UTC")
            if self._last_event_received_at
            else "never"
        )

        alert = Alert(
            detector=self.name,
            severity="high",
            title=f"Webhook Silence: No Events for {silence_str}",
            message=(
                f"No Stripe webhook events received for {silence_str} during active hours. "
                f"Last event was at {last_seen}. "
                f"Possible causes: webhook endpoint down, Stripe webhook disabled, network issue, or zero transactions."
            ),
            metadata={
                "silence_seconds": round(silence_seconds, 0),
                "last_event_at": self._last_event_received_at,
                "threshold_seconds": self._silence_threshold,
            },
        )
        self._log(f"ALERT: {alert.message}")
        return [alert]

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Human-readable duration string."""
        if seconds < 60:
            return f"{int(seconds)}s"
        if seconds < 3600:
            return f"{int(seconds // 60)}m {int(seconds % 60)}s"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"
