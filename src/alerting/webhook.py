"""Webhook alerting for BillingWatch.

POSTs anomaly alerts as JSON to a configured HTTP endpoint.
Compatible with Slack incoming webhooks, Discord webhooks, and generic HTTP hooks.

Required env vars:
    ALERT_WEBHOOK_URL       - Primary webhook URL (required)
    ALERT_WEBHOOK_SECRET    - Optional HMAC-SHA256 signing secret
    ALERT_WEBHOOK_TIMEOUT   - Request timeout seconds (default: 10)
"""
import hashlib
import hmac
import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..detectors.base import Alert

logger = logging.getLogger(__name__)

SEVERITY_COLOR = {
    "critical": 15158332,   # red
    "high": 15105570,       # orange
    "medium": 16776960,     # yellow
    "low": 3066993,         # green
}

SEVERITY_EMOJI = {
    "critical": "🚨",
    "high": "🔴",
    "medium": "🟡",
    "low": "🟢",
}


def _build_payload(alert: Alert) -> Dict[str, Any]:
    """Build a generic webhook payload (works for Slack, Discord, and plain HTTP)."""
    emoji = SEVERITY_EMOJI.get(alert.severity, "⚠️")
    color = SEVERITY_COLOR.get(alert.severity, 7506394)
    ts = int(alert.triggered_at.timestamp())

    return {
        # Generic fields (plain HTTP consumers)
        "event": "billingwatch.alert",
        "detector": alert.detector,
        "severity": alert.severity,
        "title": alert.title,
        "message": alert.message,
        "metadata": alert.metadata,
        "triggered_at": alert.triggered_at.isoformat(),
        # Slack-compatible structure
        "text": f"{emoji} *BillingWatch Alert* — {alert.title}",
        "attachments": [
            {
                "color": f"#{color:06x}",
                "title": alert.title,
                "text": alert.message,
                "fields": [
                    {"title": "Detector", "value": alert.detector, "short": True},
                    {"title": "Severity", "value": alert.severity.upper(), "short": True},
                ]
                + [
                    {"title": k, "value": str(v), "short": True}
                    for k, v in alert.metadata.items()
                ],
                "footer": "BillingWatch",
                "ts": ts,
            }
        ],
        # Discord-compatible embeds
        "embeds": [
            {
                "title": f"{emoji} {alert.title}",
                "description": alert.message,
                "color": color,
                "fields": [
                    {"name": "Detector", "value": alert.detector, "inline": True},
                    {"name": "Severity", "value": alert.severity.upper(), "inline": True},
                ]
                + [
                    {"name": k, "value": str(v), "inline": True}
                    for k, v in alert.metadata.items()
                ],
                "footer": {"text": "BillingWatch"},
                "timestamp": alert.triggered_at.isoformat(),
            }
        ],
    }


def _sign_payload(body: bytes, secret: str) -> str:
    """Return HMAC-SHA256 signature for the payload."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class WebhookAlerter:
    """Delivers BillingWatch alerts via HTTP webhook POST."""

    def __init__(
        self,
        url: Optional[str] = None,
        secret: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.url = url or os.environ.get("ALERT_WEBHOOK_URL", "")
        self.secret = secret or os.environ.get("ALERT_WEBHOOK_SECRET", "")
        self.timeout = timeout or int(os.environ.get("ALERT_WEBHOOK_TIMEOUT", "10"))

    @property
    def is_configured(self) -> bool:
        return bool(self.url)

    def send(self, alert: Alert) -> bool:
        """POST the alert to the webhook URL. Returns True on success."""
        if not self.is_configured:
            logger.warning("[webhook] No URL configured — skipping alert: %s", alert.title)
            return False

        payload = _build_payload(alert)
        body = json.dumps(payload, default=str).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "BillingWatch/1.0",
        }
        if self.secret:
            headers["X-BillingWatch-Signature"] = _sign_payload(body, self.secret)

        req = urllib.request.Request(self.url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status = resp.status
            if 200 <= status < 300:
                logger.info("[webhook] Alert delivered (%d): %s", status, alert.title)
                return True
            else:
                logger.error("[webhook] Unexpected status %d for alert: %s", status, alert.title)
                return False
        except Exception as exc:
            logger.error("[webhook] Failed to deliver alert '%s': %s", alert.title, exc)
            return False

    def send_batch(self, alerts: List[Alert]) -> int:
        """Deliver multiple alerts. Returns count of successes."""
        return sum(1 for a in alerts if self.send(a))


class AlertDispatcher:
    """Routes alerts to all configured delivery channels (email + webhook).

    Usage:
        dispatcher = AlertDispatcher()  # reads from env
        dispatcher.dispatch(alert)
        dispatcher.dispatch_batch(alerts)
    """

    def __init__(
        self,
        email_alerter: Optional[Any] = None,
        webhook_alerter: Optional[WebhookAlerter] = None,
    ):
        # Lazy import to avoid circular deps if email module isn't available
        if email_alerter is None:
            from .email import EmailAlerter
            self._email = EmailAlerter()
        else:
            self._email = email_alerter

        self._webhook = webhook_alerter or WebhookAlerter()

    def dispatch(self, alert: Alert) -> Dict[str, bool]:
        """Send alert to all configured channels. Returns per-channel success."""
        results: Dict[str, bool] = {}
        if self._email.is_configured:
            results["email"] = self._email.send(alert)
        if self._webhook.is_configured:
            results["webhook"] = self._webhook.send(alert)
        if not results:
            logger.warning("[dispatcher] No alert channels configured for: %s", alert.title)
        return results

    def dispatch_batch(self, alerts: List[Alert]) -> Dict[str, int]:
        """Send multiple alerts. Returns per-channel success counts."""
        counts: Dict[str, int] = {"email": 0, "webhook": 0}
        for alert in alerts:
            results = self.dispatch(alert)
            for channel, ok in results.items():
                if ok:
                    counts[channel] += 1
        return counts
