# BillingWatch API Documentation
*v1.2.0 — March 2026*

## Overview

BillingWatch runs a FastAPI server (default: `http://localhost:8080`). All endpoints return JSON unless noted.
Interactive Swagger docs are available at `/docs` when the server is running.

**Base URL:** `http://localhost:8080`

---

## Authentication

No API keys required to call BillingWatch. The Stripe webhook endpoint verifies the `Stripe-Signature` header using your webhook signing secret. All other endpoints are unauthenticated (private deployment via firewall or Cloudflare Tunnel assumed).

Set `STRIPE_WEBHOOK_SECRET=dev` to skip signature verification during local testing.

---

## System Endpoints

### GET /health
```json
{
  "status": "ok",
  "service": "BillingWatch",
  "version": "1.2.0",
  "uptime_seconds": 3600,
  "detector_count": 10,
  "last_event_at": 1741600000.0
}
```

### GET /
```json
{ "service": "BillingWatch", "version": "1.2.0", "docs": "/docs", "health": "/health" }
```

---

## Webhook Endpoints (/webhooks)

### POST /webhooks/stripe

Main ingestion endpoint. Point your Stripe webhook here.

**Required headers:**
- `Stripe-Signature: t=...,v1=...` (sent automatically by Stripe)
- `Content-Type: application/json`

**Stripe setup:**
1. Dashboard -> Developers -> Webhooks -> Add endpoint
2. URL: `https://your-domain.com/webhooks/stripe`
3. Select events: `charge.*`, `invoice.*`, `customer.subscription.*`
4. Copy signing secret -> set as `STRIPE_WEBHOOK_SECRET` env var

**Response:**
```json
{
  "received": true,
  "event_type": "charge.failed",
  "alerts_fired": 1,
  "detectors_active": 10
}
```
Errors: 400 if signature missing/invalid or bad JSON.

---

### GET /webhooks/alerts?limit=50

Recent alerts, newest first. In-memory store, last 500 alerts.

**Response:**
```json
{
  "alerts": [
    {
      "title": "Charge Failure Spike",
      "severity": "high",
      "detector": "charge_failure",
      "message": "Failure rate 22% exceeds 15% threshold — 11/50 charges failed",
      "fired_at": 1741600000.0,
      "stripe_event_id": "evt_abc123"
    }
  ],
  "total": 3
}
```
Severity levels: `info`, `warning`, `high`, `critical`

---

### GET /webhooks/detectors

Lists all registered detector names.

```json
{
  "detectors": ["charge_failure","duplicate_charge","fraud_spike","negative_invoice","revenue_drop","silent_lapse","webhook_lag","currency_mismatch","plan_downgrade_data_loss","timezone_billing_error"],
  "count": 10
}
```

---

## Anomalies Endpoints (/anomalies)

### GET /anomalies/?limit=50&hide_fp=false
Recent anomaly alerts, newest first. `limit` range: 1–500. Set `hide_fp=true` to exclude false positives.

**Response:**
```json
{
  "anomalies": [
    {
      "title": "Charge Failure Spike",
      "severity": "high",
      "detector": "charge_failure",
      "alert_id": 3,
      "false_positive": false
    }
  ],
  "total": 5,
  "shown": 5
}
```

### PATCH /anomalies/{alert_id}/false-positive

Mark an alert as a false positive (e.g., scheduled maintenance window).

**Request body** (optional):
```json
{ "reason": "scheduled maintenance window" }
```

**Response:**
```json
{
  "alert_id": 3,
  "detector": "charge_failure",
  "false_positive": true,
  "reason": "scheduled maintenance window",
  "message": "Alert marked as false positive. FP rate updated in /metrics/detectors."
}
```
Errors: 404 if alert_id not found.

### DELETE /anomalies/{alert_id}/false-positive

Remove a false positive marking from an alert.

```json
{ "alert_id": 3, "false_positive": false, "message": "False positive removed." }
```
Errors: 404 if no record found.

