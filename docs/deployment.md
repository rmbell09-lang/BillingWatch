# BillingWatch — Production Deployment

Deploy BillingWatch on Mac Mini with Cloudflare Tunnel for Stripe webhook ingestion.
No open ports. No exposed IPs. Just a persistent HTTPS URL Stripe can reach.

---

## Architecture

```
Stripe → Cloudflare Tunnel → Mac Mini :8000 → BillingWatch
```

---

## Prerequisites

- macOS Mac Mini (M-series recommended)
- Python 3.12+ with `.venv` set up
- Cloudflare account (free tier works)
- Stripe live keys ready

---

## 1. Secrets in Keychain

Never put live keys in `.env`. Store them in macOS Keychain:

```bash
security add-generic-password -s BillingWatch -a STRIPE_SECRET_KEY -w sk_live_YOUR_KEY
security add-generic-password -s BillingWatch -a STRIPE_WEBHOOK_SECRET -w whsec_YOUR_SECRET
```

Verify:
```bash
security find-generic-password -s BillingWatch -a STRIPE_SECRET_KEY -w
```

---

## 2. Production Launch Script

Create `~/Projects/BillingWatch/start-production.sh`:

```bash
#!/bin/bash
set -e
cd "$(dirname "$0")"

# Pull secrets from Keychain
export STRIPE_SECRET_KEY=$(security find-generic-password -s BillingWatch -a STRIPE_SECRET_KEY -w 2>/dev/null)
export STRIPE_WEBHOOK_SECRET=$(security find-generic-password -s BillingWatch -a STRIPE_WEBHOOK_SECRET -w 2>/dev/null)

[ -z "$STRIPE_SECRET_KEY" ] && echo "ERROR: STRIPE_SECRET_KEY missing from Keychain" && exit 1
[ -z "$STRIPE_WEBHOOK_SECRET" ] && echo "ERROR: STRIPE_WEBHOOK_SECRET missing from Keychain" && exit 1

export APP_ENV=production
export LOG_LEVEL=INFO
export PORT=8000

source .venv/bin/activate
exec uvicorn src.api.main:app --host 127.0.0.1 --port "$PORT" --workers 1
```

```bash
chmod +x ~/Projects/BillingWatch/start-production.sh
```

---

## 3. launchd Service (Auto-Start)

Create `~/Library/LaunchAgents/com.luckyai.billingwatch.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
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

Load and start:
```bash
launchctl load ~/Library/LaunchAgents/com.luckyai.billingwatch.plist
launchctl start com.luckyai.billingwatch
```

Manage:
```bash
launchctl stop com.luckyai.billingwatch   # stop
launchctl start com.luckyai.billingwatch  # start
launchctl unload ~/Library/LaunchAgents/com.luckyai.billingwatch.plist  # remove
```

---

## 4. Cloudflare Tunnel

### Install
```bash
brew install cloudflare/cloudflare/cloudflared
cloudflared tunnel login
cloudflared tunnel create billingwatch
```

### Configure `~/.cloudflared/config.yml`
```yaml
tunnel: billingwatch
credentials-file: /Users/luckyai/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: billing.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
```

### Add DNS in Cloudflare Dashboard
- Type: CNAME
- Name: `billing`
- Target: `<TUNNEL_ID>.cfargotunnel.com`
- Proxy: Enabled

### Run as a service
```bash
sudo cloudflared service install
```

Or via Launch Agent for user-space:
```bash
# Run tunnel manually to test
cloudflared tunnel run billingwatch

# Then install as service
sudo cloudflared service install
sudo launchctl start com.cloudflare.cloudflared
```

---

## 5. Stripe Webhook Configuration

1. [Stripe Dashboard → Developers → Webhooks → Add endpoint](https://dashboard.stripe.com/webhooks)
2. URL: `https://billing.yourdomain.com/webhooks/stripe`
3. Events (minimum set):
   - `charge.failed`
   - `charge.succeeded`
   - `charge.dispute.created`
   - `invoice.payment_failed`
   - `invoice.created`
   - `customer.subscription.deleted`
   - `customer.subscription.updated`
4. Copy the **Signing secret** (`whsec_…`) and store it in Keychain

---

## 6. Health Checks

```bash
# Local
curl http://localhost:8000/health
# → {"status": "ok", "service": "BillingWatch"}

# Via tunnel
curl https://billing.yourdomain.com/health
# → {"status": "ok", "service": "BillingWatch"}

# Active detectors
curl http://localhost:8000/webhooks/detectors
# → {"detectors": [...], "count": 7}

# Recent anomalies
curl http://localhost:8000/anomalies/summary
# → {"status": "ok", "alerts_total": 0, ...}
```

---

## 7. Env Variables Reference

| Variable | Source | Required | Description |
|----------|--------|----------|-------------|
| `STRIPE_SECRET_KEY` | Keychain | Yes (prod) | Live Stripe API key |
| `STRIPE_WEBHOOK_SECRET` | Keychain | Yes | Webhook signing secret |
| `APP_ENV` | Script | No | `production` or `development` |
| `LOG_LEVEL` | Script | No | `INFO` (prod), `DEBUG` (dev) |
| `PORT` | Script | No | Default `8000` |
| `ALERT_WEBHOOK_URL` | Keychain | No | Slack/Discord alert URL |
| `ALERT_EMAIL_TO` | Keychain | No | Alert recipient email |

---

## 8. Monitoring & Logs

```bash
# Live logs
tail -f /tmp/billingwatch.log

# Error logs
tail -f /tmp/billingwatch-error.log

# Process status
launchctl list | grep billingwatch
launchctl list | grep cloudflared

# Recent alerts via API
curl http://localhost:8000/anomalies/ | python3 -m json.tool
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| App won't start | `cat /tmp/billingwatch-error.log` — usually missing Keychain entry |
| Stripe 400/401 on webhooks | Wrong `STRIPE_WEBHOOK_SECRET` in Keychain |
| Tunnel not connecting | `cloudflared tunnel info billingwatch` |
| No events arriving | Check Stripe webhook delivery history in dashboard |

---

## Security Checklist

- [ ] All secrets in Keychain, not in `.env` or plaintext files
- [ ] BillingWatch binds to `127.0.0.1` (Cloudflare Tunnel is the only public path)
- [ ] LuLu firewall: cloudflared outbound allowed; BillingWatch inbound blocked publicly
- [ ] Stripe webhook signature validation active (not `STRIPE_WEBHOOK_SECRET=dev`)
- [ ] `.env` file excluded from git (check `.gitignore`)
- [ ] Log files at `/tmp/` — not persisted to cloud, not synced

---

*See also: [`deployment-guide.md`](deployment-guide.md) (detailed step-by-step) · [`production-setup.md`](production-setup.md) · [`README.md`](README.md)*
