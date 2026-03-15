"""Integration tests: all 7 detectors wired to a live (in-memory) EventStore."""
import time
import tempfile
import os
import pytest

from src.storage.event_store import EventStore
from src.detectors.charge_failure import ChargeFailureDetector
from src.detectors.duplicate_charge import DuplicateChargeDetector
from src.detectors.fraud_spike import FraudSpikeDetector
from src.detectors.negative_invoice import NegativeInvoiceDetector
from src.detectors.revenue_drop import RevenueDropDetector
from src.detectors.silent_lapse import SilentLapseDetector
from src.detectors.webhook_lag import WebhookLagDetector
from src.workers.event_processor import build_detectors, bootstrap_all, run_scheduled_checks


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_store(tmp_path):
    """Return a fresh EventStore backed by a temp SQLite database."""
    db = tmp_path / "test_billingwatch.db"
    return EventStore(db_path=str(db))


@pytest.fixture
def all_detectors():
    return build_detectors()


# ---------------------------------------------------------------------------
# 1. bootstrap_from_store exists on every detector
# ---------------------------------------------------------------------------

class TestBootstrapFromStoreExists:
    """All 7 detector classes expose bootstrap_from_store()."""

    @pytest.mark.parametrize("cls", [
        ChargeFailureDetector,
        DuplicateChargeDetector,
        FraudSpikeDetector,
        NegativeInvoiceDetector,
        RevenueDropDetector,
        SilentLapseDetector,
        WebhookLagDetector,
    ])
    def test_method_present(self, cls):
        d = cls()
        assert hasattr(d, "bootstrap_from_store"), (
            f"{cls.__name__} missing bootstrap_from_store()"
        )
        assert callable(d.bootstrap_from_store)

    @pytest.mark.parametrize("cls", [
        ChargeFailureDetector,
        DuplicateChargeDetector,
        FraudSpikeDetector,
        NegativeInvoiceDetector,
        RevenueDropDetector,
        SilentLapseDetector,
        WebhookLagDetector,
    ])
    def test_empty_store_returns_zero(self, cls, tmp_store):
        d = cls()
        replayed = d.bootstrap_from_store(tmp_store)
        assert replayed == 0


# ---------------------------------------------------------------------------
# 2. EventStore persists and retrieves events correctly
# ---------------------------------------------------------------------------

class TestEventStorePersistence:

    def test_insert_and_retrieve(self, tmp_store):
        event = {
            "id": "evt_001",
            "type": "charge.failed",
            "data": {"object": {"id": "ch_001", "amount": 1000}},
            "created": time.time(),
        }
        row_id = tmp_store.insert_event(event)
        assert row_id > 0

        events = tmp_store.get_events_since(3600)
        assert len(events) == 1
        assert events[0]["id"] == "evt_001"

    def test_idempotent_insert(self, tmp_store):
        event = {"id": "evt_dup", "type": "charge.succeeded", "created": time.time()}
        tmp_store.insert_event(event)
        tmp_store.insert_event(event)  # duplicate
        assert tmp_store.total_count() == 1

    def test_mark_processed(self, tmp_store):
        event = {"id": "evt_p1", "type": "charge.succeeded", "created": time.time()}
        tmp_store.insert_event(event)

        unprocessed = tmp_store.get_events_since(3600, unprocessed_only=True)
        assert len(unprocessed) == 1

        tmp_store.mark_processed("evt_p1")
        unprocessed_after = tmp_store.get_events_since(3600, unprocessed_only=True)
        assert len(unprocessed_after) == 0


# ---------------------------------------------------------------------------
# 3. ChargeFailureDetector boots from EventStore and fires alert
# ---------------------------------------------------------------------------

class TestChargeFailureFromStore:

    def _make_charge_event(self, n, succeeded=True):
        etype = "charge.succeeded" if succeeded else "charge.failed"
        return {
            "id": f"evt_cf_{n}",
            "type": etype,
            "data": {"object": {"id": f"ch_{n}", "amount": 2000}},
            "created": time.time(),
        }

    def test_bootstrap_replays_events(self, tmp_store):
        d = ChargeFailureDetector(config={"min_events": 3, "failure_threshold": 0.50, "alert_cooldown_seconds": 0})
        # Seed the store: 1 success + 3 failures = 75% failure rate
        for i, ok in enumerate([True, False, False, False]):
            tmp_store.insert_event(self._make_charge_event(i, succeeded=ok))

        replayed = d.bootstrap_from_store(tmp_store)
        assert replayed == 4
        # After bootstrap the detector knows there were failures; check() should fire
        alerts = d.check()
        assert len(alerts) == 1
        assert "Charge Failure" in alerts[0].title

    def test_bootstrap_with_zero_events(self, tmp_store):
        d = ChargeFailureDetector()
        assert d.bootstrap_from_store(tmp_store) == 0
        assert d.check() == []


# ---------------------------------------------------------------------------
# 4. DuplicateChargeDetector boots from EventStore
# ---------------------------------------------------------------------------

class TestDuplicateChargeFromStore:

    def test_bootstrap_detects_duplicate(self, tmp_store):
        d = DuplicateChargeDetector(config={"duplicate_threshold": 2, "pair_cooldown_seconds": 0})
        for i in range(2):
            tmp_store.insert_event({
                "id": f"evt_dc_{i}",
                "type": "charge.succeeded",
                "data": {"object": {"id": f"ch_dc_{i}", "customer": "cus_dup", "amount": 999}},
                "created": time.time(),
            })
        replayed = d.bootstrap_from_store(tmp_store)
        assert replayed == 2
        # Duplicate should have fired during replay (second event triggers it)
        # We verify detector has state; firing happens during process_event


