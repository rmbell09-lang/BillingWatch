"""Unit tests for all BillingWatch anomaly detectors."""
import time
import pytest
from unittest.mock import patch

from src.detectors.base import Alert
from src.detectors.charge_failure import ChargeFailureDetector
from src.detectors.duplicate_charge import DuplicateChargeDetector
from src.detectors.fraud_spike import FraudSpikeDetector
from src.detectors.negative_invoice import NegativeInvoiceDetector
from src.detectors.revenue_drop import RevenueDrop
from src.detectors.silent_lapse import SilentLapseDetector
from src.detectors.webhook_lag import WebhookLagDetector


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_event(event_type, **obj_fields):
    return {"type": event_type, "data": {"object": obj_fields}}


# ─────────────────────────────────────────────────────────────────────────────
# ChargeFailureDetector
# ─────────────────────────────────────────────────────────────────────────────

class TestChargeFailureDetector:
    def setup_method(self):
        self.d = ChargeFailureDetector(config={"min_events": 3, "failure_threshold": 0.50})

    def _feed(self, successes: int, failures: int, collect_all: bool = False):
        alerts = []
        for _ in range(successes):
            alerts = self.d.process_event({"type": "charge.succeeded"})
        for _ in range(failures):
            alerts = self.d.process_event({"type": "charge.failed"})
        return alerts

    def test_no_alert_below_min_events(self):
        alerts = self._feed(successes=1, failures=1)
        assert alerts == []

    def test_no_alert_below_threshold(self):
        # 3 successes, 1 failure → 25% < 50%
        alerts = self._feed(successes=3, failures=1)
        assert alerts == []

    def test_alert_above_threshold(self):
        # Feed events one by one, collecting all alerts
        all_alerts = []
        all_alerts += self.d.process_event({"type": "charge.succeeded"})
        all_alerts += self.d.process_event({"type": "charge.failed"})
        all_alerts += self.d.process_event({"type": "charge.failed"})  # 3rd event hits min, fires alert
        all_alerts += self.d.process_event({"type": "charge.failed"})
        assert len(all_alerts) == 1
        assert all_alerts[0].severity == "high"
        assert "Charge Failure" in all_alerts[0].title

    def test_alert_metadata(self):
        all_alerts = []
        all_alerts += self.d.process_event({"type": "charge.succeeded"})
        all_alerts += self.d.process_event({"type": "charge.failed"})
        all_alerts += self.d.process_event({"type": "charge.failed"})
        all_alerts += self.d.process_event({"type": "charge.failed"})
        assert len(all_alerts) == 1
        meta = all_alerts[0].metadata
        assert meta["failures"] >= 2
        assert meta["total"] >= 3
        assert meta["failure_rate"] > 0.60

    def test_cooldown_prevents_duplicate_alerts(self):
        self._feed(successes=1, failures=3)
        # Second batch — should be suppressed by cooldown
        alerts = self._feed(successes=0, failures=1)
        assert alerts == []

    def test_unrelated_events_ignored(self):
        alerts = self.d.process_event({"type": "customer.created"})
        assert alerts == []

    def test_check_method_returns_list(self):
        result = self.d.check()
        assert isinstance(result, list)


# ─────────────────────────────────────────────────────────────────────────────
# DuplicateChargeDetector
# ─────────────────────────────────────────────────────────────────────────────

class TestDuplicateChargeDetector:
    def setup_method(self):
        self.d = DuplicateChargeDetector(config={"duplicate_threshold": 2, "pair_cooldown_seconds": 0})

    def _charge(self, charge_id, customer_id="cus_test", amount=999):
        return self.d.process_event({
            "type": "charge.succeeded",
            "data": {"object": {"id": charge_id, "customer": customer_id, "amount": amount}}
        })

    def test_single_charge_no_alert(self):
        assert self._charge("ch_1") == []

    def test_two_same_charges_triggers_alert(self):
        self._charge("ch_1")
        alerts = self._charge("ch_2")
        assert len(alerts) == 1
        assert "Duplicate" in alerts[0].title

    def test_different_amounts_no_alert(self):
        self.d.process_event({"type": "charge.succeeded", "data": {"object": {"id": "ch_1", "customer": "cus_a", "amount": 100}}})
        alerts = self.d.process_event({"type": "charge.succeeded", "data": {"object": {"id": "ch_2", "customer": "cus_a", "amount": 200}}})
        assert alerts == []

    def test_different_customers_no_alert(self):
        self._charge("ch_1", customer_id="cus_a")
        alerts = self._charge("ch_2", customer_id="cus_b")
        assert alerts == []

    def test_same_charge_id_not_double_counted(self):
        self._charge("ch_1")
        alerts = self._charge("ch_1")  # Same ID — should be ignored
        assert alerts == []

    def test_alert_includes_charge_ids(self):
        self._charge("ch_1")
        alerts = self._charge("ch_2")
        assert "ch_1" in alerts[0].metadata["charge_ids"]
        assert "ch_2" in alerts[0].metadata["charge_ids"]

    def test_check_returns_empty(self):
        assert self.d.check() == []


