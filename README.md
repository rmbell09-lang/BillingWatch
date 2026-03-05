# BillingWatch 🔍

**Automated billing QA and anomaly detection for Stripe-powered SaaS.**

Catch billing bugs, dunning failures, and fraud attempts before they show up in your bank account or churn metrics.

## What it does

Monitors Stripe webhook events in real-time and detects:

- 💥 Charge failure spikes (>15% failure rate)
- 👻 Silent subscription lapses (active sub, no payment)
- 📉 Revenue drops (>15% below 7-day avg)
- 🔁 Duplicate charges (same customer/amount within 5 min)
- ➖ Negative invoices (broken promo code stacking)
- 🐢 Webhook processing lag (events older than 10 min)
- 🚨 Suspicious charge volume (card testing / fraud)

## Stack

Python 3.12 · FastAPI · PostgreSQL · Redis · APScheduler · Docker

## Quick Start

```bash
cp .env.example .env
# Fill in STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, etc.
docker-compose up -d
```

## Project Structure

```
src/
├── api/          # FastAPI routes
├── detectors/    # 7 anomaly detectors
├── workers/      # Event processor + scheduler
├── models/       # DB models + schemas
└── alerting/     # Email + webhook alerts
```

## Docs

- [Full Spec](docs/SPEC.md)
- [Stripe API Research](docs/stripe-api.md)

---

Built by Lucky · BillingWatch MVP v1.0
