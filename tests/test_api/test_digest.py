"""Tests for digest API endpoints and DigestBuilder."""
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import create_app
from src.alerting.digest import DigestBuilder, _build_digest_html, _build_digest_text


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def _make_alert(alert_id, severity="high", title="Test alert", detector="charge_failure",
                triggered_at=None):
    ts = triggered_at or datetime.now(timezone.utc).isoformat()
    return {
        "alert_id": alert_id,
        "detector": detector,
        "severity": severity,
        "title": title,
        "message": f"Alert {alert_id}: {title}",
        "triggered_at": ts,
        "stripe_event_id": f"evt_test_{alert_id}",
        "metadata": {},
    }


# ---------------------------------------------------------------------------
# DigestBuilder unit tests
# ---------------------------------------------------------------------------

class TestDigestBuilder:

    def test_build_preview_empty(self):
        builder = DigestBuilder()
        result = builder.build_preview([], window_label="Last 24 hours")
        assert result["alert_count"] == 0
        assert "All clear" in result["text"]
        assert "All clear" in result["html"]
        assert result["smtp_configured"] is False
        assert "generated_at" in result

    def test_build_preview_with_alerts(self):
        builder = DigestBuilder()
        alerts = [_make_alert(1, severity="critical"), _make_alert(2, severity="low")]
        result = builder.build_preview(alerts, window_label="Last 24 hours")
        assert result["alert_count"] == 2
        assert "2 anomal" in result["text"]
        assert "🚨" in result["text"]   # critical emoji in text
        assert "🚨" in result["html"]

    def test_send_digest_no_smtp(self):
        builder = DigestBuilder()  # no env vars → not configured
        alerts = [_make_alert(1)]
        result = builder.send_digest(alerts)
        assert result["sent"] is False
        assert result["reason"] == "smtp_not_configured"
        assert result["alert_count"] == 1

    def test_send_digest_with_smtp(self):
        builder = DigestBuilder(
            from_addr="from@example.com",
            to_addrs=["to@example.com"],
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="user",
            smtp_pass="pass",
        )
        alerts = [_make_alert(1, severity="high")]
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = builder.send_digest(alerts, window_label="Last 24 hours")
        assert result["sent"] is True
        assert result["recipients"] == ["to@example.com"]

    def test_send_digest_smtp_failure(self):
        builder = DigestBuilder(
            from_addr="from@example.com",
            to_addrs=["to@example.com"],
            smtp_host="smtp.example.com",
        )
        with patch("smtplib.SMTP", side_effect=ConnectionRefusedError("refused")):
            result = builder.send_digest([])
        assert result["sent"] is False
        assert "refused" in result["reason"]

    def test_is_configured_true(self):
        b = DigestBuilder(from_addr="a@b.com", to_addrs=["c@d.com"], smtp_host="smtp.x.com")
        assert b.is_configured is True

    def test_is_configured_false_missing_host(self):
        b = DigestBuilder(from_addr="a@b.com", to_addrs=["c@d.com"])
        assert b.is_configured is False

    def test_is_configured_false_missing_to(self):
        b = DigestBuilder(from_addr="a@b.com", smtp_host="smtp.x.com")
        assert b.is_configured is False


class TestDigestTemplates:

    def test_html_empty_has_all_clear(self):
        now = datetime.now(timezone.utc)
        html = _build_digest_html([], "Last 24 hours", now)
        assert "All clear" in html

    def test_html_with_alerts_shows_count(self):
        now = datetime.now(timezone.utc)
        alerts = [_make_alert(1, "critical"), _make_alert(2, "high"), _make_alert(3, "low")]
        html = _build_digest_html(alerts, "Last 24 hours", now)
        assert "3 anomal" in html
        assert "🚨" in html
        assert "🔴" in html
        assert "🟢" in html

    def test_text_empty_has_all_clear(self):
        now = datetime.now(timezone.utc)
        text = _build_digest_text([], "Last 24 hours", now)
        assert "All clear" in text

    def test_text_with_alerts_lists_them(self):
        now = datetime.now(timezone.utc)
        alerts = [_make_alert(1, "critical", "Bad thing happened")]
        text = _build_digest_text(alerts, "Last 24 hours", now)
        assert "CRITICAL" in text
        assert "Bad thing happened" in text

    def test_severity_ordering_html(self):
        """Critical alerts appear before low in the digest."""
        now = datetime.now(timezone.utc)
        alerts = [
            _make_alert(1, "low", "Low alert"),
            _make_alert(2, "critical", "Critical alert"),
        ]
        html = _build_digest_html(alerts, "24h", now)
        assert html.index("Critical alert") < html.index("Low alert")


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