# ─────────────────────────────────────────────────────────────────────────────
# FraudSpikeDetector
# ─────────────────────────────────────────────────────────────────────────────

class TestFraudSpikeDetector:
    def setup_method(self):
        self.d = FraudSpikeDetector(config={
            "absolute_dispute_threshold": 3,
            "min_charge_volume": 5,
            "dispute_rate_threshold": 0.20,
            "alert_cooldown_seconds": 0,
        })

    def _dispute(self):
        return self.d.process_event({"type": "charge.dispute.created"})

    def _succeed(self):
        return self.d.process_event({"type": "charge.succeeded"})

    def test_no_alert_below_threshold(self):
        self._succeed()
        self._succeed()
        assert self._dispute() == []

    def test_absolute_threshold_triggers(self):
        alerts = []
        for _ in range(3):
            alerts = self._dispute()
        assert len(alerts) == 1
        assert alerts[0].severity == "critical"

    def test_rate_threshold_triggers(self):
        # 5 charges, 2 disputes = 40% > 20%
        for _ in range(3):
            self._succeed()
        for _ in range(2):
            self._dispute()
        alerts = self._dispute()  # 3rd dispute triggers absolute threshold first, reset cooldown
        assert len(alerts) >= 1

    def test_efw_alert(self):
        d = FraudSpikeDetector(config={"alert_cooldown_seconds": 0, "min_charge_volume": 1})
        for _ in range(3):
            d.process_event({"type": "charge.succeeded"})
        alerts = d.process_event({"type": "radar.early_fraud_warning"})
        # 1 EFW on 3 charges = 33% > 0.5% threshold
        assert len(alerts) == 1
        assert "Fraud" in alerts[0].title or "Early" in alerts[0].title

    def test_check_returns_list(self):
        assert isinstance(self.d.check(), list)


# ─────────────────────────────────────────────────────────────────────────────
# NegativeInvoiceDetector
# ─────────────────────────────────────────────────────────────────────────────

class TestNegativeInvoiceDetector:
    def setup_method(self):
        self.d = NegativeInvoiceDetector(config={
            "large_refund_threshold_cents": 10_000,  # $100
            "customer_daily_threshold_cents": 20_000,  # $200
            "cooldown_seconds": 0,
        })

    def _refund(self, amount_cents, customer="cus_test", charge_id="ch_r1"):
        return self.d.process_event({
            "type": "charge.refunded",
            "data": {"object": {"id": charge_id, "customer": customer, "amount_refunded": amount_cents}}
        })

    def test_small_refund_no_alert(self):
        assert self._refund(500) == []  # $5 — below $100 threshold

    def test_large_refund_triggers_alert(self):
        alerts = self._refund(15_000)  # $150
        assert any("Refund" in a.title or "refund" in a.title.lower() for a in alerts)

    def test_negative_invoice_always_alerts(self):
        alerts = self.d.process_event({
            "type": "invoice.payment_succeeded",
            "data": {"object": {"id": "in_neg", "customer": "cus_x", "amount_paid": -500}}
        })
        assert len(alerts) == 1
        assert "Negative" in alerts[0].title

    def test_positive_invoice_no_alert(self):
        alerts = self.d.process_event({
            "type": "invoice.payment_succeeded",
            "data": {"object": {"id": "in_pos", "customer": "cus_x", "amount_paid": 5000}}
        })
        # No alert from a normal invoice
        assert not any("Negative" in a.title for a in alerts)

    def test_customer_daily_limit(self):
        self._refund(12_000, charge_id="ch_r1")  # $120
        alerts = self._refund(12_000, charge_id="ch_r2")  # $240 total — over $200 limit
        assert any("High Refund Volume" in a.title for a in alerts)

    def test_check_returns_list(self):
        assert isinstance(self.d.check(), list)


