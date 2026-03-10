"""Event processor worker — bootstraps detectors from EventStore and runs scheduled checks.

Replaces the v1 no-op stub.  On startup it replays the past 24 h of stored
events through every detector to restore in-memory state.  Then it polls for
unprocessed events every POLL_INTERVAL seconds and runs all scheduled
detector checks every SCHEDULED_CHECK_INTERVAL seconds.

Run from the BillingWatch project root:
    python3 -m src.workers.event_processor
"""
import os
import sys
import time

# Allow running as a script from project root
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.storage.event_store import EventStore
from src.detectors.charge_failure import ChargeFailureDetector
from src.detectors.duplicate_charge import DuplicateChargeDetector
from src.detectors.fraud_spike import FraudSpikeDetector
from src.detectors.negative_invoice import NegativeInvoiceDetector
from src.detectors.revenue_drop import RevenueDropDetector
from src.detectors.silent_lapse import SilentLapseDetector
from src.detectors.webhook_lag import WebhookLagDetector
from src.detectors.currency_mismatch import CurrencyMismatchDetector
from src.detectors.timezone_billing_error import TimezoneBillingErrorDetector
from src.detectors.plan_downgrade_data_loss import PlanDowngradeDataLossDetector

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

BOOTSTRAP_WINDOW_SECONDS = 86400    # 24 h of history to replay on startup
POLL_INTERVAL_SECONDS = 30          # how often to check for unprocessed events
SCHEDULED_CHECK_INTERVAL_SECONDS = 900  # 15 min between scheduled detector checks


# ------------------------------------------------------------------
# Detector registry
# ------------------------------------------------------------------

def build_detectors():
    """Instantiate all detectors with default config."""
    return {
        "charge_failure": ChargeFailureDetector(),
        "duplicate_charge": DuplicateChargeDetector(),
        "fraud_spike": FraudSpikeDetector(),
        "negative_invoice": NegativeInvoiceDetector(),
        "revenue_drop": RevenueDropDetector(),
        "silent_lapse": SilentLapseDetector(),
        "webhook_lag": WebhookLagDetector(),
        "currency_mismatch": CurrencyMismatchDetector(),
        "timezone_billing_error": TimezoneBillingErrorDetector(),
        "plan_downgrade_data_loss": PlanDowngradeDataLossDetector(),
    }


# ------------------------------------------------------------------
# Startup bootstrap
# ------------------------------------------------------------------

def bootstrap_all(detectors, store: EventStore) -> None:
    """Replay the last 24 h of stored events through every detector."""
    print("[event_processor] Bootstrapping detectors from EventStore...")
    total_events = store.total_count()
    print(f"[event_processor]   EventStore total events: {total_events}")
    for name, detector in detectors.items():
        replayed = detector.bootstrap_from_store(store, window_seconds=BOOTSTRAP_WINDOW_SECONDS)
        print(f"[event_processor]   {name}: replayed {replayed} events")
    print("[event_processor] Bootstrap complete.")


# ------------------------------------------------------------------
# Scheduled checks
# ------------------------------------------------------------------

def run_scheduled_checks(detectors) -> int:
    """Run check() on every detector; return total alerts fired."""
    fired = 0
    print("[event_processor] Running scheduled detector checks...")
    for name, detector in detectors.items():
        try:
            alerts = detector.check()
            fired += len(alerts)
            for alert in alerts:
                print(
                    f"[event_processor] ALERT [{alert.severity.upper()}] "
                    f"{name}: {alert.title} — {alert.message}"
                )
        except Exception as exc:
            print(f"[event_processor] check() error in {name}: {exc}")
    return fired


# ------------------------------------------------------------------
# Main loop
# ------------------------------------------------------------------

def main() -> None:
    db_path = os.getenv("BILLINGWATCH_DB", None)
    store = EventStore(db_path=db_path)

    print(
        f"[event_processor] Starting BillingWatch event processor.  "
        f"DB: {store._db_path}  |  Stored events: {store.total_count()}"
    )

    detectors = build_detectors()
    bootstrap_all(detectors, store)

    last_scheduled_check_at = time.time()

    print(
        f"[event_processor] Entering poll loop "
        f"(poll every {POLL_INTERVAL_SECONDS}s, "
        f"checks every {SCHEDULED_CHECK_INTERVAL_SECONDS}s)..."
    )

    while True:
        # ---- Process unprocessed events ----
        unprocessed = store.get_events_since(
            BOOTSTRAP_WINDOW_SECONDS, unprocessed_only=True
        )
        for event in unprocessed:
            event_id = event.get("id", "")
            for name, detector in detectors.items():
                try:
                    detector.process_event(event)
                except Exception as exc:
                    print(
                        f"[event_processor] process_event error in {name} "
                        f"for event {event_id}: {exc}"
                    )
            store.mark_processed(event_id)

        if unprocessed:
            print(
                f"[event_processor] Processed {len(unprocessed)} event(s) "
                f"from EventStore."
            )

        # ---- Scheduled checks ----
        now = time.time()
        if now - last_scheduled_check_at >= SCHEDULED_CHECK_INTERVAL_SECONDS:
            run_scheduled_checks(detectors)
            last_scheduled_check_at = now

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
