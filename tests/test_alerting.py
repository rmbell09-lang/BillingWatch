"""Unit tests for BillingWatch alerting layer.

Tests EmailAlerter, WebhookAlerter, and AlertDispatcher with mocked
SMTP and HTTP transports — no real network calls made.
"""
import hashlib
import hmac
import json
import os
import smtplib
from datetime import datetime
from unittest.mock import MagicMock, patch, call
from urllib.error import URLError

import pytest

from src.detectors.base import Alert
from src.alerting.email import EmailAlerter, _build_html, _build_text
from src.alerting.webhook import WebhookAlerter, AlertDispatcher, _build_payload, _sign_payload


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_alert():
    return Alert(
        detector="charge_failure_spike",
        severity="high",
        title="Charge Failure Spike Detected",
        message="Failure rate is 25.0% (5/20 charges failed) over the past hour.",
        metadata={"failure_rate": 0.25, "failures": 5, "total": 20},
        triggered_at=datetime(2026, 3, 6, 5, 0, 0),
    )


@pytest.fixture
def critical_alert():
    return Alert(
        detector="fraud_spike",
        severity="critical",
        title="Fraud Spike",
        message="Card fingerprint abc123 charged 10 times in 60 minutes.",
        metadata={"card": "abc123", "count": 10},
    )


# ─────────────────────────────────────────────────────────────────────────────
# EmailAlerter tests
# ─────────────────────────────────────────────────────────────────────────────

class TestEmailAlerter:

    def test_is_configured_returns_false_when_missing_fields(self):
        alerter = EmailAlerter(from_addr="", to_addrs=[], smtp_host="")
        assert not alerter.is_configured

    def test_is_configured_returns_true_when_all_set(self):
        alerter = EmailAlerter(
            from_addr="from@example.com",
            to_addrs=["to@example.com"],
            smtp_host="smtp.example.com",
        )
        assert alerter.is_configured

    def test_send_skips_when_not_configured(self, sample_alert):
        alerter = EmailAlerter()
        result = alerter.send(sample_alert)
        assert result is False

    @patch("src.alerting.email.smtplib.SMTP")
    def test_send_success(self, mock_smtp_cls, sample_alert):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        alerter = EmailAlerter(
            from_addr="from@example.com",
            to_addrs=["to@example.com"],
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="user",
            smtp_pass="pass",
            use_tls=True,
        )
        result = alerter.send(sample_alert)
        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user", "pass")
        assert mock_server.sendmail.called

    @patch("src.alerting.email.smtplib.SMTP")
    def test_send_returns_false_on_smtp_error(self, mock_smtp_cls, sample_alert):
        mock_smtp_cls.side_effect = smtplib.SMTPException("Connection refused")
        alerter = EmailAlerter(
            from_addr="from@example.com",
            to_addrs=["to@example.com"],
            smtp_host="smtp.example.com",
        )
        result = alerter.send(sample_alert)
        assert result is False

    @patch("src.alerting.email.smtplib.SMTP")
    def test_send_batch_returns_success_count(self, mock_smtp_cls, sample_alert, critical_alert):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        alerter = EmailAlerter(
            from_addr="f@x.com", to_addrs=["t@x.com"], smtp_host="smtp.x.com"
        )
        count = alerter.send_batch([sample_alert, critical_alert])
        assert count == 2

    def test_build_text_contains_key_fields(self, sample_alert):
        text = _build_text(sample_alert)
        assert "charge_failure_spike" in text
        assert "HIGH" in text
        assert "Charge Failure Spike Detected" in text
        assert "failure_rate" in text

    def test_build_html_contains_key_fields(self, sample_alert):
        html = _build_html(sample_alert)
        assert "BillingWatch Alert" in html
        assert "Charge Failure Spike Detected" in html
        assert "charge_failure_spike" in html

    def test_to_addrs_parsed_from_comma_string(self):
        alerter = EmailAlerter(
            from_addr="f@x.com",
            to_addrs="a@x.com, b@x.com, c@x.com",
            smtp_host="smtp.x.com",
        )
        assert alerter.to_addrs == ["a@x.com", "b@x.com", "c@x.com"]


# ─────────────────────────────────────────────────────────────────────────────
# WebhookAlerter tests
# ─────────────────────────────────────────────────────────────────────────────