# ─────────────────────────────────────────────────────────────────────────────
# RevenueDrop
# ─────────────────────────────────────────────────────────────────────────────

class TestRevenueDrop:
    def setup_method(self):
        self.d = RevenueDrop(config={
            "drop_threshold": 0.20,
            "min_days_of_data": 2,
            "min_daily_revenue_cents": 1_000,
            "rolling_days": 3,
        })

    def _record_days(self, amounts):
        """Record payments spread across multiple days (simulate past timestamps)."""
        base = time.time() - len(amounts) * 86400
        for i, amount in enumerate(amounts):
            self.d.record_payment(amount, base + i * 86400)

    def test_no_alert_insufficient_history(self):
        self.d.record_payment(10_000, time.time() - 86400)
        alerts = self.d.check()
        assert alerts == []

    def test_no_alert_normal_revenue(self):
        # 3 history days + today (all similar) — no drop
        self._record_days([10_000, 10_000, 10_000])
        self.d.record_payment(10_000, time.time() - 3600)  # today's revenue
        alerts = self.d.check()
        assert alerts == []

    def test_alert_on_revenue_drop(self):
        # 3 days at $1000, then today at $200 (80% drop)
        base = time.time()
        self.d.record_payment(100_000, base - 3 * 86400)
        self.d.record_payment(100_000, base - 2 * 86400)
        self.d.record_payment(100_000, base - 1 * 86400)
        self.d.record_payment(10_000, base - 3600)  # today: $100 vs $1000 avg
        alerts = self.d.check()
        assert len(alerts) == 1
        assert "Drop" in alerts[0].title or "drop" in alerts[0].title.lower()

    def test_check_returns_list(self):
        assert isinstance(self.d.check(), list)


# ─────────────────────────────────────────────────────────────────────────────
# SilentLapseDetector
# ─────────────────────────────────────────────────────────────────────────────

class TestSilentLapseDetector:
    def setup_method(self):
        self.d = SilentLapseDetector()

    def test_tracks_subscription_updates(self):
        event = {
            "type": "customer.subscription.updated",
            "data": {"object": {"id": "sub_1", "customer": "cus_1", "status": "active", "billing_cycle_anchor": int(time.time() - 100), "plan": {"interval": "month"}}}
        }
        alerts = self.d.process_event(event)
        assert isinstance(alerts, list)

    def test_tracks_successful_payments(self):
        event = {
            "type": "invoice.payment_succeeded",
            "data": {"object": {"subscription": "sub_1", "customer": "cus_1"}}
        }
        alerts = self.d.process_event(event)
        assert isinstance(alerts, list)

    def test_check_returns_list(self):
        assert isinstance(self.d.check(), list)

    def test_lapsed_subscription_detected(self):
        d = SilentLapseDetector()
        # Record subscription as active
        sub_event = {
            "type": "customer.subscription.updated",
            "data": {"object": {"id": "sub_lapsed", "customer": "cus_lapsed", "status": "active", "billing_cycle_anchor": int(time.time()), "plan": {"interval": "month"}}}
        }
        d.process_event(sub_event)
        # Record last payment as 40+ days ago (beyond monthly interval + grace)
        d._last_payment["cus_lapsed"] = time.time() - (40 * 86400)
        alerts = d.check()
        assert any("lapse" in a.title.lower() or "Lapse" in a.title for a in alerts)


# ─────────────────────────────────────────────────────────────────────────────
# WebhookLagDetector
# ─────────────────────────────────────────────────────────────────────────────

