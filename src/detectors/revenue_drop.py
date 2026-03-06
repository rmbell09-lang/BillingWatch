"""Revenue Anomaly (Sudden Drop) Detector.

Triggers when daily MRR movement is >15% below the 7-day rolling average.
Listens to: invoice.payment_succeeded

Scheduled check runs daily (or every few hours) to compare today's revenue
against the 7-day rolling average.
"""
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import Alert, BaseDetector

DROP_THRESHOLD = 0.15       # 15% below rolling average triggers alert
ROLLING_DAYS = 7
MIN_DAYS_OF_DATA = 3        # Need at least 3 days before alerting (avoid early noise)
MIN_DAILY_REVENUE = 100     # Don't alert on tiny revenue amounts (< $100/day)


def _day_bucket(ts: float) -> str:
    """Return YYYY-MM-DD string for a unix timestamp (UTC)."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


class RevenueDrop:
    """Tracks daily revenue and detects sudden drops."""

    name = "revenue_anomaly_drop"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        # day_bucket → total revenue in cents
        self._daily_revenue: Dict[str, int] = defaultdict(int)
        self._threshold = self.config.get("drop_threshold", DROP_THRESHOLD)
        self._rolling_days = self.config.get("rolling_days", ROLLING_DAYS)
        self._min_days = self.config.get("min_days_of_data", MIN_DAYS_OF_DATA)
        self._min_daily_revenue = self.config.get("min_daily_revenue_cents", MIN_DAILY_REVENUE * 100)
        self._last_alerted_day: Optional[str] = None

    def record_payment(self, amount_cents: int, paid_at: float):
        """Record a successful payment at a given timestamp."""
        day = _day_bucket(paid_at)
        self._daily_revenue[day] += amount_cents

    def check(self) -> List[Alert]:
        """Check if today's revenue is anomalously low vs 7-day average."""
        today = _day_bucket(time.time())
        # Only alert once per day
        if self._last_alerted_day == today:
            return []

        sorted_days = sorted(self._daily_revenue.keys())
        # Exclude today from rolling average (today may be incomplete)
        history_days = [d for d in sorted_days if d < today]

        if len(history_days) < self._min_days:
            return []  # Not enough data yet

        # Use the last N days of history for rolling average
        recent_days = history_days[-self._rolling_days:]
        avg_revenue = sum(self._daily_revenue[d] for d in recent_days) / len(recent_days)

        if avg_revenue < self._min_daily_revenue:
            return []  # Too small to care about

        today_revenue = self._daily_revenue.get(today, 0)
        drop_pct = (avg_revenue - today_revenue) / avg_revenue if avg_revenue > 0 else 0

        if drop_pct < self._threshold:
            return []

        self._last_alerted_day = today
        alert = Alert(
            detector=self.name,
            severity="critical" if drop_pct > 0.30 else "high",
            title="Revenue Anomaly: Sudden Drop Detected",
            message=(
                f"Today's revenue is ${today_revenue/100:.2f}, which is "
                f"{drop_pct:.1%} below the {len(recent_days)}-day rolling average "
                f"of ${avg_revenue/100:.2f}/day."
            ),
            metadata={
                "today": today,
                "today_revenue_cents": today_revenue,
                "rolling_avg_cents": round(avg_revenue, 2),
                "drop_pct": round(drop_pct, 4),
                "threshold": self._threshold,
                "rolling_days": len(recent_days),
            },
        )
        return [alert]


class RevenueDropDetector(RevenueDrop, BaseDetector):
    """Full detector integrating BaseDetector protocol."""

    name = "revenue_anomaly_drop"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        BaseDetector.__init__(self, config)
        RevenueDrop.__init__(self, config)

    def process_event(self, event: Dict[str, Any]) -> List[Alert]:
        if event.get("type") != "invoice.payment_succeeded":
            return []
        obj = event.get("data", {}).get("object", {})
        amount = obj.get("amount_paid", 0)
        paid_at_ts = obj.get("status_transitions", {}).get("paid_at") or time.time()
        self.record_payment(amount, float(paid_at_ts))
        return []  # Revenue checks run on schedule, not per-event

    def check(self) -> List[Alert]:
        return RevenueDrop.check(self)
