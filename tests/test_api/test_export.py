"""Tests for CSV export endpoint."""
import csv
import io
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def _make_alert(alert_id, detector="spike", severity="high", title="Test alert"):
    return {
        "alert_id": alert_id,
        "detector": detector,
        "severity": severity,
        "title": title,
        "message": f"Alert {alert_id} message",
        "triggered_at": "2026-03-14T05:00:00",
        "stripe_event_id": f"evt_test_{alert_id}",
        "metadata": {},
    }


def _parse_csv(content: str):
    reader = csv.DictReader(io.StringIO(content))
    return list(reader)


class TestExportAnomalies:
    """GET /export/anomalies"""

    def test_empty_export(self, client):
        with patch("src.api.routes.export._alert_log", []):
            resp = client.get("/export/anomalies")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        assert "billingwatch-anomalies.csv" in resp.headers.get("content-disposition", "")
        rows = _parse_csv(resp.text)
        assert len(rows) == 0

    def test_export_with_alerts(self, client):
        alerts = [_make_alert(1), _make_alert(2, severity="low"), _make_alert(3)]
        with patch("src.api.routes.export._alert_log", alerts):
            resp = client.get("/export/anomalies")
        assert resp.status_code == 200
        rows = _parse_csv(resp.text)
        assert len(rows) == 3
        # Most recent first
        assert rows[0]["alert_id"] == "3"
        assert rows[2]["alert_id"] == "1"

    def test_export_limit(self, client):
        alerts = [_make_alert(i) for i in range(10)]
        with patch("src.api.routes.export._alert_log", alerts):
            resp = client.get("/export/anomalies?limit=3")
        rows = _parse_csv(resp.text)
        assert len(rows) == 3

    def test_export_severity_filter(self, client):
        alerts = [
            _make_alert(1, severity="low"),
            _make_alert(2, severity="high"),
            _make_alert(3, severity="low"),
        ]
        with patch("src.api.routes.export._alert_log", alerts):
            resp = client.get("/export/anomalies?severity=low")
        rows = _parse_csv(resp.text)
        assert len(rows) == 2
        assert all(r["severity"] == "low" for r in rows)

    def test_export_detector_filter(self, client):
        alerts = [
            _make_alert(1, detector="spike"),
            _make_alert(2, detector="threshold"),
            _make_alert(3, detector="spike"),
        ]
        with patch("src.api.routes.export._alert_log", alerts):
            resp = client.get("/export/anomalies?detector=spike")
        rows = _parse_csv(resp.text)
        assert len(rows) == 2
        assert all(r["detector"] == "spike" for r in rows)

    def test_export_csv_columns(self, client):
        alerts = [_make_alert(1)]
        with patch("src.api.routes.export._alert_log", alerts):
            resp = client.get("/export/anomalies")
        rows = _parse_csv(resp.text)
        expected_cols = {"alert_id", "detector", "severity", "title", "message",
                         "triggered_at", "stripe_event_id", "false_positive"}
        assert set(rows[0].keys()) == expected_cols

    def test_export_hide_fp(self, client):
        alerts = [_make_alert(1), _make_alert(2)]
        with patch("src.api.routes.export._alert_log", alerts), \
             patch("src.api.routes.export._fp_store") as mock_fp:
            mock_fp.is_false_positive.side_effect = lambda aid: aid == 1
            resp = client.get("/export/anomalies?hide_fp=true")
        rows = _parse_csv(resp.text)
        assert len(rows) == 1
        assert rows[0]["alert_id"] == "2"

    def test_export_x_total_rows_header(self, client):
        alerts = [_make_alert(i) for i in range(5)]
        with patch("src.api.routes.export._alert_log", alerts):
            resp = client.get("/export/anomalies?limit=3")
        assert resp.headers.get("x-total-rows") == "3"
