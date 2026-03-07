# BillingWatch — Production Setup Guide

## Overview

This guide covers switching BillingWatch from test/dev mode to production with live Stripe keys,
Keychain-secured secrets, and a production-ready environment configuration.

---

## Step 1: Get Your Stripe Live Keys

1. Log into the [Stripe Dashboard](https://dashboard.stripe.com)
2. Toggle "Test mode" OFF (top-right switch)
3. Go to **Developers → API keys**
4. Copy your **Secret key** ()
5. Go to **Developers → Webhooks**
6. Add a new endpoint (your public URL, e.g. )
7. Select events to listen for: , , 
8. Copy the **Signing secret** ()

---

## Step 2: Store Keys in macOS Keychain (NOT in .env files)

Never put live Stripe keys in  files. Use macOS Keychain:



To verify they were stored:


---

## Step 3: Create a Keychain-backed Config Module

Add  to BillingWatch:



---

## Step 4: Create Production .env (non-sensitive values only)

Copy  to  and fill in only non-secret values:



Start app with:


---

## Step 5: Expose Webhook Endpoint

BillingWatch needs a public URL for Stripe to send webhook events.

**Option A — Cloudflare Tunnel (recommended for Mac Mini):**


**Option B — VPS reverse proxy:**
- Set up nginx on VPS to proxy  to Mac Mini via NordVPN mesh
- Use your own domain with SSL

---

## Step 6: Verify Production Readiness

Run through this checklist before going live:



**Expected clean output:**
-  returns 200 with 
-  returns all 7 detectors
- Stripe test webhook is received and validated (not rejected)
- No  or  logs on startup

---

## Step 7: .gitignore Verification

Ensure these are in  (never commit secrets):


---

## Webhook Secret Rotation

When rotating the Stripe webhook secret:


---

## Summary

| Secret | Storage | Never in |
|--------|---------|----------|
|  (Stripe secret key) | macOS Keychain | .env files, code, git |
|  (webhook signing secret) | macOS Keychain | .env files, code, git |
| DB password | macOS Keychain | .env files, code, git |
| SMTP password | macOS Keychain | .env files, code, git |
| App config (URLs, email addresses) | .env.production | Not sensitive, OK |

**Rule:** If a value can rotate or be revoked, it goes in Keychain. If it's just configuration, it can go in .env.production.


---

## Step 8: Configure Email Alerting (SMTP)

BillingWatch sends email alerts via SMTP when anomaly detectors fire. The implementation
is in `src/alerting/email.py` and is automatically used by `AlertDispatcher`.

### Required Environment Variables

Add these to `.env.production` (non-sensitive) and Keychain (sensitive):

**In `.env.production` (safe to commit):**
```
ALERT_EMAIL_FROM=alerts@yourdomain.com
ALERT_EMAIL_TO=you@yourdomain.com
SMTP_HOST=smtp.yourdomain.com
SMTP_PORT=587
SMTP_USER=alerts@yourdomain.com
SMTP_USE_TLS=true
```

**In macOS Keychain (never in .env):**
```bash
security add-generic-password -a billingwatch -s SMTP_PASS -w "your-smtp-password"
```

Load it at startup via `src/keychain.py` (same pattern as Stripe keys).

### Common SMTP Providers

| Provider  | SMTP Host             | Port | Notes                        |
|-----------|-----------------------|------|------------------------------|
| Gmail     | smtp.gmail.com        | 587  | Needs App Password (2FA req) |
| Mailgun   | smtp.mailgun.org      | 587  | Free tier: 100/day           |
| Postmark  | smtp.postmarkapp.com  | 587  | Best deliverability          |
| AWS SES   | email-smtp.us-east-1.amazonaws.com | 587 | Cheapest at scale |

**Recommended:** Postmark or Mailgun for reliable transactional delivery.

### Alert Email Format

Subject line: `[BillingWatch] CRITICAL: Duplicate charge detected`

Emails are sent as HTML with plain-text fallback. Each alert includes:
- Severity badge (CRITICAL / HIGH / MEDIUM / LOW)
- Detector name and timestamp
- Alert title and full message
- Metadata table (customer ID, amount, event count, etc.)

### Test Your Email Config

```bash
source .venv/bin/activate
python3 - <<EOF
from src.alerting.email import EmailAlerter
from src.detectors.base import Alert

alerter = EmailAlerter()
print("Configured:", alerter.is_configured)
print("From:", alerter.from_addr)
print("To:", alerter.to_addrs)

# Send a test alert
from datetime import datetime
test = Alert(
    detector="test",
    severity="high",
    title="Test Alert — SMTP Verification",
    message="This is a test alert to verify email delivery is working.",
    metadata={"test": "true", "source": "manual verification"},
    triggered_at=datetime.utcnow()
)
result = alerter.send(test)
print("Sent:", result)
EOF
```

Expected output: `Sent: True` and an email in your inbox within 30 seconds.

### Graceful Degradation

If SMTP is not configured, BillingWatch logs a warning and continues — alerts still
fire via webhook if configured. No crash. `EmailAlerter.is_configured` returns False
and `send()` returns False without raising.
