# 🔍 BillingWatch — Self-Hosted Stripe Billing Anomaly Detector

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: Passing](https://img.shields.io/badge/tests-passing-brightgreen.svg)]()
[![Self-Hosted](https://img.shields.io/badge/self--hosted-yes-blueviolet.svg)]()
[![Stripe](https://img.shields.io/badge/stripe-webhook--powered-635bff.svg)](https://stripe.com/)

**Catch billing bugs, dunning failures, and fraud before they hit your churn metrics — entirely on your own machine.**

BillingWatch listens to your Stripe webhook stream and runs 7 real-time anomaly detectors against every event. Duplicate charges, revenue drops, fraud spikes, silent subscription lapses — detected and alerted in seconds. No cloud subscription. No SaaS fees. No data leaving your server.

---

## 🤔 Who Is This For?

- **SaaS founders** who want billing QA without paying for another tool
- **Indie developers** using Stripe who've been burned by silent billing failures
- **Privacy-conscious teams** who don't want their revenue data on someone else's server
- **DevOps engineers** who need webhook observability without a full APM stack

---

## ✨ What It Detects

| Detector | What It Catches | Severity |
|----------|----------------|----------|
| `charge_failure_spike` | Failure rate > 15% over 1 hour — gateway issue or card BIN attack | 🔴 High |
| `duplicate_charge` | Same customer charged twice within 5 min — idempotency bug | 🚨 Critical |
| `fraud_spike` | Dispute/chargeback rate exceeds threshold — active fraud campaign | 🚨 Critical |
| `negative_invoice` | Invoice total < 0 — broken promo stacking or discount bug | 🟡 Medium |
| `revenue_drop` | MRR > 15% below 7-day rolling average — silent churn or billing break | 🔴 High |
| `silent_lapse` | Active subscription with no successful payment in period | 🟡 Medium |
| `webhook_lag` | Events arriving > 10 min late — Stripe delivery degradation | 🟢 Low |

When a detector fires, BillingWatch sends alerts via email and/or outbound webhook.

---

## 🚀 Quick Start

### Requirements
- Python 3.9+
- A Stripe account (test mode is fine)
- Stripe CLI (optional — for local webhook forwarding)

### Install

```bash
git clone https://github.com/rmbell09-lang/BillingWatch.git
cd BillingWatch
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
```

Minimum config for local dev:
```env
STRIPE_SECRET_KEY=sk_test_PLACEHOLDER
STRIPE_WEBHOOK_SECRET=dev
APP_ENV=development
LOG_LEVEL=DEBUG
PORT=8000
```

> **Note:** `STRIPE_WEBHOOK_SECRET=dev` bypasses signature verification. Never use in production.

### Run

```bash
source .venv/bin/activate
STRIPE_WEBHOOK_SECRET=dev uvicorn src.api.main:app --reload --port 8000
```

### Verify

```bash
curl http://localhost:8000/health
# {"status": "ok"}

curl http://localhost:8000/webhooks/detectors
# Lists all 7 registered detectors
```

### Send a Test Event

```bash
curl -s -X POST localhost:8000/webhooks/stripe \
  -H 'Content-Type: application/json' \
  -H 'Stripe-Signature: dev' \
  -d '{
    "id": "evt_test_001",
    "type": "charge.failed",
    "created": 1709599200,
    "data": {"object": {"id": "ch_001", "customer": "cus_001", "amount": 2999}}
  }'
```

Or with Stripe CLI for real test events:
```bash
stripe listen --forward-to localhost:8000/webhooks/stripe
stripe trigger charge.failed
```

---

## 📡 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/docs` | GET | Interactive Swagger UI |
| `/webhooks/stripe` | POST | Stripe event ingestion |
| `/webhooks/alerts` | GET | Recent anomaly alerts |
| `/webhooks/detectors` | GET | Registered detectors list |
| `/metrics` | GET | `total_events`, `events_by_type`, `uptime_seconds`, `detector_count` |
| `/metrics?window_hours=N` | GET | Rolling window metrics (0.1–168h) |
| `/metrics/detectors` | GET | Per-detector alert counts + severity |
| `/metrics/recent-events` | GET | Most recent webhook events |

---

## 🏗️ Architecture

```
Stripe Webhooks
      │
      ▼
 FastAPI (port 8000)
      │
      ├─── Signature Validation (Stripe-Signature header)
      │
      ├─── Event Store (SQLite / PostgreSQL)
      │
      └─── Detector Pipeline (parallel evaluation)
                │
                ├─── charge_failure_spike
                ├─── duplicate_charge
                ├─── fraud_spike
                ├─── negative_invoice
                ├─── revenue_drop
                ├─── silent_lapse
                └─── webhook_lag
                          │
                          ▼
                   Alert Dispatch
                   ├─── Email (SMTP)
                   └─── Outbound Webhook
```

**Stack:** Python 3.9+ · FastAPI · SQLite (dev) / PostgreSQL (prod) · Redis · APScheduler · Stripe SDK

---

## 🧪 Running Tests

```bash
source .venv/bin/activate
pytest tests/ -v

# Detector unit tests only
pytest tests/test_detectors/ -v

# With coverage
pytest tests/ --cov=src --cov-report=term-missing
```

---

## 🔧 Adding a Custom Detector

Extend `BaseDetector` from `src/detectors/base.py`:

```python
from .base import Alert, BaseDetector

class MyDetector(BaseDetector):
    name = "my_detector"

    def process_event(self, event: dict):
        if event.get("type") == "some.stripe.event":
            return [Alert(
                detector=self.name,
                severity="medium",
                title="Something happened",
                message="Details here"
            )]
        return []
```

Register it in `src/api/main.py` startup. Done.

---

## 🔒 Production Deployment

See [`docs/production-setup.md`](docs/production-setup.md) for:
- Stripe live key setup via macOS Keychain
- Cloudflare Tunnel for webhook exposure (no open ports)
- PostgreSQL + Redis configuration
- Pre-launch security checklist

**Never put live Stripe keys in `.env` files.** Use Keychain or a secrets manager.

---

## 📁 Project Structure

```
BillingWatch/
├── src/
│   ├── api/               # FastAPI app + routes
│   ├── detectors/         # 7 anomaly detectors + BaseDetector
│   ├── storage/           # SQLite/Postgres event persistence
│   ├── workers/           # Async processing + APScheduler
│   ├── alerting/          # Email + webhook alert delivery
│   ├── models/            # SQLAlchemy models + Pydantic schemas
│   └── stripe_client.py   # Stripe SDK wrapper
├── tests/                 # Unit + E2E tests
├── docs/                  # Setup guides + spec
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 🗺️ Roadmap

### v1.1 (In Progress)
- 📧 **Email Digest** — daily/weekly anomaly summary (endpoint live, SMTP config needed)
- ☁️ **Render.com 1-Click Deploy** — `render.yaml` + deploy button
- 🔍 **Webhook Event Explorer UI** — searchable, filterable event log

### v1.2 (Planned)
- 📊 **Grafana Dashboard** — pre-built anomaly trend dashboard
- 🔔 **Slack/Discord Alerts** — native integrations
- 🧪 **Test Mode Replay** — replay historical events without live webhooks

---



---

## 🛠️ More Dev Tools

Built by the same maker — if you're interested in algorithmic trading:

**[TradeSight — AI Paper Trading Strategy Lab →](https://qcautonomous.gumroad.com/l/tradesight)** — Python trading bot with overnight strategy tournaments, RSI confluence, and Alpaca integration.

## License

MIT — see [LICENSE](LICENSE)

---

*Built by an indie maker who got burned by a silent dunning failure. Stripe is great — but it doesn't tell you when things go wrong until it's too late.*
