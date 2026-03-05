# BillingWatch — MVP Technical Specification
*Version: 1.0 | Author: Lucky | Date: 2026-03-05*

---

## Overview

BillingWatch is an automated billing QA and anomaly detection system for SaaS businesses using Stripe. It monitors billing events in real-time, detects anomalies, and alerts operators before revenue leaks or billing errors become customer problems.

**Core value prop:** Catch billing bugs, dunning failures, and fraud attempts before they show up in the bank account or churn metrics.

---

## Problem Statement

Stripe is powerful but silent. Businesses using it don't know when:
- A charge silently fails but the subscription stays active
- A promo code causes negative charges
- Subscription revenue drops 20% overnight
- A customer gets double-charged
- Webhook processing falls behind and events get missed

BillingWatch is the watchdog layer that Stripe doesn't provide.

---

## MVP Scope

### In scope
- Stripe webhook ingestion
- 7 core anomaly detectors (see below)
- Alert delivery (email + webhook)
- Simple dashboard (last 24h anomalies, revenue metrics)
- REST API for manual queries

### Out of scope (v2)
- Multi-PSP support (Braintree, PayPal)
- ML-based anomaly detection (rule-based only in MVP)
- Slack/PagerDuty native integrations (webhook covers it)
- Custom detector configuration UI

---

## Core Anomaly Detectors (7)

### 1. Charge Failure Spike
- **Trigger:** Charge failure rate exceeds 15% over rolling 1-hour window
- **Signals:** `charge.failed` events
- **Alert:** "Charge failure rate at X% (baseline: Y%)"
- **Why it matters:** Payment processor issues, card BIN attacks, bad UX

### 2. Silent Subscription Lapse
- **Trigger:** Subscription marked active but no successful charge in > (billing_interval + 3 days)
- **Signals:** Cross-reference `customer.subscription.updated` with `invoice.payment_succeeded`
- **Alert:** "Customer [ID] subscription active but no payment in N days"
- **Why it matters:** Revenue leakage — customer using product without paying

### 3. Revenue Anomaly (Sudden Drop)
- **Trigger:** Daily MRR movement > 15% below 7-day rolling average
- **Signals:** Aggregate `invoice.payment_succeeded` amounts
- **Alert:** "Revenue down X% vs 7-day avg — investigate"
- **Why it matters:** Early churn signal or billing system failure

### 4. Duplicate Charge Detection
- **Trigger:** Same customer, same amount, same description within 5-minute window
- **Signals:** `charge.succeeded` events
- **Alert:** "Possible duplicate charge: Customer [ID] charged $X twice in N seconds"
- **Why it matters:** Direct financial harm + support ticket flood

### 5. Negative Invoice Amount
- **Trigger:** Any invoice with total_amount < 0 finalized
- **Signals:** `invoice.finalized` events
- **Alert:** "Negative invoice detected: Invoice [ID] for Customer [ID] = $-X"
- **Why it matters:** Promo code stacking bugs, discount misconfiguration

### 6. Webhook Processing Lag
- **Trigger:** Unprocessed events in queue older than 10 minutes
- **Signals:** Internal queue depth + event timestamps
- **Alert:** "Webhook lag: X events unprocessed, oldest is N minutes old"
- **Why it matters:** Silent failures — events get missed, state goes stale

### 7. Suspicious Volume Spike (Fraud Indicator)
- **Trigger:** New customer charges > 3 times in 60 minutes, or total > $500 from one card in 24h
- **Signals:** `charge.succeeded` with card fingerprint
- **Alert:** "Suspicious activity: Card [fingerprint] charged $X in N transactions today"
- **Why it matters:** Card testing attacks, friendly fraud

---

## Data Model

### PostgreSQL Schema

