#!/usr/bin/env bash
# BillingWatch Landing Page — Wrangler Deploy Script
# Usage: CLOUDFLARE_API_TOKEN=xxx bash deploy_wrangler.sh
# Requires: wrangler at /usr/local/bin/wrangler (already installed)

set -e

LANDING_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_NAME="billingwatch"

if [ -z "$CLOUDFLARE_API_TOKEN" ]; then
  echo "ERROR: Set CLOUDFLARE_API_TOKEN first."
  echo "Get it at: dash.cloudflare.com -> My Profile -> API Tokens -> Create Token (Pages:Edit)"
  exit 1
fi

echo "[1/2] Deploying $LANDING_DIR to Cloudflare Pages project: $PROJECT_NAME"
/usr/local/bin/wrangler pages deploy "$LANDING_DIR" \
  --project-name="$PROJECT_NAME" \
  --commit-dirty=true

echo ""
echo "[2/2] Deploy complete!"
echo "Landing page: https://${PROJECT_NAME}.pages.dev"
echo ""
echo "Next steps:"
echo "  1. Test: curl -X POST https://${PROJECT_NAME}.pages.dev/subscribe -H 'Content-Type: application/json' -d '{\"email\":\"test@example.com\",\"name\":\"Test\"}'"
echo "  2. Update BETA_OUTREACH.md with live URL"
echo "  3. Post Show HN Tuesday 9 AM ET"
