# BillingWatch — Production Launch Checklist
*Last updated: March 6, 2026*
*Lucky has completed all scripting. Ray completes the 5 manual steps below.*

---

## Status
- [x] start-production.sh — written + chmod +x
- [x] launchd plist — written to ~/Library/LaunchAgents/com.luckyai.billingwatch.plist
- [x] cloudflared config template — written to ~/.cloudflared/config.yml
- [x] Beta invite drafts — ~/Projects/BillingWatch/docs/beta-invites-draft.md
- [ ] cloudflared binary — needs install (see Step 1)
- [ ] Stripe live keys — needs Keychain entry (see Step 2)
- [ ] Cloudflare tunnel — needs Ray login (see Step 3)
- [ ] BillingWatch started — needs launchctl load (see Step 4)
- [ ] Beta invites sent — drafts ready (see Step 5)

---

## STEP 1 — Install cloudflared (2 min)
Download the binary manually (no Homebrew needed):

1. Go to: https://github.com/cloudflare/cloudflared/releases/latest
2. Download: cloudflared-darwin-arm64.tgz
3. Extract and install:
   tar -xzf cloudflared-darwin-arm64.tgz
   sudo mv cloudflared /usr/local/bin/
   cloudflared --version

---

## STEP 2 — Add Stripe live keys to Keychain (1 min)
Get your live keys from https://dashboard.stripe.com/apikeys

security add-generic-password -s BillingWatch -a STRIPE_SECRET_KEY -w sk_live_YOUR_KEY_HERE
security add-generic-password -s BillingWatch -a STRIPE_WEBHOOK_SECRET -w whsec_PLACEHOLDER_UNTIL_STEP_3

Verify they're there:
security find-generic-password -s BillingWatch -a STRIPE_SECRET_KEY -w

---

## STEP 3 — Create Cloudflare Tunnel (5 min)
Requires a Cloudflare account. Free tier works.

cloudflared tunnel login
cloudflared tunnel create billingwatch
# Note the TUNNEL_ID from the output

# Edit ~/.cloudflared/config.yml — replace:
# - REPLACE_WITH_TUNNEL_ID with actual tunnel ID
# - REPLACE_WITH_YOUR_DOMAIN.com with your domain (e.g. billing.yourdomain.com)

# In Cloudflare Dashboard: DNS > Add CNAME record
# Name: billing (or whatever subdomain)
# Target: TUNNEL_ID.cfargotunnel.com
# Proxy: enabled

cloudflared tunnel run billingwatch  # test it, then Ctrl+C

# Install as service (auto-starts on boot):
sudo cloudflared service install
sudo launchctl start com.cloudflare.cloudflared

---

## STEP 4 — Add Stripe webhook endpoint (2 min)
With tunnel running, go to:
https://dashboard.stripe.com/webhooks > Add endpoint

URL: https://YOUR_DOMAIN/webhooks/stripe

Events to enable:
- charge.failed
- charge.succeeded
- charge.dispute.created
- invoice.payment_failed
- invoice.created
- customer.subscription.deleted
- customer.subscription.updated

Copy the Signing Secret (whsec_...) and update Keychain:
security delete-generic-password -s BillingWatch -a STRIPE_WEBHOOK_SECRET
security add-generic-password -s BillingWatch -a STRIPE_WEBHOOK_SECRET -w whsec_YOUR_REAL_SECRET

---

## STEP 5 — Start BillingWatch (30 sec)
launchctl load ~/Library/LaunchAgents/com.luckyai.billingwatch.plist
launchctl start com.luckyai.billingwatch

# Verify it's running:
curl http://localhost:8000/health
# Expected: {status: ok, service: BillingWatch}

tail -f /tmp/billingwatch.log

---

## STEP 6 — Send Beta Invites (10 min)
Open: ~/Projects/BillingWatch/docs/beta-invites-draft.md
Three drafts ready. Send in this order:
1. Comment in self-hosted billing thread (r/SaaS)
2. DM @filippanoski on Indie Hackers
3. DM 2-3 commenters from GetRackz thread

---

## DONE CRITERIA
- curl https://YOUR_DOMAIN/health returns OK
- Stripe webhook dashboard shows endpoint active
- 3 beta invites sent