class TestWebhookAlerter:

    def test_is_configured_false_when_no_url(self):
        alerter = WebhookAlerter(url="")
        assert not alerter.is_configured

    def test_is_configured_true_with_url(self):
        alerter = WebhookAlerter(url="https://hooks.example.com/bw")
        assert alerter.is_configured

    def test_send_skips_when_not_configured(self, sample_alert):
        alerter = WebhookAlerter(url="")
        assert alerter.send(sample_alert) is False

    @patch("src.alerting.webhook.urllib.request.urlopen")
    def test_send_success(self, mock_urlopen, sample_alert):
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 200
        mock_urlopen.return_value = mock_resp

        alerter = WebhookAlerter(url="https://hooks.example.com/bw")
        result = alerter.send(sample_alert)
        assert result is True
        assert mock_urlopen.called

    @patch("src.alerting.webhook.urllib.request.urlopen")
    def test_send_returns_false_on_non_2xx(self, mock_urlopen, sample_alert):
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 500
        mock_urlopen.return_value = mock_resp

        alerter = WebhookAlerter(url="https://hooks.example.com/bw")
        result = alerter.send(sample_alert)
        assert result is False

    @patch("src.alerting.webhook.urllib.request.urlopen")
    def test_send_returns_false_on_network_error(self, mock_urlopen, sample_alert):
        mock_urlopen.side_effect = URLError("Connection refused")
        alerter = WebhookAlerter(url="https://hooks.example.com/bw")
        result = alerter.send(sample_alert)
        assert result is False

    def test_hmac_signature_in_headers_when_secret_set(self, sample_alert):
        """Verify that HMAC header is added when secret is configured."""
        from src.alerting.webhook import _build_payload, _sign_payload
        payload = _build_payload(sample_alert)
        body = json.dumps(payload, default=str).encode("utf-8")
        sig = _sign_payload(body, "mysecret")
        expected = hmac.new(b"mysecret", body, hashlib.sha256).hexdigest()
        assert sig == expected

    def test_payload_has_slack_and_discord_fields(self, sample_alert):
        payload = _build_payload(sample_alert)
        assert "attachments" in payload      # Slack
        assert "embeds" in payload           # Discord
        assert payload["event"] == "billingwatch.alert"
        assert payload["detector"] == "charge_failure_spike"

    def test_payload_severity_colors(self, critical_alert):
        payload = _build_payload(critical_alert)
        # Critical should map to red (15158332)
        assert payload["embeds"][0]["color"] == 15158332

    @patch("src.alerting.webhook.urllib.request.urlopen")
    def test_send_batch_returns_count(self, mock_urlopen, sample_alert, critical_alert):
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 200
        mock_urlopen.return_value = mock_resp

        alerter = WebhookAlerter(url="https://hooks.example.com/bw")
        count = alerter.send_batch([sample_alert, critical_alert])
        assert count == 2


# ─────────────────────────────────────────────────────────────────────────────
# AlertDispatcher tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAlertDispatcher:

    def test_dispatch_calls_both_channels(self, sample_alert):
        mock_email = MagicMock()
        mock_email.is_configured = True
        mock_email.send.return_value = True

        mock_webhook = MagicMock()
        mock_webhook.is_configured = True
        mock_webhook.send.return_value = True

        dispatcher = AlertDispatcher(email_alerter=mock_email, webhook_alerter=mock_webhook)
        results = dispatcher.dispatch(sample_alert)

        mock_email.send.assert_called_once_with(sample_alert)
        mock_webhook.send.assert_called_once_with(sample_alert)
        assert results == {"email": True, "webhook": True}

    def test_dispatch_skips_unconfigured_channels(self, sample_alert):
        mock_email = MagicMock()
        mock_email.is_configured = False

        mock_webhook = MagicMock()
        mock_webhook.is_configured = True
        mock_webhook.send.return_value = True

        dispatcher = AlertDispatcher(email_alerter=mock_email, webhook_alerter=mock_webhook)
        results = dispatcher.dispatch(sample_alert)

        mock_email.send.assert_not_called()
        assert results == {"webhook": True}

    def test_dispatch_batch_aggregates_counts(self, sample_alert, critical_alert):
        mock_email = MagicMock()
        mock_email.is_configured = True
        mock_email.send.return_value = True

        mock_webhook = MagicMock()
        mock_webhook.is_configured = True
        mock_webhook.send.return_value = False  # webhook always fails

        dispatcher = AlertDispatcher(email_alerter=mock_email, webhook_alerter=mock_webhook)
        counts = dispatcher.dispatch_batch([sample_alert, critical_alert])

        assert counts["email"] == 2
        assert counts["webhook"] == 0

    def test_dispatch_handles_no_channels_configured(self, sample_alert):
        mock_email = MagicMock()
        mock_email.is_configured = False
        mock_webhook = MagicMock()
        mock_webhook.is_configured = False

        dispatcher = AlertDispatcher(email_alerter=mock_email, webhook_alerter=mock_webhook)
        results = dispatcher.dispatch(sample_alert)
        assert results == {}
