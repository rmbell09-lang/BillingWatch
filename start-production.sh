#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "[BillingWatch] Starting production server..."

# Pull secrets from Keychain
export STRIPE_SECRET_KEY=$(security find-generic-password -s BillingWatch -a STRIPE_SECRET_KEY -w 2>/dev/null)
export STRIPE_WEBHOOK_SECRET=$(security find-generic-password -s BillingWatch -a STRIPE_WEBHOOK_SECRET -w 2>/dev/null)

[ -z "$STRIPE_SECRET_KEY" ] && echo "ERROR: STRIPE_SECRET_KEY missing from Keychain" && exit 1
[ -z "$STRIPE_WEBHOOK_SECRET" ] && echo "WARNING: STRIPE_WEBHOOK_SECRET not set (webhooks disabled)"

# Optional alerting
export ALERT_WEBHOOK_URL=$(security find-generic-password -s BillingWatch -a ALERT_WEBHOOK_URL -w 2>/dev/null || echo '')

export APP_ENV=production
export LOG_LEVEL=INFO
export PORT=8000
export DATABASE_URL="sqlite:///./billingwatch.db"

echo "[BillingWatch] Secrets loaded. Starting on port $PORT..."
source .venv/bin/activate
exec uvicorn src.api.main:app --host 127.0.0.1 --port "$PORT" --workers 1