```sql
-- Raw Stripe events (append-only log)
CREATE TABLE stripe_events (
  id              TEXT PRIMARY KEY,           -- Stripe event ID
  type            TEXT NOT NULL,              -- e.g. "charge.succeeded"
  created_at      TIMESTAMPTZ NOT NULL,       -- Stripe event timestamp
  received_at     TIMESTAMPTZ DEFAULT NOW(),  -- When we got it
  data            JSONB NOT NULL,             -- Full event payload
  processed       BOOLEAN DEFAULT FALSE,
  processing_error TEXT
);
CREATE INDEX idx_stripe_events_type ON stripe_events(type);
CREATE INDEX idx_stripe_events_created ON stripe_events(created_at);

-- Detected anomalies
CREATE TABLE anomalies (
  id              SERIAL PRIMARY KEY,
  detector_id     TEXT NOT NULL,              -- e.g. "duplicate_charge"
  severity        TEXT NOT NULL,              -- critical | warning | info
  customer_id     TEXT,                       -- Stripe customer ID if applicable
  description     TEXT NOT NULL,
  event_ids       TEXT[],                     -- Stripe event IDs that triggered this
  detected_at     TIMESTAMPTZ DEFAULT NOW(),
  acknowledged    BOOLEAN DEFAULT FALSE,
  acknowledged_at TIMESTAMPTZ,
  acknowledged_by TEXT
);
CREATE INDEX idx_anomalies_detected ON anomalies(detected_at);
CREATE INDEX idx_anomalies_acknowledged ON anomalies(acknowledged);

-- Aggregated revenue snapshots (hourly)
CREATE TABLE revenue_snapshots (
  id              SERIAL PRIMARY KEY,
  snapshot_at     TIMESTAMPTZ NOT NULL,
  mrr             NUMERIC(12,2),
  charges_count   INT,
  charges_total   NUMERIC(12,2),
  failures_count  INT,
  failure_rate    NUMERIC(5,4)
);

-- Alert delivery log
CREATE TABLE alert_deliveries (
  id              SERIAL PRIMARY KEY,
  anomaly_id      INT REFERENCES anomalies(id),
  channel         TEXT NOT NULL,              -- email | webhook | slack
  destination     TEXT NOT NULL,
  sent_at         TIMESTAMPTZ DEFAULT NOW(),
  status          TEXT NOT NULL,              -- sent | failed
  error           TEXT
);
```

---

## Stripe Integration

### Webhook Ingestion

BillingWatch registers as a Stripe webhook endpoint receiving all events.

**Critical events to process:**

| Event | Detector(s) |
|---|---|
| `charge.succeeded` | Duplicate charge, fraud spike |
| `charge.failed` | Charge failure spike |
| `invoice.payment_succeeded` | Revenue tracking, silent lapse |
| `invoice.payment_failed` | Charge failure spike |
| `invoice.finalized` | Negative invoice |
| `customer.subscription.updated` | Silent lapse |
| `customer.subscription.deleted` | Revenue drop |

**Webhook security:**
```python
import stripe

def verify_webhook(payload: bytes, sig_header: str) -> stripe.Event:
    return stripe.Webhook.construct_event(
        payload, sig_header, os.environ["STRIPE_WEBHOOK_SECRET"]
    )
```

### Stripe API Queries (for backfill + enrichment)

```python
# List recent charges for a customer
stripe.Charge.list(customer=customer_id, limit=100, created={"gte": since_ts})

# Get subscription status
stripe.Subscription.retrieve(subscription_id)

# List all active subscriptions (for silent lapse scan)
stripe.Subscription.list(status="active", limit=100)
```

---

## API Design

### Endpoints

```
GET  /api/health                     # Service health
GET  /api/anomalies                  # List anomalies (filters: since, severity, detector, unacked)
GET  /api/anomalies/:id              # Get single anomaly
POST /api/anomalies/:id/acknowledge  # Mark acknowledged
GET  /api/metrics                    # Revenue metrics (last 24h, 7d, 30d)
GET  /api/metrics/revenue            # MRR breakdown
GET  /api/metrics/charges            # Charge success/failure rates
POST /api/webhooks/stripe            # Stripe webhook receiver
GET  /api/detectors                  # List detectors + their status
POST /api/detectors/:id/run          # Manually trigger a detector
```

### Example Response

