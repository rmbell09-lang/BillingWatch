"""Base class for all BillingWatch anomaly detectors."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Alert:
    """Represents a detected anomaly alert."""
    detector: str
    severity: str  # low | medium | high | critical
    title: str
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    triggered_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detector": self.detector,
            "severity": self.severity,
            "title": self.title,
            "message": self.message,
            "metadata": self.metadata,
            "triggered_at": self.triggered_at.isoformat(),
        }


class BaseDetector(ABC):
    """Abstract base class for all anomaly detectors."""

    name: str = "base"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    @abstractmethod
    def process_event(self, event: Dict[str, Any]) -> List[Alert]:
        """Process a single Stripe event and return any triggered alerts."""
        ...

    @abstractmethod
    def check(self) -> List[Alert]:
        """Scheduled check — runs independently of event stream (e.g., every 15 min)."""
        ...

    def bootstrap_from_store(self, store: Any, window_seconds: float = 86400) -> int:
        """
        Hydrate in-memory state from EventStore.

        Queries the past ``window_seconds`` of events and replays each one
        through :meth:`process_event`.  Call this at startup to restore
        detector state after a process restart.

        Args:
            store: An :class:`~src.storage.event_store.EventStore` instance.
            window_seconds: How far back to look (default 24 h).

        Returns:
            Number of events successfully replayed.
        """
        events = store.get_events_since(window_seconds)
        count = 0
        for event in events:
            try:
                self.process_event(event)
                count += 1
            except Exception as exc:
                self._log(
                    "bootstrap_from_store: error replaying event "
                    + str(event.get("id", "?")) + ": " + str(exc)
                )
        return count

    def _log(self, msg: str):
        print(f"[{self.name}] {msg}")