class TestDigestConfig:

    def test_get_config_defaults(self, client):
        resp = client.get("/digest/config")
        assert resp.status_code == 200
        cfg = resp.json()["config"]
        assert "enabled" in cfg
        assert "frequency" in cfg
        assert cfg["frequency"] in ("daily", "weekly")

    def test_put_config_enable(self, client):
        resp = client.put("/digest/config", json={"enabled": True, "frequency": "weekly"})
        assert resp.status_code == 200
        cfg = resp.json()["config"]
        assert cfg["enabled"] is True
        assert cfg["frequency"] == "weekly"

    def test_put_config_partial(self, client):
        # Only update window_hours
        resp = client.put("/digest/config", json={"window_hours": 48})
        assert resp.status_code == 200
        assert resp.json()["config"]["window_hours"] == 48

    def test_put_config_invalid_window(self, client):
        resp = client.put("/digest/config", json={"window_hours": 999})
        assert resp.status_code == 422

    def test_put_config_invalid_frequency(self, client):
        resp = client.put("/digest/config", json={"frequency": "hourly"})
        assert resp.status_code == 422

    def test_put_config_to_addrs(self, client):
        resp = client.put("/digest/config", json={"to_addrs": ["admin@example.com"]})
        assert resp.status_code == 200
        assert "admin@example.com" in resp.json()["config"]["to_addrs"]


class TestDigestSend:

    def test_send_preview_empty(self, client):
        with patch("src.api.routes.digest._alert_log", []):
            resp = client.post("/digest/send", json={"preview_only": True, "window_hours": 24})
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "preview"
        assert data["alert_count"] == 0
        assert "All clear" in data["text"]

    def test_send_preview_with_alerts(self, client):
        now_str = datetime.now(timezone.utc).isoformat()
        alerts = [_make_alert(1, "critical", triggered_at=now_str)]
        with patch("src.api.routes.digest._alert_log", alerts):
            resp = client.post("/digest/send", json={"preview_only": True, "window_hours": 24})
        assert resp.status_code == 200
        data = resp.json()
        assert data["alert_count"] == 1
        assert "1 anomaly" in data["text"]

    def test_send_no_smtp_returns_not_sent(self, client):
        with patch("src.api.routes.digest._alert_log", []):
            resp = client.post("/digest/send", json={"preview_only": False})
        assert resp.status_code == 200
        data = resp.json()
        assert data["sent"] is False
        assert data["reason"] == "smtp_not_configured"

    def test_send_with_mock_smtp(self, client):
        now_str = datetime.now(timezone.utc).isoformat()
        alerts = [_make_alert(1, "high", triggered_at=now_str)]
        with patch("src.api.routes.digest._alert_log", alerts), \
             patch("src.alerting.digest.DigestBuilder.is_configured", new_callable=lambda: property(lambda self: True)), \
             patch("smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
            with patch.dict("os.environ", {
                "ALERT_EMAIL_FROM": "from@example.com",
                "ALERT_EMAIL_TO": "to@example.com",
                "SMTP_HOST": "smtp.example.com",
            }):
                resp = client.post("/digest/send", json={"to_addrs": ["to@example.com"]})
        assert resp.status_code == 200

    def test_send_filters_old_alerts(self, client):
        """Alerts outside the window should be excluded."""
        old_ts = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        new_ts = datetime.now(timezone.utc).isoformat()
        alerts = [
            _make_alert(1, triggered_at=old_ts, title="Old alert"),
            _make_alert(2, triggered_at=new_ts, title="New alert"),
        ]
        with patch("src.api.routes.digest._alert_log", alerts):
            resp = client.post("/digest/send", json={"preview_only": True, "window_hours": 24})
        assert resp.status_code == 200
        data = resp.json()
        assert data["alert_count"] == 1  # only the new one

    def test_send_default_window(self, client):
        """POST /digest/send with no body should work with defaults."""
        with patch("src.api.routes.digest._alert_log", []):
            resp = client.post("/digest/send")
        assert resp.status_code == 200

    def test_preview_html_is_string(self, client):
        with patch("src.api.routes.digest._alert_log", []):
            resp = client.post("/digest/send", json={"preview_only": True})
        assert isinstance(resp.json()["html"], str)
        assert "<html" in resp.json()["html"]
