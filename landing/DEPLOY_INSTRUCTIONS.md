# BillingWatch Landing Page — Deploy Instructions

## ⚠️ BLOCKED — Ray's Action Items (Show HN is TUESDAY 9 AM ET)

To unblock the CF deploy, Ray must provide:
1. **CF_API_TOKEN** — [dash.cloudflare.com](https://dash.cloudflare.com) → My Profile → API Tokens → Create Token → select "Edit Cloudflare Pages" template
2. **CF_ACCOUNT_ID** — visible on the right sidebar of [dash.cloudflare.com](https://dash.cloudflare.com) main page
3. **LuLu rule** — allow `api.cloudflare.com` outbound from Mac Mini

Once provided, Lucky runs (no Ray involvement needed):
```bash
CF_API_TOKEN=xxx CF_ACCOUNT_ID=yyy python3 ~/Projects/BillingWatch/landing/deploy_cf.py
```

---

## Current Status (verified Mar 8, 2026 8:15 PM ET)
- ✅ Landing page built and running locally at http://127.0.0.1:8080 (launchd auto-start)
- ✅ FastAPI backend running at http://127.0.0.1:8001 (`{"status":"ok","service":"BillingWatch"}`)
- ✅ /subscribe CF Pages Function created (landing/functions/subscribe.js)
- ✅ serve-landing.py handles /subscribe locally with SQLite storage
- ✅ deploy_cf.py ready (Python, no external deps)
- ❌ Wrangler CLI: NOT installed (Node.js not on Mac Mini — ignore Option 0 in old docs)
- ⏳ Cloudflare Pages deploy: blocked on CF credentials + LuLu rule

---

## Option 1: Cloudflare Pages — RECOMMENDED (use deploy_cf.py)

### Step 1: Get CF credentials (Ray provides these)
```
CF_API_TOKEN=your_token_here      # dash.cloudflare.com → My Profile → API Tokens
CF_ACCOUNT_ID=your_account_id    # Right sidebar on dash.cloudflare.com main page
```

### Step 2: Deploy (Lucky runs this once LuLu allows api.cloudflare.com outbound)
```bash
CF_API_TOKEN=your_token_here CF_ACCOUNT_ID=your_account_id python3 ~/Projects/BillingWatch/landing/deploy_cf.py
```

### Step 3: (Optional) Set up KV for signup storage
1. CF Dashboard → Workers & Pages → KV → Create namespace
2. Name it: `billingwatch_signups`
3. CF Dashboard → Pages → billingwatch → Settings → Functions → KV namespace bindings
4. Add binding: Variable name = `SIGNUPS`, KV namespace = `billingwatch_signups`

Without KV binding: signups logged to CF Pages logs (visible in dashboard).
With KV binding: signups stored persistently.

### Step 4: Test live /subscribe endpoint
```bash
curl -X POST https://billingwatch.pages.dev/subscribe \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com","name":"Test User"}'
# Expected: {"ok":true,"message":"You're on the list!..."}
```

---

## Option 2: Surge.sh (Static Only — no /subscribe backend)
**Only use if CF credentials can't be obtained before Show HN.**
```bash
# Requires LuLu allow surge.sh outbound + Node.js install or npx available
npx surge ~/Projects/BillingWatch/landing billingwatch.surge.sh
```
⚠️ /subscribe won't work on Surge (no serverless functions). Signups would be lost.

---

## Option 3: Local Access Only (already running)
Landing page: http://127.0.0.1:8080
Subscribe test:
```bash
curl -X POST http://127.0.0.1:8080/subscribe \
  -H 'Content-Type: application/json' \
  -d '{"email":"ray@test.com","name":"Ray"}'
```

---

## Note on Wrangler
~~Option 0: Wrangler CLI (RECOMMENDED — Already Installed!)~~
**REMOVED** — Wrangler and Node.js are NOT installed on Mac Mini (confirmed Mar 8, 2026).
deploy_cf.py (Python, no deps) is the correct deploy path.
