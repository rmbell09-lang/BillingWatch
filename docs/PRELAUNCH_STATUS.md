# BillingWatch Pre-Launch Status Brief
**Generated: Sunday March 8, 2026 — 8:20 PM ET**
**Show HN: TUESDAY March 10, 2026 — 9:00 AM ET (T-37 hours)**

---

## ✅ What's Ready (No Action Needed)

| Item | Status | Details |
|------|--------|---------|
| FastAPI backend | ✅ LIVE | Port 8001, `{"status":"ok"}` confirmed |
| Landing page | ✅ LIVE | Port 8080, launchd auto-start, 846-line HTML |
| CF Pages Function | ✅ READY | `landing/functions/subscribe.js` handles POST /subscribe |
| Temp tunnel | ✅ LIVE | `https://neck-dna-fotos-specialties.trycloudflare.com` |
| SEO / OG tags | ✅ DONE | og:title, og:description, og:image, Twitter card, canonical URL |
| All 7 detectors | ✅ DONE | Wired to EventStore, integration tests pass |
| Outreach templates | ✅ READY | `docs/BETA_OUTREACH.md` — HN, IH, Reddit, email |
| Deploy script | ✅ READY | `landing/deploy_cf.py` (Python, no deps) |

---

## ❌ Ray's Action Items (TONIGHT or MONDAY MORNING)

### 1. Get CF API Token (5 min)
1. Go to: https://dash.cloudflare.com → My Profile → API Tokens
2. Click **Create Token**
3. Select template: **"Edit Cloudflare Pages"**
4. Click Continue to Summary → Create Token
5. Copy the token and send to Lucky

### 2. Get CF Account ID (1 min)
1. Go to: https://dash.cloudflare.com (main page)
2. Look at the **right sidebar** — Account ID is listed there
3. Copy and send to Lucky

### 3. LuLu Rule (2 min)
When Lucky runs deploy_cf.py, it calls `api.cloudflare.com`
1. Open LuLu
2. Add rule: Allow `api.cloudflare.com` outbound from Mac Mini
3. (Or temporarily allow and re-block after deploy)

### 4. (Optional but recommended) Stripe Keys to Keychain
Task #340 — needed for production webhook handling
```bash
security add-generic-password -s BillingWatch -a STRIPE_SECRET_KEY -w sk_live_xxx
security add-generic-password -s BillingWatch -a STRIPE_WEBHOOK_SECRET -w whsec_xxx
```

---

## 🚀 What Lucky Does Automatically (Once Unblocked)

Once Ray provides CF_API_TOKEN + CF_ACCOUNT_ID + LuLu rule:

```bash
CF_API_TOKEN=xxx CF_ACCOUNT_ID=yyy python3 ~/Projects/BillingWatch/landing/deploy_cf.py
```

Lucky will:
1. Deploy landing page to Cloudflare Pages
2. Test the live `/subscribe` endpoint
3. Update all `[REPLACE WITH URL]` placeholders in `docs/BETA_OUTREACH.md` with the live URL
4. Update outreach templates with `?ref=hn`, `?ref=ih`, `?ref=reddit` tracking params
5. Post Show HN at 9:00 AM Tuesday (Task #315)
6. Mark CF deploy task done in Mission Control

---

## 📋 Launch Timeline

| Date | Task | Owner | Status |
|------|------|-------|--------|
| Sun Mar 8 (tonight) | Provide CF credentials | **RAY** | ⏳ WAITING |
| Sun Mar 8 (tonight) | CF Pages deploy | Lucky | Blocked until above |
| Tue Mar 10 9 AM ET | Post Show HN | Lucky | Scheduled |
| Wed Mar 11 10 AM ET | Post Indie Hackers | Lucky | Scheduled |
| Thu Mar 12 10 AM ET | Post r/SaaS Reddit | Lucky | Scheduled |

---

## Current Temp Tunnel
URL: `https://neck-dna-fotos-specialties.trycloudflare.com`
- ✅ LIVE as of 8:15 PM ET
- This URL is temporary and won't survive Mac reboots
- CF Pages gives permanent URL (billingwatch.pages.dev or custom domain)

---

## Risk if CF Deploy Doesn't Happen
- Show HN must link to a real URL — temp tunnel is unreliable (dies on reboot)
- If temp tunnel dies before Tuesday: Show HN post would link to dead URL
- **Time-to-fix if Ray sends credentials now:** ~15 minutes
