# BillingWatch Launch Action Plan — Sunday March 8, 2026
*Written by Lucky | Updated: 4:41 PM ET — deploy path corrected (use deploy_cf.py, needs CF_ACCOUNT_ID)*

## STATUS: READY TO DEPLOY — Blocked on 3 things from Ray

Everything is built. Landing page is live locally. Deploy script is written and tested.
Show HN is Tuesday 9 AM ET. You have today + Monday to get this done.

---

## WHAT RAY NEEDS TO DO (in order, ~15 min total)

### Step 1: Create CF API Token (5 min)
1. Go to: https://dash.cloudflare.com/profile/api-tokens
2. Click "Create Token"
3. Use template: "Edit Cloudflare Pages" OR custom with:
   - Zone Resources: All zones
   - Account Resources: Your account (All accounts)
   - Permissions: Cloudflare Pages: Edit
4. Copy the token

### Step 2: Get Account ID (1 min)
1. Go to: https://dash.cloudflare.com/
2. Look at right sidebar — your Account ID is listed there
3. Copy it

### Step 3: Allow api.cloudflare.com in LuLu (2 min)
1. Open LuLu on Mac Mini
2. Add outbound rule: allow api.cloudflare.com outbound
3. This is a one-time unlock for the deploy

### Step 4: Send to Lucky
Reply with:
```
CF_API_TOKEN=your_token_here
CF_ACCOUNT_ID=your_account_id_here
LuLu: done
```

Lucky will run: 
(Pure Python — no Node.js or wrangler needed.)

> ⚠️ NOTE: Earlier task #328 said wrangler-only / no account ID needed. That was wrong.
> Node.js is NOT installed on Mac Mini. deploy_cf.py (Python) is the correct path.
> It needs BOTH CF_API_TOKEN and CF_ACCOUNT_ID. Updated Mar 8 4:41 PM ET.

---

## WHAT HAPPENS AFTER DEPLOY (Lucky handles)

1. Lucky runs: `CF_API_TOKEN=xxx CF_ACCOUNT_ID=yyy python3 ~/Projects/BillingWatch/landing/deploy_cf.py`
2. Live URL confirmed: https://billingwatch.pages.dev (or custom domain)
3. Lucky replaces `[REPLACE WITH URL]` in all 3 outreach templates
4. Tasks #315, #317, #321 become ready to execute at their scheduled times:
   - **Tuesday 9 AM** → Show HN post
   - **Wednesday 10 AM** → Indie Hackers post
   - **Thursday 10 AM** → r/SaaS post

---

## TIMELINE CHECK

| When | What | Owner |
|------|------|-------|
| Sunday (today!) | Provide CF credentials + LuLu rule | Ray |
| Sunday (today!) | Deploy landing page to CF Pages | Lucky (auto) |
| Monday | Verify live URL, test /subscribe endpoint | Lucky |
| Tuesday 9 AM | Post Show HN | Lucky |
| Wednesday 10 AM | Post Indie Hackers | Lucky |
| Thursday 10 AM | Post r/SaaS | Lucky |

---

## FILES READY TO GO
- Landing page: ~/Projects/BillingWatch/landing/index.html ✅
- Deploy script: ~/Projects/BillingWatch/landing/deploy_cf.py ✅  
- /subscribe function: ~/Projects/BillingWatch/landing/functions/subscribe.js ✅
- Show HN template: ~/Projects/BillingWatch/docs/BETA_OUTREACH.md ✅
- IH template: same file ✅
- r/SaaS template: same file ✅

---

## ONE RISK
Without KV namespace binding, beta signups go to CF Pages logs (not a database).
Optional: set up KV namespace in CF dashboard after deploy.
See DEPLOY_INSTRUCTIONS.md Step 3 for details.
