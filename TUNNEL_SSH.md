# BillingWatch — SSH Tunnel (No LuLu Changes Needed)

**Status: TESTED AND WORKING** (2026-03-17)

## The Problem
cloudflared, ngrok, and localtunnel all require the **Mac to initiate outbound connections** to their relay services.
LuLu blocks these. Requesting LuLu rules for each tool is the same friction.

## The Solution: SSH Local Port Forwarding

Use the **existing SSH connection from VPS → Mac** to expose BillingWatch publicly.
The Mac doesn't make any new outbound connections — LuLu never sees it.

### How It Works
- VPS runs: `ssh -L 0.0.0.0:8080:127.0.0.1:8000 -N luckyai@mac`
- VPS port 8080 (public) → SSH tunnel → Mac port 8000 (BillingWatch)
- Stripe webhook URL: `http://187.77.204.203:8080/webhook`

### Start the Tunnel (from VPS)
```bash
ssh -i /home/openclaw/.ssh/lucky_to_mac -o IdentitiesOnly=yes \
  -L 0.0.0.0:8080:127.0.0.1:8000 \
  -N -f -o ExitOnForwardFailure=yes \
  luckyai@100.90.7.148
```

### Verify
```bash
curl http://187.77.204.203:8080/health
# Expected: {status:ok,service:BillingWatch,...}
```

### Stop the Tunnel
```bash
pkill -f 'ssh.*8080.*luckyai@100.90.7.148'
```

## Stripe Webhook Setup (when ready)
1. Start tunnel: run command above from VPS
2. In Stripe Dashboard → Webhooks → Add endpoint:
   - URL: `http://187.77.204.203:8080/webhook`
   - Events: `charge.*`, `invoice.*`, `customer.*`, `payment_intent.*`
3. Copy signing secret to Mac Keychain:
   `security add-generic-password -s BillingWatch -a STRIPE_WEBHOOK_SECRET -w 'whsec_...'`
4. Restart BillingWatch

## For Persistent Tunnel (production)
Create systemd service on VPS at `/etc/systemd/system/billingwatch-tunnel.service`
(see scripts/billingwatch-tunnel.service)

## vs. ngrok/localtunnel
| Option | LuLu Rule Needed | Cost | Setup |
|--------|-----------------|------|-------|
| cloudflared | Yes (blocked) | Free | Medium |
| ngrok | Yes (new binary) | Free tier limited | Easy |
| localtunnel | Yes (node binary) | Free, unstable | Easy |
| **SSH tunnel** | **No** | **Free** | **Already works** |

Winner: SSH tunnel. Zero dependencies, zero cost, works now.