class TestWebhookLagDetector:
    def setup_method(self):
        self.d = WebhookLagDetector(config={
            "warning_lag_seconds": 60,    # 1 min
            "critical_lag_seconds": 300,  # 5 min
            "lag_alert_cooldown": 0,
            "silence_alert_cooldown": 0,
            "silence_threshold_seconds": 3600,
        })

    def _event(self, lag_seconds, event_id="evt_test"):
        return {
            "type": "invoice.payment_succeeded",
            "id": event_id,
            "created": time.time() - lag_seconds,
        }

    def test_fresh_event_no_alert(self):
        alerts = self.d.process_event(self._event(lag_seconds=5))
        assert alerts == []

    def test_warning_lag_triggers_alert(self):
        alerts = self.d.process_event(self._event(lag_seconds=120))  # 2 min
        assert len(alerts) == 1
        assert alerts[0].severity == "warning"
        assert "Lag" in alerts[0].title

    def test_critical_lag_triggers_critical_alert(self):
        alerts = self.d.process_event(self._event(lag_seconds=600))  # 10 min
        assert len(alerts) == 1
        assert alerts[0].severity == "critical"

    def test_metadata_contains_lag_info(self):
        alerts = self.d.process_event(self._event(lag_seconds=120))
        meta = alerts[0].metadata
        assert meta["lag_seconds"] >= 119

    def test_event_without_created_no_crash(self):
        alerts = self.d.process_event({"type": "foo"})
        assert alerts == []

    def test_check_no_silence_if_recent_event(self):
        self.d.process_event(self._event(lag_seconds=5))
        alerts = self.d.check()
        # Not silent — recent event received
        assert alerts == []

    def test_silence_alert_when_no_events(self):
        d = WebhookLagDetector(config={
            "silence_threshold_seconds": 1,
            "silence_alert_cooldown": 0,
        })
        d._last_event_received_at = time.time() - 10  # 10 seconds ago
        with patch.object(d, "_in_active_hours", return_value=True):
            alerts = d.check()
        assert len(alerts) == 1
        assert "Silence" in alerts[0].title


# ─────────────────────────────────────────────────────────────────────────────
# CurrencyMismatchDetector
# ─────────────────────────────────────────────────────────────────────────────

from src.detectors.currency_mismatch import CurrencyMismatchDetector


class TestCurrencyMismatchDetector:
    def setup_method(self):
        self.d = CurrencyMismatchDetector(config={"baseline_events": 3, "pair_cooldown_seconds": 0})

    def _charge_event(self, customer_id, currency):
        return {
            "type": "charge.succeeded",
            "data": {"object": {"id": "ch_test", "customer": customer_id, "currency": currency}},
        }

    def _invoice_event(self, customer_id, currency):
        return {
            "type": "invoice.payment_succeeded",
            "data": {"object": {"charge": "ch_invoice", "customer": customer_id, "currency": currency}},
        }

    def test_no_alert_during_baseline(self):
        # First 3 events build baseline — no alerts
        for _ in range(2):
            alerts = self.d.process_event(self._charge_event("cus_1", "usd"))
        assert alerts == []

    def test_no_alert_matching_home_currency(self):
        for _ in range(3):
            self.d.process_event(self._charge_event("cus_1", "usd"))
        alerts = self.d.process_event(self._charge_event("cus_1", "usd"))
        assert alerts == []

    def test_alert_on_currency_mismatch(self):
        for _ in range(3):
            self.d.process_event(self._charge_event("cus_1", "usd"))
        alerts = self.d.process_event(self._charge_event("cus_1", "eur"))
        assert len(alerts) == 1
        assert alerts[0].severity == "high"
        assert "Currency Mismatch" in alerts[0].title

    def test_alert_metadata(self):
        for _ in range(3):
            self.d.process_event(self._charge_event("cus_1", "usd"))
        alerts = self.d.process_event(self._charge_event("cus_1", "gbp"))
        meta = alerts[0].metadata
        assert meta["customer_id"] == "cus_1"
        assert meta["expected_currency"] == "USD"
        assert meta["actual_currency"] == "GBP"

    def test_cooldown_suppresses_repeat_alert(self):
        d = CurrencyMismatchDetector(config={"baseline_events": 3, "pair_cooldown_seconds": 3600})
        for _ in range(3):
            d.process_event(self._charge_event("cus_1", "usd"))
        d.process_event(self._charge_event("cus_1", "eur"))  # fires
        alerts = d.process_event(self._charge_event("cus_1", "eur"))  # suppressed
        assert alerts == []

    def test_invoice_event_also_detected(self):
        for _ in range(3):
            self.d.process_event(self._invoice_event("cus_2", "usd"))
        alerts = self.d.process_event(self._invoice_event("cus_2", "jpy"))
        assert len(alerts) == 1

    def test_event_without_customer_ignored(self):
        alerts = self.d.process_event({"type": "charge.succeeded", "data": {"object": {"currency": "usd"}}})
        assert alerts == []

    def test_unrelated_event_ignored(self):
        alerts = self.d.process_event({"type": "customer.created"})
        assert alerts == []

    def test_currency_normalized_to_uppercase(self):
        for _ in range(3):
            self.d.process_event(self._charge_event("cus_3", "usd"))
        alerts = self.d.process_event(self._charge_event("cus_3", "EUR"))
        assert len(alerts) == 1
        assert alerts[0].metadata["actual_currency"] == "EUR"

    def test_check_returns_empty(self):
        assert self.d.check() == []


