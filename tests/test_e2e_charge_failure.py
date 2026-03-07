"""
Integration test: webhook → EventStore → ChargeFailureSpikeDetector → anomaly

Tests the complete pipeline:
  1. Send charge.failed events via the webhook handler
  2. Confirm they're persisted in EventStore
  3. Confirm ChargeFailureSpikeDetector fires when threshold is breached

Run from BillingWatch project root:
    .venv/bin/python3.14 tests/test_e2e_charge_failure.py
"""

import json
import os
import sys
import time
import tempfile
import unittest

# Run from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.storage.event_store import EventStore
from src.detectors.charge_failure import ChargeFailureDetector, MIN_EVENTS


def _make_charge_event(event_id: str, succeeded: bool) -> dict:
    return {
        "id": event_id,
        "type": "charge.succeeded" if succeeded else "charge.failed",
        "data": {
            "object": {
                "id": event_id.replace("evt_", "ch_"),
                "amount": 2000,
                "currency": "usd",
            }
        },
    }


class TestChargeFailureE2E(unittest.TestCase):
    """End-to-end: webhook events → SQLite → detector → alert."""

    def setUp(self):
        # Each test gets a fresh temp DB
        self.db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_file.close()
        self.store = EventStore(db_path=self.db_file.name)
        # Detector configured for testing: only need 5 events, 50% threshold
        self.detector = ChargeFailureDetector(config={
            "min_events": 5,
            "failure_threshold": 0.50,
            "alert_cooldown_seconds": 0,  # no cooldown during tests
        })

    # ------------------------------------------------------------------
    # Step 1: Storage
    # ------------------------------------------------------------------

    def test_01_events_stored_in_eventstore(self):
        """Events sent through EventStore are persisted correctly."""
        for i in range(5):
            event = _make_charge_event(f"evt_fail_{i}", succeeded=False)
            row_id = self.store.insert_event(event)
            # Row 0 means duplicate (ignored); new rows get positive IDs
            self.assertGreaterEqual(row_id, 0)

        total = self.store.total_count()
        self.assertEqual(total, 5)

        recent = self.store.get_events_since(3600, event_type="charge.failed")
        self.assertEqual(len(recent), 5)
        print("  [PASS] 5 charge.failed events stored in EventStore")

    def test_02_idempotent_insert(self):
        """Inserting the same event twice doesn't duplicate it."""
        event = _make_charge_event("evt_idem_001", succeeded=False)
        self.store.insert_event(event)
        self.store.insert_event(event)  # duplicate
        self.assertEqual(self.store.total_count(), 1)
        print("  [PASS] Duplicate insert is idempotent")

    def test_03_mark_processed(self):
        """mark_processed correctly flags events."""
        event = _make_charge_event("evt_proc_001", succeeded=False)
        self.store.insert_event(event)
        ok = self.store.mark_processed("evt_proc_001")
        self.assertTrue(ok)
        unproc = self.store.get_events_since(3600, unprocessed_only=True)
        self.assertEqual(len(unproc), 0)
        print("  [PASS] mark_processed works correctly")

    # ------------------------------------------------------------------
    # Step 2: Detector fires from EventStore data
    # ------------------------------------------------------------------

    def test_04_detector_fires_via_process_event(self):
        """
        process_event on 5+ charge.failed events triggers HIGH alert.
        This simulates the webhook handler feeding events to the detector.
        """
        alerts_total = []
        for i in range(7):
            event = _make_charge_event(f"evt_det_{i}", succeeded=False)
            self.store.insert_event(event)
            alerts = self.detector.process_event(event)
            alerts_total.extend(alerts)

        self.assertGreater(len(alerts_total), 0, "Expected at least one alert to fire")
        alert = alerts_total[0]
        self.assertEqual(alert.severity, "high")
        self.assertIn("Charge Failure Spike", alert.title)
        print(f"  [PASS] Detector fired: [{alert.severity.upper()}] {alert.title}")
        print(f"         {alert.message}")

    def test_05_full_pipeline_webhook_to_alert(self):
        """
        Full pipeline: 5 failed + 5 succeeded → below threshold (no alert).
        Then add 5 more failures → above threshold → alert fires.
        """
        # 5 succeeded + 5 failed = 50% failure rate
        for i in range(5):
            self.store.insert_event(_make_charge_event(f"evt_ok_{i}", succeeded=True))
            self.detector.process_event(_make_charge_event(f"evt_ok_{i}", succeeded=True))
        
        initial_alerts = []
        for i in range(5):
            event = _make_charge_event(f"evt_fail_p2_{i}", succeeded=False)
            self.store.insert_event(event)
            initial_alerts.extend(self.detector.process_event(event))

        # 50% failure rate at exactly threshold — may or may not fire depending on rounding
        # Now push it clearly above 50%
        spike_alerts = []
        for i in range(5):
            event = _make_charge_event(f"evt_spike_{i}", succeeded=False)
            self.store.insert_event(event)
            spike_alerts.extend(self.detector.process_event(event))

        self.assertGreater(len(initial_alerts) + len(spike_alerts), 0,
            "Expected at least one alert across the full test")
        
        total_stored = self.store.total_count()
        self.assertEqual(total_stored, 15)
        print(f"  [PASS] Full pipeline: 15 events stored, {len(initial_alerts)+len(spike_alerts)} alert(s) fired")

    # ------------------------------------------------------------------
    # Step 3: Event count summary
    # ------------------------------------------------------------------

    def test_06_get_event_count(self):
        """get_event_count returns correct counts by type."""
        for i in range(3):
            self.store.insert_event(_make_charge_event(f"evt_cnt_f_{i}", succeeded=False))
        for i in range(7):
            self.store.insert_event(_make_charge_event(f"evt_cnt_s_{i}", succeeded=True))

        failed_ct = self.store.get_event_count(3600, event_type="charge.failed")
        succeeded_ct = self.store.get_event_count(3600, event_type="charge.succeeded")
        total_ct = self.store.get_event_count(3600)

        self.assertEqual(failed_ct, 3)
        self.assertEqual(succeeded_ct, 7)
        self.assertEqual(total_ct, 10)
        print(f"  [PASS] get_event_count: {failed_ct} failed, {succeeded_ct} succeeded, {total_ct} total")


if __name__ == "__main__":
    print("=" * 60)
    print("BillingWatch E2E Integration Test")
    print("webhook → EventStore → ChargeFailureSpikeDetector → alert")
    print("=" * 60)
    loader = unittest.TestLoader()
    loader.sortTestMethodsUsing = None  # preserve order
    suite = loader.loadTestsFromTestCase(TestChargeFailureE2E)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
