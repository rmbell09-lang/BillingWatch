# BillingWatch Pre-Launch Status
*Updated: March 8, 2026 9:43 PM ET by Lucky*

## 🟢 What's READY

- Landing page: running at localhost:8080 ✅
- FastAPI backend: running at localhost:8001 (health ok) ✅  
- /subscribe endpoint: tested and working (writes to billingwatch.db) ✅
- BETA_OUTREACH.md: all 3 post templates complete ✅
- CF Pages Function (subscribe.js): written, ready to deploy ✅
- deploy_cf.py: script ready (needs CF_API_TOKEN + CF_ACCOUNT_ID) ✅
- wrangler deploy script: ready as alternative ✅
- OG image: og-image.png present ✅
- Git history: 14 commits ✅

## 🔴 BLOCKED — Needs Ray

### 1. Cloudflare Deploy (Task #328) — HIGHEST PRIORITY
**Required before anything goes live:**
- [ ] CF_API_TOKEN: dash.cloudflare.com → My Profile → API Tokens → Create Token (Pages:Edit + Account:Read)
- [ ] CF_ACCOUNT_ID: visible on right sidebar of dash.cloudflare.com
- [ ] LuLu rule: allow api.cloudflare.com outbound on Mac Mini
- [ ] (Optional but recommended) Create KV namespace billingwatch_signups in CF Dashboard → bind to Pages project

Once Ray provides these, Lucky runs:

Or with wrangler: 

### 2. Stripe Keys (Task #340) — After launch
- [ ] 
- [ ] 
- [ ] 

### 3. GitHub Repo — Before HN post
- Beta users will ask for source code
- GitHub CLI not installed, no remote configured
- Options: install gh CLI + push, or Ray creates repo manually and provides SSH remote URL

## 📅 Post Schedule

| Platform | Task # | Time | Template |
|----------|--------|------|----------|
| Hacker News | #315 | Tuesday Mar 10 @ 9:00 AM ET | Ready in BETA_OUTREACH.md |
| Indie Hackers | #317 | Wednesday Mar 11 @ 10:00 AM ET | Ready in BETA_OUTREACH.md |
| r/SaaS | #321 | Thursday Mar 12 @ 10:00 AM ET | Ready in BETA_OUTREACH.md |

## ⚠️ Critical Path

CF credentials → deploy → live URL → update BETA_OUTREACH.md → post Show HN (Tuesday 9AM)

Time remaining until HN post: ~35 hours. CF credentials needed ASAP.
