# BillingWatch — Developer Documentation

> Real-time Stripe billing anomaly detection for SaaS operators.

---

## Table of Contents

1. [What BillingWatch Does](#what-billingwatch-does)
2. [Installation & Setup](#installation--setup)
3. [Configuring Stripe Webhooks](#configuring-stripe-webhooks)
4. [Reading the Dashboard (API)](#reading-the-dashboard-api)
5. [Adding Custom Detectors](#adding-custom-detectors)
6. [Running Tests](#running-tests)
7. [Environment Variables](#environment-variables)

---

## What BillingWatch Does

BillingWatch is a webhook listener + anomaly engine that sits between Stripe and your team. It ingests every Stripe event, runs it through 7 rule-based detectors, and fires alerts before billing problems turn into support tickets or churn.

**The 7 built-in detectors:**

| Detector | What It Catches | Severity |
|---|---|---|
| `charge_failure` | Charge failure rate > 15% over 1 hour | High |
| `duplicate_charge` | Same customer/amount charged twice within 5 min | Critical |
| `fraud_spike` | Dispute/fraud rate exceeds threshold | Critical |
| `negative_invoice` | Invoice total < 0 (broken promo stacking) | Medium |
| `revenue_drop` | MRR > 15% below 7-day rolling average | High |
| `silent_lapse` | Active subscription, no successful payment | Medium |
| `webhook_lag` | Unprocessed events older than 10 minutes | Low |

**Alert delivery:** Email (SMTP) and/or webhook POST to any endpoint you choose (Slack, Discord, PagerDuty, etc.).

---

## Installation & Setup

### Prerequisites

- Python 3.9+
- A Stripe account (test mode is fine for local dev)
- Stripe CLI (optional — needed only for live event forwarding)

### 1. Clone and install

```bash
cd ~/Projects/BillingWatch
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

For **local development**, you only need these:

```env
STRIPE_SECRET_KEY=sk_test_YOUR_KEY_HERE
STRIPE_WEBHOOK_SECRET=dev
APP_ENV=development
LOG_LEVEL=DEBUG
PORT=8000
```

> **`STRIPE_WEBHOOK_SECRET=dev`** bypasses Stripe signature verification. Safe for local testing, never use in production.

### 3. Start the server

```bash
source .venv/bin/activate
STRIPE_WEBHOOK_SECRET=dev uvicorn src.api.main:app --reload --port 8000
```

Expected output:
```
[BillingWatch] Starting up — all detectors registered.
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### 4. Verify it's running

```bash
# Health check
curl http://localhost:8000/health
# → {"status": "ok", "service": "BillingWatch"}

# List active detectors
curl http://localhost:8000/webhooks/detectors
# → {"detectors": ["charge_failure", "duplicate_charge", ...], "count": 7}

# Interactive API docs (Swagger UI)
open http://localhost:8000/docs
```

---

## Configuring Stripe Webhooks

### Option A: Stripe CLI (local dev)

The simplest way to get real Stripe events flowing locally:

```bash
# Install Stripe CLI: https://stripe.com/docs/stripe-cli
stripe login

# Forward events to BillingWatch
stripe listen --forward-to localhost:8000/webhooks/stripe

# In a separate terminal, trigger test events
stripe trigger charge.failed
stripe trigger invoice.payment_succeeded
stripe trigger charge.succeeded
```

### Option B: Manual cURL (no CLI needed)

Send raw test events directly:

```bash
curl -s -X POST localhost:8000/webhooks/stripe \
  -H 'Content-Type: application/json' \
  -H 'Stripe-Signature: dev' \
  -d '{
    "id": "evt_test_001",
    "type": "charge.failed",
    "created": 1709599200,
    "data": {
      "object": {
        "id": "ch_test_001",
        "customer": "cus_test_001",
        "amount": 2999
      }
    }
  }'
```

Expected response:
```json
{
  "received": true,
  "event_type": "charge.failed",
  "alerts_fired": 0,
  "detectors_active": 7
}
```

> `alerts_fired: 0` is normal for a single event — detectors look for patterns over time (e.g., failure spikes require multiple events in the window).

### Option C: Production Stripe Dashboard

For production, configure the webhook URL in [Stripe Dashboard → Developers → Webhooks](https://dashboard.stripe.com/webhooks):

- **Endpoint URL:** `https://your-domain.com/webhooks/stripe`
- **Events to listen for:** Select all, or at minimum:
  - `charge.failed`
  - `charge.succeeded`
  - `invoice.finalized`
  - `invoice.payment_succeeded`
  - `invoice.payment_failed`
  - `customer.subscription.updated`

Copy the **Signing Secret** from the webhook page and set it as `STRIPE_WEBHOOK_SECRET` (via Keychain in production — see `docs/production-setup.md`).

---

## Reading the Dashboard (API)

BillingWatch exposes a JSON API at `http://localhost:8000`. Use `/docs` for the interactive Swagger UI.

### Anomaly Summary

```bash
curl http://localhost:8000/anomalies/summary
```

```json
{
  "status": "ok",
  "alerts_total": 0,
  "alerts_high": 0,
  "alerts_critical": 0,
  "last_hour": {
    "charge_failed": 0,
    "charge_total": 0,
    "failure_rate_pct": "0.0%"
  }
}
```

`status` is `"alert"` when any high or critical alerts exist, `"ok"` otherwise.

### List Recent Alerts

```bash
# Last 50 alerts (default)
curl http://localhost:8000/anomalies/

# Last 10 alerts
curl "http://localhost:8000/anomalies/?limit=10"
```

```json
{
  "anomalies": [
    {
      "detector": "charge_failure",
      "severity": "high",
      "title": "Charge Failure Spike",
      "message": "Failure rate at 22.3% over the last hour (threshold: 15%)",
      "timestamp": "2026-03-06T07:00:00Z",
      "stripe_event_id": "evt_abc123"
    }
  ],
  "total": 1,
  "shown": 1
}
```

**Severity levels:** `low` → `medium` → `high` → `critical`

### Live Metrics

```bash
# Last 1 hour (default)
curl http://localhost:8000/metrics/

# Last 24 hours
curl "http://localhost:8000/metrics/?window_hours=24"
```

```json
{
  "window_hours": 1.0,
  "total_events": 142,
  "charges": {
    "succeeded": 130,
    "failed": 12,
    "total": 142,
    "failure_rate": 0.0845,
    "failure_rate_pct": "8.5%"
  },
  "all_time_total": 8921,
  "status": "live"
}
```

### Recent Events

```bash
# Last 20 events (default)
curl http://localhost:8000/metrics/recent-events

# Last 100 events
curl "http://localhost:8000/metrics/recent-events?limit=100"
```

### Quick Reference — All Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Service health check |
| `/docs` | GET | Interactive Swagger UI |
| `/webhooks/stripe` | POST | Stripe webhook ingestion |
| `/webhooks/alerts` | GET | Recent alerts (alias) |
| `/webhooks/detectors` | GET | List all active detectors |
| `/anomalies/` | GET | List anomaly alerts |
| `/anomalies/summary` | GET | High-level status + counts |
| `/metrics/` | GET | Event counts + failure rate |
| `/metrics/recent-events` | GET | Recent raw events |

---

## Adding Custom Detectors

All detectors live in `src/detectors/` and extend `BaseDetector`. Adding your own takes 3 steps.

### Step 1: Create the detector file

```python
# src/detectors/refund_spike.py
from typing import List
from .base import Alert, BaseDetector


class RefundSpikeDetector(BaseDetector):
    """Fires when refund volume exceeds 10% of successful charges in the last hour."""

    name = "refund_spike"
    THRESHOLD = 0.10  # 10%

    def __init__(self):
        super().__init__()
        self._refund_count = 0
        self._charge_count = 0

    def process_event(self, event: dict) -> List[Alert]:
        event_type = event.get("type", "")

        if event_type == "charge.refunded":
            self._refund_count += 1
        elif event_type == "charge.succeeded":
            self._charge_count += 1

        if self._charge_count == 0:
            return []

        rate = self._refund_count / self._charge_count
        if rate > self.THRESHOLD:
            return [Alert(
                detector=self.name,
                severity="high",
                title="Refund Spike Detected",
                message=f"Refund rate at {rate:.1%} (threshold: {self.THRESHOLD:.0%}). "
                        f"{self._refund_count} refunds vs {self._charge_count} charges.",
            )]

        return []
```

### Step 2: Register it in `src/api/routes/webhooks.py`

```python
from ...detectors.refund_spike import RefundSpikeDetector

_detectors = {
    "charge_failure": ChargeFailureDetector(),
    "duplicate_charge": DuplicateChargeDetector(),
    # ... existing detectors ...
    "refund_spike": RefundSpikeDetector(),   # ← add here
}
```

### Step 3: Verify it's registered

```bash
curl http://localhost:8000/webhooks/detectors
# Should show "refund_spike" in the list
```

### BaseDetector API

```python
class BaseDetector:
    name: str                    # Unique identifier (snake_case)

    def process_event(self, event: dict) -> List[Alert]:
        """Called for every incoming Stripe event. Return [] if no alert."""
        ...
```

### Alert dataclass

```python
@dataclass
class Alert:
    detector: str        # Which detector fired
    severity: str        # "low" | "medium" | "high" | "critical"
    title: str           # Short human-readable title
    message: str         # Full description with numbers
    timestamp: str       # ISO timestamp (auto-set)
```

### Tips for detector design

- **Keep state in memory** for rate/count detectors (rolling windows reset on restart)
- **Use EventStore** (`from ...storage.event_store import EventStore`) for persistent lookups across restarts
- **Never raise exceptions** — a detector error silently drops that detector for that event; use `print()` for debug output
- **Return `[]`** when no alert fires — never return `None`

---

## Running Tests

```bash
source .venv/bin/activate

# All tests
pytest tests/ -v

# Detector unit tests only
pytest tests/test_detectors/ -v

# End-to-end flow test
pytest tests/test_e2e_charge_failure.py -v

# With coverage
pytest tests/ --cov=src --cov-report=term-missing
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `STRIPE_SECRET_KEY` | Yes (prod) | — | Stripe API key (`sk_test_…` or `sk_live_…`) |
| `STRIPE_WEBHOOK_SECRET` | Yes | — | Webhook signing secret. Set to `dev` to bypass verification |
| `APP_ENV` | No | `production` | `development` or `production` |
| `LOG_LEVEL` | No | `INFO` | Python logging level |
| `PORT` | No | `8000` | Uvicorn listen port |
| `ALERT_EMAIL_TO` | No | — | Recipient email for alerts |
| `ALERT_EMAIL_FROM` | No | — | Sender email |
| `ALERT_EMAIL_HOST` | No | — | SMTP host |
| `ALERT_EMAIL_PORT` | No | `587` | SMTP port |
| `ALERT_EMAIL_USER` | No | — | SMTP username |
| `ALERT_EMAIL_PASS` | No | — | SMTP password |
| `ALERT_WEBHOOK_URL` | No | — | URL to POST alert payloads (Slack/Discord/etc.) |

> **Production:** Never put secrets in `.env` files. Use macOS Keychain via `src/keychain.py`. See `docs/production-setup.md`.

---

*See also: [`docs/local-dev-setup.md`](local-dev-setup.md) · [`docs/production-setup.md`](production-setup.md) · [`docs/deployment-guide.md`](deployment-guide.md)*
