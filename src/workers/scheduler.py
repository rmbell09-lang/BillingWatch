"""BillingWatch digest scheduler.

Checks every POLL_INTERVAL_SECONDS whether a digest is due and sends it.
Designed to be imported and started from event_processor.py or run standalone.

Run standalone:
    python3 -m src.workers.scheduler
"""

import logging
import os
import sys
import time
from datetime import datetime, timezone, timedelta

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 300  # check every 5 minutes


# ---------------------------------------------------------------------------
# Scheduler state (in-process; survives restarts only if you write to disk)
# ---------------------------------------------------------------------------

_state = {
    "enabled": False,
    "frequency": "daily",       # "daily" | "weekly"
    "window_hours": 24,
    "to_addrs": [],
    "last_sent_at": None,       # datetime | None
}


def configure(
    enabled: bool = False,
    frequency: str = "daily",
    window_hours: int = 24,
    to_addrs=None,
):
    """Update scheduler config at runtime."""
    _state["enabled"] = enabled
    _state["frequency"] = frequency
    _state["window_hours"] = window_hours
    _state["to_addrs"] = to_addrs or []
    logger.info(
        "[scheduler] Config updated: enabled=%s frequency=%s window_hours=%s",
        enabled, frequency, window_hours,
    )


def _is_due() -> bool:
    if not _state["enabled"]:
        return False
    last = _state["last_sent_at"]
    if last is None:
        return True  # never sent → due immediately
    freq = _state["frequency"]
    interval = timedelta(hours=24 if freq == "daily" else 168)
    return datetime.now(timezone.utc) - last >= interval


def _run_digest():
    """Pull alerts from the API's in-memory log and send digest."""
    try:
        from src.api.routes.webhooks import _alert_log
        from src.alerting.digest import DigestBuilder

        window_hours = _state["window_hours"]
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        alerts = []
        for a in list(_alert_log):
            triggered = a.get("triggered_at")
            try:
                if isinstance(triggered, str):
                    ts = datetime.fromisoformat(triggered.replace("Z", "+00:00"))
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    if ts >= cutoff:
                        alerts.append(a)
                else:
                    alerts.append(a)
            except (ValueError, TypeError):
                alerts.append(a)

        builder_kwargs = {}
        if _state["to_addrs"]:
            builder_kwargs["to_addrs"] = _state["to_addrs"]

        builder = DigestBuilder(**builder_kwargs)
        window_label = f"Last {window_hours} hour{'s' if window_hours != 1 else ''}"
        result = builder.send_digest(alerts, window_label=window_label)

        now = datetime.now(timezone.utc)
        _state["last_sent_at"] = now

        if result.get("sent"):
            logger.info("[scheduler] Digest sent: %d alerts → %s", len(alerts), result.get("recipients"))
        else:
            logger.info("[scheduler] Digest built (not sent): %s", result.get("reason", "unknown"))

    except Exception as exc:
        logger.error("[scheduler] Digest run failed: %s", exc)


def run_loop():
    """Main scheduler loop. Blocks forever. Run in a thread or subprocess."""
    logger.info("[scheduler] Starting digest scheduler (poll=%ds)", POLL_INTERVAL_SECONDS)
    while True:
        if _is_due():
            logger.info("[scheduler] Digest due — running now.")
            _run_digest()
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # Default: daily enabled when run standalone (for testing)
    configure(enabled=True, frequency="daily", window_hours=24)
    run_loop()