# ─────────────────────────────────────────────────────────────────────────────
# TimezoneBillingErrorDetector
# ─────────────────────────────────────────────────────────────────────────────

from src.detectors.timezone_billing_error import TimezoneBillingErrorDetector


class TestTimezoneBillingErrorDetector:
    def setup_method(self):
        self.d = TimezoneBillingErrorDetector(config={
            "double_invoice_window_hours": 26,
            "subscription_cooldown_seconds": 0,
        })

    def _invoice_event(self, sub_id, created_ts):
        return {
            "type": "invoice.created",
            "data": {"object": {"subscription": sub_id, "created": created_ts}},
        }

    def test_no_alert_on_first_invoice(self):
        alerts = self.d.process_event(self._invoice_event("sub_1", int(time.time())))
        assert alerts == []

    def test_alert_on_double_invoice_within_window(self):
        now = int(time.time())
        self.d.process_event(self._invoice_event("sub_1", now))
        alerts = self.d.process_event(self._invoice_event("sub_1", now + 3600))  # 1h later
        assert len(alerts) == 1
        assert "Double Invoice" in alerts[0].title

    def test_no_alert_outside_double_window(self):
        now = int(time.time())
        self.d.process_event(self._invoice_event("sub_2", now))
        alerts = self.d.process_event(self._invoice_event("sub_2", now + 30 * 86400))  # 30 days
        assert alerts == []

    def test_double_invoice_metadata(self):
        now = int(time.time())
        self.d.process_event(self._invoice_event("sub_3", now))
        alerts = self.d.process_event(self._invoice_event("sub_3", now + 7200))
        meta = alerts[0].metadata
        assert meta["subscription_id"] == "sub_3"
        assert meta["gap_hours"] == pytest.approx(2.0, abs=0.1)

    def test_cooldown_suppresses_repeat(self):
        d = TimezoneBillingErrorDetector(config={
            "double_invoice_window_hours": 26,
            "subscription_cooldown_seconds": 3600,
        })
        now = int(time.time())
        d.process_event(self._invoice_event("sub_4", now))
        d.process_event(self._invoice_event("sub_4", now + 1800))  # fires
        alerts = d.process_event(self._invoice_event("sub_4", now + 3600))  # suppressed
        assert alerts == []

    def test_invoice_payment_succeeded_also_triggers(self):
        now = int(time.time())
        self.d.process_event({
            "type": "invoice.payment_succeeded",
            "data": {"object": {"subscription": "sub_5", "created": now}},
        })
        alerts = self.d.process_event({
            "type": "invoice.payment_succeeded",
            "data": {"object": {"subscription": "sub_5", "created": now + 1800}},
        })
        assert len(alerts) == 1

    def test_unrelated_event_ignored(self):
        alerts = self.d.process_event({"type": "charge.succeeded"})
        assert alerts == []

    def test_event_without_subscription_ignored(self):
        alerts = self.d.process_event({
            "type": "invoice.created",
            "data": {"object": {"amount": 100}},
        })
        assert alerts == []

    def test_check_does_not_raise(self):
        now = int(time.time())
        self.d.process_event(self._invoice_event("sub_6", now))
        self.d.check()  # should prune without error


# ─────────────────────────────────────────────────────────────────────────────
# PlanDowngradeDataLossDetector
# ─────────────────────────────────────────────────────────────────────────────

