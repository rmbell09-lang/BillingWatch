# BillingWatch Landing Page — Deploy Instructions

## Current Status
- ✅ Landing page built: 
- ✅ Running locally at: http://127.0.0.1:8080 (auto-starts via launchd)
- ✅ Committed to git (branch: master)
- ⏳ Cloudflare Pages deploy: blocked on CF credentials

## Option 1: Cloudflare Pages (Recommended)

### Step 1: Get your CF credentials
1. Log into https://dash.cloudflare.com
2. Go to My Profile → API Tokens → Create Token
3. Use template: "Edit Cloudflare Workers" or create custom with Pages:Edit permission
4. Also get your Account ID from the main dashboard right sidebar

### Step 2: Deploy
```bash
export CF_API_TOKEN=your_token_here
export CF_ACCOUNT_ID=your_account_id_here
python3 ~/Projects/BillingWatch/landing/deploy_cf.py
```

### Step 3: Update Formspree endpoint
1. Create a free form at https://formspree.io
2. Get your form ID (looks like: xyzabcde)
3. Run: sed -i '' 's/REPLACE_ME/your_form_id/' ~/Projects/BillingWatch/landing/index.html
4. Redeploy

## Option 2: Surge.sh (Fast Alternative)
```bash
export PATH=/opt/homebrew/bin:~/.npm-global/bin:$PATH
npx surge ~/Projects/BillingWatch/landing billingwatch.surge.sh
# Follow email/password prompts
```

## Option 3: Local Access Only
Landing page already running at http://127.0.0.1:8080 — no action needed.

## Formspree Setup (Beta Signup Form)
1. Go to https://formspree.io/register (free)
2. Create new form → name it "BillingWatch Beta Signup"
3. Copy the form ID from the endpoint URL
4. Update index.html: replace REPLACE_ME with your form ID
5. Redeploy