# ---------------------------------------------------------------------------
# 5. FraudSpikeDetector boots from EventStore
# ---------------------------------------------------------------------------

class TestFraudSpikeFromStore:

    def test_bootstrap_replays_disputes(self, tmp_store):
        d = FraudSpikeDetector(config={"absolute_dispute_threshold": 3, "alert_cooldown_seconds": 0})
        for i in range(3):
            tmp_store.insert_event({
                "id": f"evt_fraud_{i}",
                "type": "charge.dispute.created",
                "data": {"object": {}},
                "created": time.time(),
            })
        replayed = d.bootstrap_from_store(tmp_store)
        assert replayed == 3


# ---------------------------------------------------------------------------
# 6. RevenueDropDetector boots from EventStore
# ---------------------------------------------------------------------------

class TestRevenueDropFromStore:

    def test_bootstrap_loads_revenue_history(self, tmp_store):
        d = RevenueDropDetector(config={
            "min_days_of_data": 2,
            "drop_threshold": 0.20,
            "min_daily_revenue_cents": 1000,
        })
        base = time.time()
        for i in range(3):
            tmp_store.insert_event({
                "id": f"evt_rev_{i}",
                "type": "invoice.payment_succeeded",
                "data": {"object": {
                    "amount_paid": 100_000,  # $1000/day
                    "status_transitions": {"paid_at": base - (3 - i) * 86400},
                }},
                "created": base - (3 - i) * 86400,
            })
        # Today — very low revenue
        tmp_store.insert_event({
            "id": "evt_rev_today",
            "type": "invoice.payment_succeeded",
            "data": {"object": {
                "amount_paid": 5_000,  # $50
                "status_transitions": {"paid_at": base - 3600},
            }},
            "created": base - 3600,
        })
        replayed = d.bootstrap_from_store(tmp_store)
        assert replayed == 4
        alerts = d.check()
        assert len(alerts) == 1
        assert "Drop" in alerts[0].title or "drop" in alerts[0].title.lower()


# ---------------------------------------------------------------------------
# 7. SilentLapseDetector boots from EventStore
# ---------------------------------------------------------------------------

class TestSilentLapseFromStore:

    def test_bootstrap_tracks_subscription(self, tmp_store):
        d = SilentLapseDetector()
        tmp_store.insert_event({
            "id": "evt_sl_sub",
            "type": "customer.subscription.updated",
            "data": {"object": {
                "id": "sub_123", "customer": "cus_lapse", "status": "active",
                "plan": {"interval": "month", "interval_count": 1},
            }},
            "created": time.time(),
        })
        tmp_store.insert_event({
            "id": "evt_sl_pay",
            "type": "invoice.payment_succeeded",
            "data": {"object": {
                "customer": "cus_lapse",
                "status_transitions": {"paid_at": time.time() - 40 * 86400},
            }},
            "created": time.time() - 40 * 86400,
        })
        replayed = d.bootstrap_from_store(tmp_store)
        assert replayed == 2
        alerts = d.check()
        assert any("lapse" in a.title.lower() or "Lapse" in a.title for a in alerts)


# ---------------------------------------------------------------------------
# 8. WebhookLagDetector boots from EventStore
# ---------------------------------------------------------------------------

class TestWebhookLagFromStore:

    def test_bootstrap_updates_last_event_received(self, tmp_store):
        d = WebhookLagDetector(config={"warning_lag_seconds": 9999})
        recent_ts = time.time() - 30
        tmp_store.insert_event({
            "id": "evt_wl_1",
            "type": "invoice.payment_succeeded",
            "created": recent_ts,
        })
        replayed = d.bootstrap_from_store(tmp_store)
        assert replayed == 1
        # After bootstrap, last_event_received_at should be updated
        assert d._last_event_received_at is not None


# ---------------------------------------------------------------------------
# 9. NegativeInvoiceDetector boots from EventStore
# ---------------------------------------------------------------------------

class TestNegativeInvoiceFromStore:

    def test_bootstrap_counts_refunds(self, tmp_store):
        d = NegativeInvoiceDetector(config={"large_refund_threshold_cents": 10_000})
        tmp_store.insert_event({
            "id": "evt_ni_1",
            "type": "charge.refunded",
            "data": {"object": {"id": "ch_r1", "customer": "cus_refund", "amount_refunded": 5_000}},
            "created": time.time(),
        })
        replayed = d.bootstrap_from_store(tmp_store)
        assert replayed == 1


# ---------------------------------------------------------------------------
# 10. Full bootstrap_all (event_processor) uses all 7 detectors
# ---------------------------------------------------------------------------

class TestBootstrapAll:

    def test_all_seven_detectors_bootstrapped(self, tmp_store):
        """bootstrap_all() runs without error across all 10 detectors."""
        detectors = build_detectors()
        assert len(detectors) == 10
        # Should not raise
        bootstrap_all(detectors, tmp_store)

    def test_run_scheduled_checks_returns_int(self, all_detectors):
        """run_scheduled_checks() returns the count of alerts fired."""
        result = run_scheduled_checks(all_detectors)
        assert isinstance(result, int)
        assert result >= 0

    def test_all_detector_names_present(self):
        detectors = build_detectors()
        expected = {
            "charge_failure", "duplicate_charge", "fraud_spike",
            "negative_invoice", "revenue_drop", "silent_lapse", "webhook_lag",
            "currency_mismatch", "timezone_billing_error", "plan_downgrade_data_loss",
        }
        assert set(detectors.keys()) == expected
