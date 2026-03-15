"""Slack and Discord alerting for BillingWatch.

Dedicated alerters for Slack and Discord webhooks with platform-native payloads.

Required env vars:
    SLACK_WEBHOOK_URL    - Slack incoming webhook URL (optional)
    DISCORD_WEBHOOK_URL  - Discord webhook URL (optional)
"""
import json
import logging
import os
import urllib.request
from typing import Any, Dict, List, Optional

from ..detectors.base import Alert

logger = logging.getLogger(__name__)

SEVERITY_COLOR = {
    "critical": 15158332,   # red     #E74C3C
    "high":     15105570,   # orange  #E67E22
    "medium":   16776960,   # yellow  #FFFF00
    "low":       3066993,   # green   #2ECC71
}

SEVERITY_EMOJI = {
    "critical": "🚨",
    "high":     "🔴",
    "medium":   "🟡",
    "low":      "🟢",
}


# ─── Slack ──────────────────────────────────────────────────────────────────────

def _slack_payload(alert: Alert) -> Dict[str, Any]:
    """Build a Slack Block Kit + legacy attachment payload."""
    emoji = SEVERITY_EMOJI.get(alert.severity, "⚠️")
    color_map = {"critical": "danger", "high": "warning", "medium": "warning", "low": "good"}
    color = color_map.get(alert.severity, "warning")

    meta_fields = [
        {"title": k, "value": str(v), "short": True}
        for k, v in alert.metadata.items()
    ]

    return {
        "text": f"{emoji} *BillingWatch Alert* — {alert.title}",
        "attachments": [
            {
                "color": color,
                "title": alert.title,
                "text": alert.message,
                "fields": [
                    {"title": "Detector", "value": alert.detector, "short": True},
                    {"title": "Severity", "value": alert.severity.upper(), "short": True},
                ] + meta_fields,
                "footer": "BillingWatch",
                "ts": int(alert.triggered_at.timestamp()),
                "mrkdwn_in": ["text"],
            }
        ],
    }


class SlackAlerter:
    """Delivers BillingWatch alerts to a Slack channel via incoming webhook."""

    def __init__(self, url: Optional[str] = None, timeout: int = 10):
        self.url = url or os.environ.get("SLACK_WEBHOOK_URL", "")
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        return bool(self.url)

    def send(self, alert: Alert) -> bool:
        if not self.is_configured:
            return False
        payload = _slack_payload(alert)
        body = json.dumps(payload, default=str).encode("utf-8")
        req = urllib.request.Request(
            self.url, data=body,
            headers={"Content-Type": "application/json", "User-Agent": "BillingWatch/1.0"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if 200 <= resp.status < 300:
                    logger.info("[slack] Alert delivered: %s", alert.title)
                    return True
                logger.error("[slack] Status %d for alert: %s", resp.status, alert.title)
                return False
        except Exception as exc:
            logger.error("[slack] Failed to deliver '%s': %s", alert.title, exc)
            return False

    def send_batch(self, alerts: List[Alert]) -> int:
        return sum(1 for a in alerts if self.send(a))


# ─── Discord ─────────────────────────────────────────────────────────────────────

def _discord_payload(alert: Alert) -> Dict[str, Any]:
    """Build a Discord webhook payload with embeds."""
    emoji = SEVERITY_EMOJI.get(alert.severity, "⚠️")
    color = SEVERITY_COLOR.get(alert.severity, 7506394)

    meta_fields = [
        {"name": k, "value": str(v), "inline": True}
        for k, v in alert.metadata.items()
    ]

    return {
        "content": f"{emoji} **BillingWatch Alert** — {alert.title}",
        "embeds": [
            {
                "title": alert.title,
                "description": alert.message,
                "color": color,
                "fields": [
                    {"name": "Detector", "value": alert.detector, "inline": True},
                    {"name": "Severity", "value": alert.severity.upper(), "inline": True},
                ] + meta_fields,
                "footer": {"text": "BillingWatch"},
                "timestamp": alert.triggered_at.isoformat(),
            }
        ],
    }


class DiscordAlerter:
    """Delivers BillingWatch alerts to a Discord channel via webhook."""

    def __init__(self, url: Optional[str] = None, timeout: int = 10):
        self.url = url or os.environ.get("DISCORD_WEBHOOK_URL", "")
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        return bool(self.url)

    def send(self, alert: Alert) -> bool:
        if not self.is_configured:
            return False
        payload = _discord_payload(alert)
        body = json.dumps(payload, default=str).encode("utf-8")
        req = urllib.request.Request(
            self.url, data=body,
            headers={"Content-Type": "application/json", "User-Agent": "BillingWatch/1.0"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                # Discord returns 204 No Content on success
                if resp.status in (200, 204):
                    logger.info("[discord] Alert delivered: %s", alert.title)
                    return True
                logger.error("[discord] Status %d for alert: %s", resp.status, alert.title)
                return False
        except Exception as exc:
            logger.error("[discord] Failed to deliver '%s': %s", alert.title, exc)
            return False

    def send_batch(self, alerts: List[Alert]) -> int:
        return sum(1 for a in alerts if self.send(a))