### GET /anomalies/summary

Health summary with alert counts, last-hour charge metrics, and false positive stats.

```json
{
  "status": "alert",
  "alerts_total": 5,
  "alerts_high": 2,
  "alerts_critical": 1,
  "false_positives": {
    "total": 1,
    "by_detector": { "charge_failure": 1 }
  },
  "last_hour": {
    "charge_failed": 8,
    "charge_total": 40,
    "failure_rate_pct": "20.0%"
  }
}
```
`status` is `"ok"` when no high/critical alerts exist; `"alert"` otherwise.

---

## Metrics Endpoints (/metrics)

### GET /metrics/?window_hours=1.0

Live event counts from SQLite. `window_hours` range: 0.1–168.0

```json
{
  "window_hours": 1.0,
  "total_events": 150,
  "charges": {
    "succeeded": 140,
    "failed": 10,
    "failure_rate": 0.0667,
    "failure_rate_pct": "6.7%"
  },
  "all_time_total": 4823,
  "status": "live"
}
```
`status` is `"live"` if events exist in window, `"no_data"` if empty.

### GET /metrics/detectors

Active detector summary with alert counts and false positive rates.

### GET /metrics/recent-events?limit=20

Most recent raw webhook events, newest first. `limit` range: 1–200.

```json
{
  "events": [
    {
      "id": "evt_abc123",
      "type": "charge.failed",
      "object_id": "ch_xyz789",
      "amount": 9900,
      "currency": "usd"
    }
  ],
  "count": 20
}
```

---

## Config Endpoints (/config)

Runtime threshold management — no restart required.

### GET /config/thresholds

Return all current detector thresholds (with defaults for any unset keys).

```json
{
  "thresholds": {
    "charge_failure_rate": 0.15,
    "revenue_drop_pct": 0.15,
    "webhook_lag_warning_s": 300,
    "webhook_lag_critical_s": 1800,
    "duplicate_threshold": 2,
    "dispute_rate_threshold": 0.01,
    "refund_rate_threshold": 0.10,
    "large_refund_usd": 500.0
  },
  "defaults": { "...": "same keys with default values" }
}
```

### PATCH /config/thresholds

Update one or more thresholds at runtime. Changes persist to SQLite and take effect on the next webhook event — no restart required.

**Request body** (send only the keys you want to change):
```json
{ "charge_failure_rate": 0.20, "duplicate_threshold": 3 }
```

**Response:**
```json
{
  "updated": ["charge_failure_rate", "duplicate_threshold"],
  "thresholds": { "...": "full updated thresholds" },
  "detectors_reloaded": true
}
```
Errors: 400 if no fields sent; 422 if unknown keys.

---

## Dashboard Endpoints (/dashboard)

### GET /dashboard

Renders the HTML monitoring dashboard (browser UI).

### GET /dashboard/summary

JSON summary of current dashboard state.

---

## Demo Endpoints (/demo)

Interactive billing scenarios — synthetic events through isolated detector instances.
No Stripe connection, no real data touched.

### GET /demo/

Lists available scenarios.

| Scenario | Severity | What happens |
|----------|----------|-------------|
| `charge_failure_spike` | high | 18 failures in 60s, pushes rate above 15% threshold |
| `duplicate_charge` | high | Same customer charged 3x in 90 seconds |
| `fraud_spike` | critical | 12 fraud-flagged failures in 30 seconds |
| `negative_invoice` | high | Coupon misconfiguration produces negative invoice total |

### GET /demo/run?scenario={scenario_name}

Run a scenario by name, see which alerts fire. Uses a **query parameter** (not a path param).

```bash
curl "http://localhost:8080/demo/run?scenario=charge_failure_spike"
```

```json
{
  "scenario": "charge_failure_spike",
  "title": "Charge Failure Spike",
  "alerts_fired": 1,
  "alerts": [{ "title": "Charge Failure Spike", "severity": "high" }]
}
```

