# BillingWatch Deploy — Cloudflared Setup

## Current Blocker
cloudflared is NOT installed on Mac. LuLu must allow it outbound.

## Fastest Path (3 commands, ~2 minutes)

### Step 1: Install
```bash
brew install cloudflared
```
LuLu will prompt → click **Allow** for cloudflared.

### Step 2: Quick Tunnel (instant, no auth needed)
```bash
cloudflared tunnel --url http://localhost:8080
```
This gives you a `https://xxxxx.trycloudflare.com` URL immediately.
- No Cloudflare login needed
- URL changes on restart (fine for launch day)
- Use this URL in Show HN post

### Step 3 (optional): Permanent Tunnel
For a persistent URL that survives restarts:
1. Go to https://one.dash.cloudflare.com → Networks → Tunnels → Create
2. Name it `billingwatch`
3. Copy the connector install command (includes token)
4. Run it on Mac — sets up as a service automatically
5. Configure public hostname → route to `localhost:8080`

## After Getting URL
1. Update SHOW_HN_FINAL.md — replace `[REPLACE WITH URL]`
2. Update IH_POST.md and REDDIT_SAAS_POST.md
3. Post Show HN
4. Post r/SaaS (was scheduled for today, Thu Mar 12 10AM)

## Why Not CF Pages?
We have CF API token in Keychain but Pages deploy requires `wrangler` CLI + 
the landing page has API calls to localhost. A tunnel is simpler — it exposes 
the actual running app, not a static deploy.
