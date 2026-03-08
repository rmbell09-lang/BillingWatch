# BillingWatch Landing Page — Deploy Instructions

## Current Status
- ✅ Landing page built
- ✅ Running locally at: http://127.0.0.1:8080 (auto-starts via launchd)
- ✅ Committed to git (branch: master)
- ✅ /subscribe CF Pages Function created (landing/functions/subscribe.js)
- ✅ serve-landing.py handles /subscribe locally with SQLite storage
- ⏳ Cloudflare Pages deploy: blocked on CF credentials + LuLu rule

## What Ray Needs to Provide
1. CF_API_TOKEN — dash.cloudflare.com → My Profile → API Tokens → Create Token (Pages:Edit)
2. CF_ACCOUNT_ID — dash.cloudflare.com → right sidebar on main page
3. LuLu rule: allow cloudflare.com outbound from Mac Mini
4. (Optional) Create KV namespace in CF Dashboard for storing signups

## Option 0: Wrangler CLI (RECOMMENDED — Already Installed!)
wrangler is at /usr/local/bin/wrangler. This is the simplest path.

### What Ray provides
- CLOUDFLARE_API_TOKEN (Pages:Edit permission)
- LuLu rule: allow cloudflare.com outbound

### What Lucky runs (once allowed)
```bash
CLOUDFLARE_API_TOKEN=your_token bash ~/Projects/BillingWatch/landing/deploy_wrangler.sh
```

Done. Takes ~10 seconds. No ACCOUNT_ID needed for wrangler.

---

## Option 1: Cloudflare Pages (Recommended)

### Step 1: Get CF credentials (Ray provides these)
```
CF_API_TOKEN=your_token_here
CF_ACCOUNT_ID=your_account_id_here
```

### Step 2: Deploy (Lucky runs this once LuLu is allowed)
```bash
export CF_API_TOKEN=your_token_here
export CF_ACCOUNT_ID=your_account_id_here
python3 ~/Projects/BillingWatch/landing/deploy_cf.py
```

### Step 3: Set up KV for signup storage (optional but recommended)
1. CF Dashboard → Workers & Pages → KV → Create namespace
2. Name it: billingwatch_signups
3. CF Dashboard → Pages → billingwatch → Settings → Functions → KV namespace bindings
4. Add binding: Variable name = SIGNUPS, KV namespace = billingwatch_signups
5. Redeploy (or trigger from deploy_cf.py)

Without KV binding: signups are logged to CF Pages logs (visible in dashboard).
With KV binding: signups stored persistently, no external service needed.

### Step 4: Test the /subscribe endpoint
```bash
curl -X POST https://billingwatch.pages.dev/subscribe \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com","name":"Test User"}'
# Expected: {"ok":true,"message":"You're on the list!..."}
```

## Option 2: Surge.sh (Fast Alternative — needs LuLu allow surge.sh)
```bash
export PATH=/opt/homebrew/bin:~/.npm-global/bin:$PATH
npx surge ~/Projects/BillingWatch/landing billingwatch.surge.sh
# Note: /subscribe won't work on Surge (no serverless functions)
```

## Option 3: Local Access Only
Landing page already running at http://127.0.0.1:8080
serve-landing.py now handles POST /subscribe with SQLite storage.

## Local Testing
```bash
# Restart the local server to pick up serve-landing.py changes
pkill -f serve-landing.py
python3 ~/Projects/BillingWatch/serve-landing.py &
# Test signup
curl -X POST http://127.0.0.1:8080/subscribe \
  -H 'Content-Type: application/json' \
  -d '{"email":"ray@test.com","name":"Ray"}'
```