---

## Beta Endpoints (/beta)

User feedback collection — used for beta validation.

### POST /beta/feedback (status 201)

Submit feedback.

### GET /beta/feedback

List all feedback entries.

### GET /beta/feedback/summary

Aggregated feedback summary.

---

## Onboarding Endpoints (/onboarding)

### GET /onboarding/

Setup checklist — verifies env vars, Stripe connectivity, webhook signature config.

---

## Detector Reference

All 10 detectors run on every incoming Stripe event.

| Detector | Trigger | Default Threshold | Severity |
|----------|---------|-------------------|----------|
| `charge_failure` | Charge failure rate spike | 15% in 5-min window | high |
| `duplicate_charge` | Same customer + same amount repeated | 2 in 90 seconds | high |
| `fraud_spike` | Fraud-flagged charge failures | 10 in 60 seconds | critical |
| `negative_invoice` | Invoice with negative total | Any negative amount | high |
| `revenue_drop` | Rolling 7-day revenue drop | 15% drop | high |
| `silent_lapse` | Subscription active after payment failure | Any | high |
| `webhook_lag` | Stripe event delivery delay | >5 minutes | warning |
| `currency_mismatch` | Unexpected currency on charge | Any | warning |
| `plan_downgrade_data_loss` | Subscription downgraded with data risk | Any | high |
| `timezone_billing_error` | Billing timestamp timezone anomaly | Any | warning |

Use `GET /config/thresholds` to view current values; `PATCH /config/thresholds` to update.

---

## Alert Routing (Environment Variables)

Set these in your `.env` file at project root:

```bash
# Stripe
STRIPE_WEBHOOK_SECRET=whsec_...

# Email alerts (SMTP)
ALERT_EMAIL_FROM=alerts@yourcompany.com
ALERT_EMAIL_TO=you@yourcompany.com
ALERT_EMAIL_HOST=smtp.yourprovider.com
ALERT_EMAIL_PORT=587
ALERT_EMAIL_USER=alerts@yourcompany.com
ALERT_EMAIL_PASS=your-smtp-password

# Webhook alerts (Slack, Discord, PagerDuty, etc.)
ALERT_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

---

## Quick curl Reference

```bash
# Health check
curl http://localhost:8080/health

# Run demo scenario (query param, not path param)
curl "http://localhost:8080/demo/run?scenario=fraud_spike"

# Recent alerts
curl "http://localhost:8080/webhooks/alerts?limit=10"

# Anomaly summary
curl http://localhost:8080/anomalies/summary

# List anomalies (hide false positives)
curl "http://localhost:8080/anomalies/?hide_fp=true"

# Mark alert as false positive
curl -X PATCH http://localhost:8080/anomalies/3/false-positive \
  -H "Content-Type: application/json" \
  -d {reason: maintenance window}

# Last-hour metrics
curl http://localhost:8080/metrics/

# 24-hour metrics
curl "http://localhost:8080/metrics/?window_hours=24"

# Recent events
curl "http://localhost:8080/metrics/recent-events?limit=5"

# Get current thresholds
curl http://localhost:8080/config/thresholds

# Update a threshold at runtime (no restart needed)
curl -X PATCH http://localhost:8080/config/thresholds \
  -H "Content-Type: application/json" \
  -d {charge_failure_rate: 0.20}

# Setup checklist
curl http://localhost:8080/onboarding/

# Test webhook in dev mode (set STRIPE_WEBHOOK_SECRET=dev first)
curl -X POST http://localhost:8080/webhooks/stripe \
  -H "Content-Type: application/json" \
  -H "Stripe-Signature: dev" \
  -d '{"id":"evt_test","type":"charge.failed","data":{"object":{"amount":9900,"currency":"usd"}}}'
```

---
*Updated: March 11, 2026 | BillingWatch v1.2.0 | Audit: api_docs_audit_2026-03-11.md*
