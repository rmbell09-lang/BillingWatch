"""Plan Downgrade Data Loss Detector.

Detects when a customer downgrades their subscription to a plan with lower
limits — signaling risk of data loss, feature lockout, or overage errors if
the customer is already using resources above the new plan's caps.

Common real-world scenarios:
  - Customer on "Pro" (100 seats) downgrades to "Starter" (5 seats) while
    actively using 80 seats → 75 users lose access immediately.
  - Customer on "Business" (unlimited storage) downgrades to "Hobby" (5 GB)
    while storing 40 GB → data is silently truncated or inaccessible.
  - Customer downgrades mid-cycle after feature-flag access has already been
    granted → audit trail gap.

Listens to:
  - customer.subscription.updated

Detection logic:
  - Compares previous_attributes.items with the updated items list.
  - A downgrade is detected when:
    (a) A plan item is removed entirely, OR
    (b) A plan item's quantity decreases (seat/usage reduction), OR
    (c) Price tier metadata indicates a move to a lower plan tier.
  - Detects well-known SaaS tier naming conventions (starter < basic < pro
    < business < enterprise) and fires when direction is downward.
"""
import time
from typing import Any, Dict, List, Optional, Tuple

from .base import Alert, BaseDetector

# Canonical tier ordering (lower index = lower tier)
TIER_ORDER = [
    "free", "starter", "basic", "hobby", "personal",
    "standard", "growth", "plus", "pro", "professional",
    "business", "team", "scale", "enterprise", "ultimate",
]

# Cooldown per subscription between downgrade alerts (2 hours)
SUBSCRIPTION_COOLDOWN_SECONDS = 7200


def _tier_rank(name: str) -> int:
    """Return tier rank from TIER_ORDER, or -1 if unknown."""
    name_lower = name.lower()
    for i, tier in enumerate(TIER_ORDER):
        if tier in name_lower:
            return i
    return -1


class PlanDowngradeDataLossDetector(BaseDetector):
    """Detects subscription plan downgrades that may cause data loss or access removal."""

    name = "plan_downgrade_data_loss"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._cooldown = self.config.get(
            "subscription_cooldown_seconds", SUBSCRIPTION_COOLDOWN_SECONDS
        )
        # subscription_id → last alert timestamp
        self._last_alerted: Dict[str, float] = {}

    def _is_cooldown_active(self, sub_id: str) -> bool:
        last = self._last_alerted.get(sub_id)
        return bool(last and (time.time() - last) < self._cooldown)

    def _record_alert(self, sub_id: str):
        self._last_alerted[sub_id] = time.time()

    def process_event(self, event: Dict[str, Any]) -> List[Alert]:
        if event.get("type") != "customer.subscription.updated":
            return []

        obj = event.get("data", {}).get("object", {})
        previous = event.get("data", {}).get("previous_attributes", {})

        sub_id = obj.get("id", "")
        customer_id = obj.get("customer", "unknown")

        if not sub_id or not previous:
            return []

        alerts: List[Alert] = []

        # ── Check 1: Quantity reduction (seat/license decrease) ───────────
        prev_items = previous.get("items", {})
        if prev_items:
            prev_data = prev_items.get("data", [])
            curr_data = obj.get("items", {}).get("data", [])

            # Build maps: price_id → quantity
            prev_map: Dict[str, int] = {}
            for item in prev_data:
                pid = item.get("price", {}).get("id") or item.get("price", "")
                qty = item.get("quantity") or 1
                prev_map[pid] = qty

            curr_map: Dict[str, int] = {}
            for item in curr_data:
                pid = item.get("price", {}).get("id") or item.get("price", "")
                qty = item.get("quantity") or 1
                curr_map[pid] = qty

            removed_prices = set(prev_map) - set(curr_map)
            reduced_prices = {
                pid: (prev_map[pid], curr_map[pid])
                for pid in set(prev_map) & set(curr_map)
                if curr_map[pid] < prev_map[pid]
            }

            if (removed_prices or reduced_prices) and not self._is_cooldown_active(sub_id):
                self._record_alert(sub_id)
                details_parts = []
                for pid in removed_prices:
                    details_parts.append(f"price {pid} removed entirely")
                for pid, (old, new) in reduced_prices.items():
                    details_parts.append(f"price {pid} qty {old}→{new} (−{old - new} seats/units)")
                details = "; ".join(details_parts)

                alert = Alert(
                    detector=self.name,
                    severity="high",
                    title="Plan Downgrade: Quantity Reduction Detected",
                    message=(
                        f"Subscription {sub_id} (customer {customer_id}) has been "
                        f"downgraded with reduced plan items: {details}. "
                        f"Customers currently over the new limits risk immediate data loss or access removal."
                    ),
                    metadata={
                        "subscription_id": sub_id,
                        "customer_id": customer_id,
                        "removed_prices": list(removed_prices),
                        "reduced_prices": {
                            pid: {"from": old, "to": new}
                            for pid, (old, new) in reduced_prices.items()
                        },
                    },
                )
                self._log(f"ALERT: {alert.message}")
                alerts.append(alert)
                return alerts

        # ── Check 2: Plan tier name regression ─────────────────────────────
        # Look for plan nickname / product name changes indicating a tier drop
        prev_plan = previous.get("plan", {}) or {}
        curr_plan = obj.get("plan", {}) or {}

        prev_nickname = (
            prev_plan.get("nickname")
            or prev_plan.get("name")
            or ""
        )
        curr_nickname = (
            curr_plan.get("nickname")
            or curr_plan.get("name")
            or ""
        )

        if prev_nickname and curr_nickname and prev_nickname != curr_nickname:
            prev_rank = _tier_rank(prev_nickname)
            curr_rank = _tier_rank(curr_nickname)

            if prev_rank > curr_rank >= 0 and not self._is_cooldown_active(sub_id):
                self._record_alert(sub_id)
                alert = Alert(
                    detector=self.name,
                    severity="medium",
                    title="Plan Downgrade: Tier Regression Detected",
                    message=(
                        f"Subscription {sub_id} (customer {customer_id}) moved from "
                        f'"{prev_nickname}" to "{curr_nickname}" — a lower plan tier. '
                        f"If the customer is using features or resources above the new "
                        f"plan's limits, data loss or lockout may occur."
                    ),
                    metadata={
                        "subscription_id": sub_id,
                        "customer_id": customer_id,
                        "previous_plan": prev_nickname,
                        "current_plan": curr_nickname,
                        "previous_tier_rank": prev_rank,
                        "current_tier_rank": curr_rank,
                    },
                )
                self._log(f"ALERT: {alert.message}")
                alerts.append(alert)

        return alerts

    def check(self) -> List[Alert]:
        """No scheduled check needed — purely event-driven."""
        return []
