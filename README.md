# BillingWatch 🔍

**Automated billing QA and anomaly detection for Stripe-powered SaaS.**

Catch billing bugs, dunning failures, and fraud attempts in real-time — before they show up in your churn metrics or bank account.

---

## What It Does

BillingWatch listens to your Stripe webhook stream and runs 7 anomaly detectors against every event:

| Detector | Trigger | Severity |
|----------|---------|----------|
| `charge_failure_spike` | Failure rate > 15% over 1 hour | High |
| `duplicate_charge` | Same customer/amount charged twice within 5 min | Critical |
| `fraud_spike` | Dispute/fraud rate exceeds threshold | Critical |
| `negative_invoice` | Invoice total < 0 (broken promo stacking) | Medium |
| `revenue_drop` | MRR > 15% below 7-day rolling average | High |
| `silent_lapse` | Active subscription with no successful payment | Medium |
| `webhook_lag` | Events arriving > 10 min after creation | Low |

When a detector fires, BillingWatch sends alerts via email and/or webhook.

---

## Stack

- **Python 3.12** + **FastAPI** — async webhook ingestion
- **SQLite** (dev) / **PostgreSQL** (prod) — event storage
- **Redis** + **APScheduler** — background processing and scheduled checks
- **Stripe SDK** — signature validation and event parsing
- **macOS Keychain** — production secret storage (no plaintext keys)

---

## Quick Start (Local Dev — No Docker Required)

### Prerequisites
- Python 3.9+
- A Stripe account (test mode is fine)
- Stripe CLI (optional, for local webhook forwarding)

### 1. Clone and set up environment

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

Edit `.env` — for dev, you only need:
```
STRIPE_SECRET_KEY=sk_test_PLACEHOLDER
STRIPE_WEBHOOK_SECRET=dev
APP_ENV=development
LOG_LEVEL=DEBUG
PORT=8000
```

> **Note:** When `STRIPE_WEBHOOK_SECRET=dev`, signature verification is bypassed. Never use this in production.

### 3. Start the app

```bash
source .venv/bin/activate
STRIPE_WEBHOOK_SECRET=dev uvicorn src.api.main:app --reload --port 8000
```

You should see:
```
INFO:     Started server process
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 4. Verify it's running

```bash
curl http://localhost:8000/health
# {"status": "ok"}

curl http://localhost:8000/webhooks/detectors
# Lists all 7 registered detectors
```

### 5. Send a test webhook event

Without Stripe CLI:
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
        "id": "ch_001",
        "customer": "cus_001",
        "amount": 2999
      }
    }
  }'
```

With Stripe CLI (forwards real test events):
```bash
stripe listen --forward-to localhost:8000/webhooks/stripe
stripe trigger charge.failed
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check — `{"status": "ok"}` |
| `/docs` | GET | Interactive Swagger UI |
| `/webhooks/stripe` | POST | Stripe event ingestion endpoint |
| `/webhooks/alerts` | GET | Recent anomaly alerts |
| `/webhooks/detectors` | GET | List registered detectors |
| `/metrics` | GET | Event metrics: `total_events`, `events_by_type`, `uptime_seconds`, `detector_count` |
| `/metrics?window_hours=N` | GET | Same as above over a custom rolling window (0.1–168 hours) |
| `/metrics/detectors` | GET | Per-detector alert counts and severity breakdown |
| `/metrics/recent-events` | GET | Most recent webhook events |

---

## Project Structure

```
BillingWatch/
├── src/
│   ├── api/
│   │   ├── main.py              # FastAPI app + startup
│   │   └── routes/
│   │       ├── webhooks.py      # Stripe webhook ingestion
│   │       ├── anomalies.py     # Alert history endpoints
│   │       └── metrics.py       # Stats endpoints
│   ├── detectors/
│   │   ├── base.py              # BaseDetector + Alert dataclass
│   │   ├── charge_failure.py    # Charge failure spike
│   │   ├── duplicate_charge.py  # Duplicate charge detection
│   │   ├── fraud_spike.py       # Fraud/dispute rate
│   │   ├── negative_invoice.py  # Negative invoices
│   │   ├── revenue_drop.py      # MRR drop detection
│   │   ├── silent_lapse.py      # Silent subscription lapse
│   │   └── webhook_lag.py       # Webhook delivery lag
│   ├── storage/
│   │   └── event_store.py       # SQLite/Postgres event persistence
│   ├── workers/
│   │   ├── event_processor.py   # Async event processing
│   │   └── scheduler.py         # APScheduler for periodic checks
│   ├── alerting/
│   │   ├── email.py             # Email alerts via SMTP
│   │   └── webhook.py           # Webhook alert delivery
│   ├── models/
│   │   ├── database.py          # SQLAlchemy models
│   │   └── schemas.py           # Pydantic schemas
│   ├── stripe_client.py         # Stripe SDK wrapper
│   └── keychain.py              # macOS Keychain secret access
├── tests/
│   ├── test_detectors/          # Unit tests for all 7 detectors
│   ├── test_alerting.py         # Alert delivery tests
│   └── test_e2e_charge_failure.py  # End-to-end flow test
├── docs/
│   ├── local-dev-setup.md       # Detailed dev environment setup
│   ├── production-setup.md      # Production deployment + Keychain guide
│   └── SPEC.md                  # Full product specification
├── webhook_handler.py           # Standalone webhook testing utility
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Running Tests

