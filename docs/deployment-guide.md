# BillingWatch — Production Deployment Guide

## Architecture

```
Internet
   ↓
Stripe Webhooks → Cloudflare Tunnel → Mac Mini (localhost:8000) → BillingWatch
```

Your Mac Mini runs BillingWatch locally. Cloudflare Tunnel gives it a public HTTPS URL without
opening firewall ports or exposing your IP. Stripe sends webhooks to that URL.

---

## Prerequisites

- Mac Mini (M-series, macOS 26+)
- Python 3.12+
- A Cloudflare account (free tier works)
- Stripe account with live keys ready
- BillingWatch cloned to `~/Projects/BillingWatch`

---

## Step 1: Install cloudflared

```bash
brew install cloudflare/cloudflare/cloudflared
```

Verify:
```bash
cloudflared --version
```

---

## Step 2: Set up Cloudflare Tunnel

### Option A — Quick (temporary URL, good for testing)

```bash
cloudflared tunnel --url http://localhost:8000
```

Cloudflare prints a URL like `https://abc123.trycloudflare.com`. Use this in Stripe.
This URL changes every time you restart — not suitable for production.

### Option B — Persistent (permanent URL, recommended for production)

1. Log into [Cloudflare Zero Trust](https://one.dash.cloudflare.com)
2. Go to **Networks → Tunnels → Create a tunnel**
3. Name it `billingwatch`
4. Install the connector:
   ```bash
   cloudflared tunnel login
   cloudflared tunnel create billingwatch
   ```
5. Create config at `~/.cloudflared/config.yml`:
   ```yaml
   tunnel: billingwatch
   credentials-file: /Users/luckyai/.cloudflared/<TUNNEL_ID>.json

   ingress:
     - hostname: billing.yourdomain.com
       service: http://localhost:8000
     - service: http_status:404
   ```
6. Add a DNS record in Cloudflare dashboard:
   - Type: CNAME
   - Name: `billing`
   - Target: `<TUNNEL_ID>.cfargotunnel.com`
   - Proxy: On

7. Run the tunnel:
   ```bash
   cloudflared tunnel run billingwatch
   ```

Your permanent URL: `https://billing.yourdomain.com`

---

## Step 3: Configure Stripe Webhook

1. Go to [Stripe Dashboard → Developers → Webhooks](https://dashboard.stripe.com/webhooks)
2. Click **Add endpoint**
3. URL: `https://billing.yourdomain.com/webhooks/stripe`
4. Select events:
   - `charge.failed`
   - `charge.succeeded`
   - `charge.dispute.created`
   - `invoice.payment_failed`
   - `invoice.created`
   - `customer.subscription.deleted`
   - `customer.subscription.updated`
5. Click **Add endpoint**
6. Copy the **Signing secret** (`whsec_...`)

---

## Step 4: Store Secrets in Keychain

```bash
# Stripe live secret key
security add-generic-password -s BillingWatch -a STRIPE_SECRET_KEY -w sk_live_YOUR_KEY

# Stripe webhook signing secret
security add-generic-password -s BillingWatch -a STRIPE_WEBHOOK_SECRET -w whsec_YOUR_SECRET
```

---

## Step 5: Create Production Launch Script

Create `~/Projects/BillingWatch/start-production.sh`:

```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Load secrets from Keychain
export STRIPE_SECRET_KEY=$(security find-generic-password -s BillingWatch -a STRIPE_SECRET_KEY -w 2>/dev/null)
export STRIPE_WEBHOOK_SECRET=$(security find-generic-password -s BillingWatch -a STRIPE_WEBHOOK_SECRET -w 2>/dev/null)

if [ -z "$STRIPE_SECRET_KEY" ]; then
  echo "ERROR: STRIPE_SECRET_KEY not found in Keychain"
  echo "Run: security add-generic-password -s BillingWatch -a STRIPE_SECRET_KEY -w sk_live_..."
  exit 1
fi

if [ -z "$STRIPE_WEBHOOK_SECRET" ]; then
  echo "ERROR: STRIPE_WEBHOOK_SECRET not found in Keychain"
  exit 1
fi

# Load non-secret config
export APP_ENV=production
export LOG_LEVEL=INFO
export PORT=8000

# Activate venv
source .venv/bin/activate

echo "Starting BillingWatch on port $PORT..."
uvicorn src.api.main:app --host 127.0.0.1 --port "$PORT" --workers 1
```

Make it executable:
```bash
chmod +x ~/Projects/BillingWatch/start-production.sh
```

---

## Step 6: Run as a macOS Launch Agent (auto-start on login)

Create `~/Library/LaunchAgents/com.luckyai.billingwatch.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.luckyai.billingwatch</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>/Users/luckyai/Projects/BillingWatch/start-production.sh</string>
  </array>
  <key>WorkingDirectory</key>
  <string>/Users/luckyai/Projects/BillingWatch</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/tmp/billingwatch.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/billingwatch-error.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
</dict>
</plist>
```

Load it:
```bash
launchctl load ~/Library/LaunchAgents/com.luckyai.billingwatch.plist
launchctl start com.luckyai.billingwatch
```

Check it's running:
```bash
launchctl list | grep billingwatch
curl http://localhost:8000/health
```

Stop/restart:
```bash
launchctl stop com.luckyai.billingwatch
launchctl start com.luckyai.billingwatch
```

---

## Step 7: Run Cloudflare Tunnel as a Launch Agent

```bash
# Install as system service
sudo cloudflared service install
```

Or manually via Launch Agent — create `~/Library/LaunchAgents/com.luckyai.cloudflared.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.luckyai.cloudflared</string>
  <key>ProgramArguments</key>
  <array>
    <string>/opt/homebrew/bin/cloudflared</string>
    <string>tunnel</string>
    <string>run</string>
    <string>billingwatch</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/tmp/cloudflared.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/cloudflared-error.log</string>
</dict>
</plist>
```

Load:
```bash
launchctl load ~/Library/LaunchAgents/com.luckyai.cloudflared.plist
```

---

## Step 8: Verify End-to-End

```bash
# 1. Check BillingWatch is running
curl http://localhost:8000/health
# {"status": "ok"}

# 2. Check tunnel is forwarding
curl https://billing.yourdomain.com/health
# {"status": "ok"}

# 3. Send a Stripe test webhook
# In Stripe Dashboard → Webhooks → your endpoint → Send test event → charge.failed
# Check BillingWatch logs
tail -f /tmp/billingwatch.log
# Should show: "Received charge.failed event" and "charge_failure_spike detector processed event"

# 4. Check alerts endpoint
curl https://billing.yourdomain.com/webhooks/alerts
```

---

## Monitoring

```bash
# Watch live logs
tail -f /tmp/billingwatch.log

# Check process status
launchctl list | grep billingwatch

# Check tunnel status
launchctl list | grep cloudflared

# Check recent alerts
curl http://localhost:8000/webhooks/alerts | python3 -m json.tool
```

---

## Troubleshooting

| Problem | Check |
|---------|-------|
| App won't start | `cat /tmp/billingwatch-error.log` — likely missing Keychain entry |
| Stripe webhook 400/401 | Wrong `STRIPE_WEBHOOK_SECRET` in Keychain |
| Tunnel not connecting | `cloudflared tunnel info billingwatch` |
| Events not reaching app | Check Stripe webhook delivery logs in dashboard |
| Detector not firing | Thresholds may need tuning — check `src/detectors/` configs |

---

## Security Checklist

- [ ] `STRIPE_SECRET_KEY` in Keychain, not `.env`
- [ ] `STRIPE_WEBHOOK_SECRET` in Keychain, not `.env`
- [ ] `.env` not committed to git (check `.gitignore`)
- [ ] BillingWatch bound to `127.0.0.1` (not `0.0.0.0`) — tunnel handles public access
- [ ] LuLu firewall: only cloudflared needs outbound access
- [ ] Stripe webhook signature validation enabled (not `STRIPE_WEBHOOK_SECRET=dev`)