```json
{
  "anomalies": [
    {
      "id": 42,
      "detector_id": "duplicate_charge",
      "severity": "critical",
      "customer_id": "cus_xxx",
      "description": "Possible duplicate charge: Customer cus_xxx charged $29.00 twice in 47 seconds",
      "event_ids": ["evt_abc", "evt_def"],
      "detected_at": "2026-03-05T18:23:11Z",
      "acknowledged": false
    }
  ],
  "total": 1,
  "unacknowledged": 1
}
```

---

## Tech Stack

| Layer | Choice | Rationale |
|---|---|---|
| Language | Python 3.12 | Stripe SDK, fast to build |
| Web framework | FastAPI | Async, auto-docs, pydantic validation |
| Database | PostgreSQL | JSONB for event storage, proven reliability |
| Queue | Redis (list-based) | Webhook events queue before processing |
| Scheduler | APScheduler | Periodic detector runs (revenue checks) |
| Stripe SDK | stripe-python | Official, well-maintained |
| Alerting | SMTP + HTTP webhooks | No external dependencies |
| Dashboard | Jinja2 + htmx | Minimal JS, server-rendered |
| Deployment | Docker Compose | Single-host MVP |

---

## Architecture

```
Stripe ──webhooks──▶ FastAPI /webhooks/stripe
                          │
                          ▼
                     Redis Queue
                          │
                          ▼
                   Event Processor
                   (async worker)
                          │
                    ┌─────┴─────┐
                    ▼           ▼
             PostgreSQL    7 Detectors
             (events)          │
                               ▼
                         Anomaly Table
                               │
                               ▼
                        Alert Dispatcher
                        (email / webhook)
                               │
                               ▼
                         Dashboard API
```

**Key design decisions:**
- Webhook receiver is fire-and-forget (200 immediately, process async)
- Event processor is idempotent (Stripe event ID as PK)
- Detectors run on every relevant event + scheduled periodic scans
- PostgreSQL JSONB stores full Stripe event payload for debugging

---

## Directory Structure

```
BillingWatch/
├── src/
│   ├── api/
│   │   ├── main.py          # FastAPI app
│   │   ├── routes/
│   │   │   ├── anomalies.py
│   │   │   ├── metrics.py
│   │   │   └── webhooks.py
│   ├── detectors/
│   │   ├── base.py          # BaseDetector class
│   │   ├── charge_failure.py
│   │   ├── silent_lapse.py
│   │   ├── revenue_drop.py
│   │   ├── duplicate_charge.py
│   │   ├── negative_invoice.py
│   │   ├── webhook_lag.py
│   │   └── fraud_spike.py
│   ├── workers/
│   │   ├── event_processor.py
│   │   └── scheduler.py
│   ├── models/
│   │   ├── database.py
│   │   └── schemas.py
│   ├── alerting/
│   │   ├── email.py
│   │   └── webhook.py
│   └── stripe_client.py
├── tests/
│   ├── test_detectors/
│   └── test_api/
├── docs/
│   ├── SPEC.md              # This file
│   └── stripe-api.md
├── research/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

## Environment Variables

```bash
# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/billingwatch

# Redis
REDIS_URL=redis://localhost:6379/0

# Alerting
ALERT_EMAIL_FROM=alerts@yourdomain.com
ALERT_EMAIL_TO=you@yourdomain.com
SMTP_HOST=smtp.yourdomain.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASS=...

# Optional: webhook alerts
ALERT_WEBHOOK_URL=https://hooks.yourdomain.com/billingwatch
```

---

## MVP Success Criteria

- [ ] Ingests Stripe webhooks reliably (zero dropped events)
- [ ] All 7 detectors operational
- [ ] Alerts delivered within 60 seconds of detection
- [ ] Dashboard shows last 24h anomalies + revenue chart
- [ ] Can replay historical events for testing
- [ ] Zero false positives on a normal day's traffic

---

## Build Order

1. Project skeleton + Docker setup (Task 79)
2. Stripe webhook ingestion + event storage
3. Event processor worker
4. Detector #1: duplicate charge (simplest)
5. Detector #2: charge failure spike
6. Alert delivery (email)
7. Remaining 5 detectors
8. Dashboard
9. Tests

---

*Spec written by Lucky. Ready to build once Ray greenlights.*