```bash
source .venv/bin/activate
pytest tests/ -v

# Run just detector tests
pytest tests/test_detectors/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing
```

---

## Customizing Detectors

Each detector extends `BaseDetector` from `src/detectors/base.py`. To add a new detector:

1. Create `src/detectors/my_detector.py` extending `BaseDetector`
2. Implement `process_event(event: dict) -> List[Alert]`
3. Register it in `src/api/main.py` startup

Example:
```python
from .base import Alert, BaseDetector

class MyDetector(BaseDetector):
    name = "my_detector"

    def process_event(self, event: dict):
        if event.get("type") == "some.event":
            return [Alert(
                detector=self.name,
                severity="medium",
                title="Something happened",
                message="Details here"
            )]
        return []
```

---

## Production Deployment

See [`docs/production-setup.md`](docs/production-setup.md) for the full guide covering:
- Stripe live key setup
- macOS Keychain secret storage
- Cloudflare Tunnel for webhook exposure
- Environment configuration
- Pre-launch checklist

**Never put live Stripe keys in `.env` files.** Always use Keychain.

---

## Security Notes

- Stripe webhook signatures are validated on every request (bypassed only when `STRIPE_WEBHOOK_SECRET=dev`)
- Production secrets stored in macOS Keychain via `src/keychain.py`
- No API keys in version control — `.env` is gitignored
- Database credentials use Keychain in production

---

## 🔗 Related Tools

| Tool | Description |
|------|-------------|
| [TradeSight](https://github.com/rmbell09-lang/tradesight) | AI-driven Python paper trading system — strategy tournaments + live Alpaca integration |

---

## License

Private — Ray's project. Not open source.

---

## Roadmap

BillingWatch is under active development. Here's what's coming:

### v1.1 (In Progress)
- **📧 SMTP Email Digest** — daily/weekly summary of anomaly activity, delivered to your inbox
- **☁️ Render.com 1-Click Deploy** — `render.yaml` + deploy button for zero-config cloud hosting
- **🔍 Webhook Event Explorer UI** — searchable, filterable event log with detector metadata

### v1.2 (Planned)
- **📊 Grafana Dashboard** — pre-built dashboard for anomaly trends and alert history
- **🔔 Slack/Discord Alerts** — native integrations beyond email webhooks
- **🧪 Stripe Test Mode Replay** — replay historical events against detectors without a live webhook stream

### Future
- Multi-account support (multiple Stripe accounts per instance)
- Alert suppression rules (silence known-good patterns)
- Custom detector SDK + plugin marketplace

---

*Want a feature? Open an issue or [drop a message](https://github.com/rmbell09-lang/BillingWatch/issues).*
