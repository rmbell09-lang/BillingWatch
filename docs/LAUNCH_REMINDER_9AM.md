# 🚀 BillingWatch — 9AM Launch Reminder
*Prepared by Lucky at 3AM so you don't have to think at 8:50AM*

---

## START HERE at 8:50 AM

### Step 1 — Allow cloudflared in LuLu (2 min)
Open LuLu → allow `cloudflared` binary → it connects to `*.argotunnel.com` and `*.cloudflare.com`

### Step 2 — Start BillingWatch server (Terminal 1)
```bash
cd ~/Projects/BillingWatch
python3 billingwatch.py
```
Leave this running.

### Step 3 — Start Cloudflare tunnel (Terminal 2)
```bash
cloudflared tunnel --url http://localhost:8080
```
Cloudflare prints a URL like: `https://abc123.trycloudflare.com`
**Copy that URL.**

### Step 4 — Update the HN post with your live URL (30 seconds)
```bash
LIVE_URL="https://PASTE-YOUR-URL-HERE.trycloudflare.com"
sed -i "s|\[LIVE_URL\]|$LIVE_URL|g" ~/Projects/BillingWatch/docs/SHOW_HN_FINAL.md
```

### Step 5 — Test the form (1 min)
1. Open `$LIVE_URL` in browser — landing page should load
2. Submit a test email
3. Confirm: `sqlite3 ~/Projects/BillingWatch/billingwatch.db "SELECT * FROM beta_signups;"`

### Step 6 — Post to HN at exactly 9:00 AM
URL: https://news.ycombinator.com/submit

**Title (copy exactly):**
```
Show HN: BillingWatch – self-hosted Stripe anomaly detector (webhook lag, silent lapses, card testing)
```
**URL field:** your `trycloudflare.com` URL

**Immediately after submitting — post the first comment** (copy from `docs/SHOW_HN_FINAL.md`)

---

## IF CLOUDFLARED FAILS — Formspree Fallback (3 min)
1. Go to https://formspree.io → create free form → copy endpoint: `https://formspree.io/f/XXXXXX`
2. Edit `docs/landing.html` — replace the form `action` with your Formspree URL
3. Open `landing.html` directly in browser — use that as your demo URL (no server needed)
4. Submit to HN with that URL

---

## After Posting (9:00 AM–11:00 AM)
- Check HN comments every 30 min
- Reply to everything in the first 2 hours (HN rewards speed)
- DM the 10 targets from `docs/OUTREACH_TARGETS.md` + `docs/COLD_OUTREACH_DMS.md`
- Evening: update `docs/LAUNCH_RESULTS.md` with points / signups / responses

---

## Key Files
| What | Where |
|------|-------|
| HN post copy | `~/Projects/BillingWatch/docs/SHOW_HN_FINAL.md` |
| First comment | Same file (scroll down) |
| Cold DMs (5) | `~/Projects/BillingWatch/docs/COLD_OUTREACH_DMS.md` |
| More DMs (5) | `~/Projects/BillingWatch/docs/OUTREACH_TARGETS.md` |
| Log results | `~/Projects/BillingWatch/docs/LAUNCH_RESULTS.md` |
| Full playbook | `~/Projects/BillingWatch/docs/HN_DAY_PLAYBOOK.md` |

---

## 🔔 Gumroad Session Also Needs Fixing
The Gumroad session expired at 3AM. TradeSight listing is ready to publish — just needs re-auth.
Open https://gumroad.com in Chrome and log in to refresh the session.
