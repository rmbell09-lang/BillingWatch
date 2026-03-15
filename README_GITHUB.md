# BillingWatch

**Open-source billing anomaly detection for Stripe.**

Catch phantom subscriptions, price drift, duplicate charges, and 7 other billing bugs before they cost you money.

![Python](https://img.shields.io/badge/python-3.10+-blue) ![Tests](https://img.shields.io/badge/tests-126%20passing-green) ![License](https://img.shields.io/badge/license-MIT-brightgreen)

## What It Does

BillingWatch monitors your Stripe webhooks in real-time and flags billing anomalies. It catches the bugs that slip through — the ones that don't crash your app but silently drain revenue.

**10 built-in detectors:**
- Phantom subscriptions
- Price drift on plan changes
- Duplicate charge events
- Failed payment cascades
- Usage metering gaps
- Unexpected refund patterns
- Trial-to-paid conversion anomalies
- Discount abuse detection
- Currency mismatch alerts
- Invoice amount outliers

## Quick Start

```bash
# Clone and install
git clone https://github.com/qcautonomous/billingwatch.git
cd billingwatch
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your Stripe webhook secret

# Run
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

Point your Stripe webhook at `https://your-server.com/webhook` and BillingWatch starts monitoring immediately.

## API

```bash
# Health check
curl http://localhost:8000/health

# View detected anomalies
curl http://localhost:8000/anomalies

# Detector metrics (last 24h)
curl http://localhost:8000/metrics/detectors?window_hours=24

# Visual dashboard
open http://localhost:8000/dashboard
```

## Alerts

BillingWatch sends alerts when anomalies are detected:

- **Email (SMTP)** — built-in, configure in `.env`
- **Slack** — set `SLACK_WEBHOOK_URL`
- **Discord** — set `DISCORD_WEBHOOK_URL`

## Self-Hosted

BillingWatch runs on your infrastructure. No data leaves your server. No cloud dependency. SQLite database — zero external deps.

**Requirements:** Python 3.10+, that's it.

## Dashboard

Dark-themed visual dashboard with:
- Detector alert bar chart
- Severity breakdown (doughnut)
- Auto-refresh (30s)
- Recent anomalies list

Access at `GET /dashboard` when running.

## API Docs

Full API documentation: [API_DOCS.md](docs/API_DOCS.md)

## Contributing

PRs welcome. Run tests with:

```bash
python -m pytest tests/ -v
```

126 tests, all passing.

## License

MIT
