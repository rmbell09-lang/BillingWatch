# BillingWatch — Local Dev Setup

## Quick Start (without Docker)

```bash
# 1. Create and activate venv
cd ~/Projects/BillingWatch
/opt/homebrew/bin/python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install fastapi uvicorn stripe python-dotenv

# 3. Run in dev mode (signature verification bypassed when STRIPE_WEBHOOK_SECRET=dev)
STRIPE_WEBHOOK_SECRET=dev uvicorn src.api.main:app --reload --port 8000
```

## Test Webhook Dry Run

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

## Docker Setup (requires Docker Desktop)

Docker is **not installed** on the Mac Mini. To use Docker:
1. Install Docker Desktop from https://docker.com
2. Copy `.env.example` to `.env` and fill in real values
3. Run `docker-compose up --build`
4. App reachable at http://localhost:8000/health

## Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/docs` | GET | Swagger UI |
| `/webhooks/stripe` | POST | Stripe event ingestion |
| `/webhooks/alerts` | GET | Recent alerts |
| `/webhooks/detectors` | GET | Registered detectors |

## Detectors (7 active)

- `charge_failure` — failed charge rate spikes
- `duplicate_charge` — same customer charged twice in short window
- `fraud_spike` — disputed/fraudulent charge rate
- `negative_invoice` — negative invoice amounts
- `revenue_drop` — sudden MRR drops
- `silent_lapse` — subscription lapses without cancellation
- `webhook_lag` — delayed or stalled webhook delivery

## Notes

- `.env` is gitignored — never commit secrets
- `STRIPE_WEBHOOK_SECRET=dev` bypasses signature verification (local/test only)
- Full PostgreSQL + Redis integration coming in v2