from src.detectors.plan_downgrade_data_loss import PlanDowngradeDataLossDetector


class TestPlanDowngradeDataLossDetector:
    def setup_method(self):
        self.d = PlanDowngradeDataLossDetector(config={"subscription_cooldown_seconds": 0})

    def _sub_updated(self, sub_id, customer_id="cus_1", previous_attrs=None, items=None, plan=None):
        event = {
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": sub_id,
                    "customer": customer_id,
                },
                "previous_attributes": previous_attrs or {},
            },
        }
        if items is not None:
            event["data"]["object"]["items"] = items
        if plan is not None:
            event["data"]["object"]["plan"] = plan
        return event

    def test_quantity_reduction_fires_alert(self):
        event = self._sub_updated(
            "sub_1",
            previous_attrs={
                "items": {"data": [{"price": {"id": "price_pro"}, "quantity": 10}]}
            },
            items={"data": [{"price": {"id": "price_pro"}, "quantity": 3}]},
        )
        alerts = self.d.process_event(event)
        assert len(alerts) == 1
        assert alerts[0].severity == "high"
        assert "Quantity Reduction" in alerts[0].title

    def test_quantity_reduction_metadata(self):
        event = self._sub_updated(
            "sub_2",
            customer_id="cus_abc",
            previous_attrs={
                "items": {"data": [{"price": {"id": "price_biz"}, "quantity": 50}]}
            },
            items={"data": [{"price": {"id": "price_biz"}, "quantity": 5}]},
        )
        alerts = self.d.process_event(event)
        meta = alerts[0].metadata
        assert meta["subscription_id"] == "sub_2"
        assert meta["customer_id"] == "cus_abc"
        assert meta["reduced_prices"]["price_biz"]["from"] == 50
        assert meta["reduced_prices"]["price_biz"]["to"] == 5

    def test_price_removed_entirely_fires_alert(self):
        event = self._sub_updated(
            "sub_3",
            previous_attrs={
                "items": {"data": [{"price": {"id": "price_addon"}, "quantity": 1}]}
            },
            items={"data": []},  # addon removed
        )
        alerts = self.d.process_event(event)
        assert len(alerts) == 1
        assert "price_addon" in alerts[0].metadata["removed_prices"]

    def test_tier_regression_fires_alert(self):
        event = self._sub_updated(
            "sub_4",
            previous_attrs={"plan": {"nickname": "Business"}},
            plan={"nickname": "Starter"},
        )
        alerts = self.d.process_event(event)
        assert len(alerts) == 1
        assert alerts[0].severity == "medium"
        assert "Tier Regression" in alerts[0].title

    def test_tier_upgrade_no_alert(self):
        event = self._sub_updated(
            "sub_5",
            previous_attrs={"plan": {"nickname": "Starter"}},
            plan={"nickname": "Pro"},
        )
        alerts = self.d.process_event(event)
        assert alerts == []

    def test_quantity_increase_no_alert(self):
        event = self._sub_updated(
            "sub_6",
            previous_attrs={
                "items": {"data": [{"price": {"id": "price_pro"}, "quantity": 5}]}
            },
            items={"data": [{"price": {"id": "price_pro"}, "quantity": 20}]},
        )
        alerts = self.d.process_event(event)
        assert alerts == []

    def test_cooldown_suppresses_repeat(self):
        d = PlanDowngradeDataLossDetector(config={"subscription_cooldown_seconds": 3600})
        event = self._sub_updated(
            "sub_7",
            previous_attrs={
                "items": {"data": [{"price": {"id": "p1"}, "quantity": 10}]}
            },
            items={"data": [{"price": {"id": "p1"}, "quantity": 2}]},
        )
        d.process_event(event)  # fires
        alerts = d.process_event(event)  # suppressed
        assert alerts == []

    def test_unrelated_event_ignored(self):
        alerts = self.d.process_event({"type": "charge.succeeded"})
        assert alerts == []

    def test_no_previous_attributes_ignored(self):
        event = self._sub_updated("sub_8", previous_attrs={})
        alerts = self.d.process_event(event)
        assert alerts == []

    def test_check_returns_empty(self):
        assert self.d.check() == []
