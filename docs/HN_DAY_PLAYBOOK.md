# BillingWatch — HN Launch Day Playbook
*Written by Lucky — March 10, 2026*
*For Ray — everything you need to go from 0 to live in 10 minutes*

---

## ⏰ TIMELINE

| Time | Action |
|------|--------|
| 8:45 AM | Wake up, coffee, read this doc |
| 8:50 AM | LuLu allowlist + cloudflared |
| 8:55 AM | Get live URL, test form, update SHOW_HN_FINAL.md |
| 9:00 AM | Submit to HN + post first comment |
| 9:01–11:00 AM | Monitor + reply every 30 min |
| 11:00 AM–5 PM | Check hourly, send outreach DMs to warm leads |
| Evening | Count signups, log results in LAUNCH_RESULTS.md |

---

## STEP 1: DEPLOY (8:50 AM, ~5 min)

### Option A — Cloudflare Tunnel (Fastest)

```bash
# 1. In LuLu: allow cloudflared binary (one-time rule)
#    It will try to connect to *.argotunnel.com and *.cloudflare.com

# 2. Run the server first (in a new terminal):
cd ~/Projects/BillingWatch
python3 billingwatch.py

# 3. In another terminal, start the tunnel:
cloudflared tunnel --url http://localhost:8080

# 4. Cloudflare prints: "https://abc123.trycloudflare.com"
# That's your live URL. Copy it.
```

### Option B — If cloudflared fails
Use Formspree (2 min):
1. Go to https://formspree.io → create free form
2. Get your form endpoint: `https://formspree.io/f/XXXXXX`
3. Edit `docs/landing.html` — replace form action with Formspree URL
4. Open `landing.html` directly in browser — that's your demo URL (no server needed)

---

## STEP 2: UPDATE POST (8:55 AM, ~2 min)

```bash
# Replace [LIVE_URL] in the HN post:
LIVE_URL="https://YOUR-ACTUAL-URL-HERE.trycloudflare.com"
sed -i "s|\[LIVE_URL\]|$LIVE_URL|g" ~/Projects/BillingWatch/docs/SHOW_HN_FINAL.md

# Verify:
grep "trycloudflare" ~/Projects/BillingWatch/docs/SHOW_HN_FINAL.md | head -3
```

Then test the form:
1. Open `$LIVE_URL` in browser
2. Submit a test email (use your own)
3. Confirm: `sqlite3 ~/Projects/BillingWatch/billingwatch.db "SELECT * FROM beta_signups;"`

---

## STEP 3: SUBMIT TO HN (9:00 AM)

**URL:** https://news.ycombinator.com/submit

**Title** (copy exactly):
```
Show HN: BillingWatch – self-hosted Stripe anomaly detector (webhook lag, silent lapses, card testing)
```

**URL field:** Your live URL (no `?ref=hn` needed — HN strips query params anyway)

**Immediately after posting:**
1. Click your submission link
2. Copy the FIRST COMMENT from `docs/SHOW_HN_FINAL.md`
3. Paste into the comment box → Submit
4. Bookmark the HN thread URL

---

## STEP 4: OUTREACH (9:01 AM onward)

Send DMs to all 10 targets AFTER HN is live (links won't 404 now).

**Priority order:**
1. @swizec (Twitter) — warmest, has talked about Stripe issues publicly
2. @marc_louvion (IH) — high output, multiple Stripe products
3. @dannypostmaa (Twitter) — Headliner founder, serious Stripe user
4. @csallen (IH) — Baremetrics territory, knows billing pain
5. @levelsio (Twitter) — multiple products, notoriously manual about ops

Templates in:
- `docs/COLD_OUTREACH_DMS.md` (5 DMs)
- `docs/OUTREACH_TARGETS.md` (5 more DMs)

Replace `[LIVE_URL]` with your actual URL before sending.

---

## STEP 5: MONITOR & REPLY (9:00 AM–11:00 AM)

**Every 30 min:**
1. Check HN thread for new comments
2. Reply to EVERYTHING — even "this is interesting" gets a reply
3. Upvote good questions (they bubble up)

**Reply strategy:**
- Technical questions → go deep, show you know the code
- "Why not just use X?" → acknowledge, explain the self-hosted tradeoff
- "What's the price?" → "Beta is free. Paid tiers coming based on feedback from this thread."
- "Is this just a webhook logger?" → No — explain the detection logic (7 detectors, pattern matching, not just logging)
- Skeptics → Don't be defensive. "Fair point — here's the specific edge case it caught for me."

**Check signups:**
```bash
sqlite3 ~/Projects/BillingWatch/billingwatch.db "SELECT COUNT(*), MAX(created_at) FROM beta_signups;"
```

---

## STEP 6: SECONDARY CHANNELS (Wednesday + Thursday)

If HN gets traction (>5 points, any comments):
- **Wednesday 10 AM:** Post to Indie Hackers (template in `docs/BETA_OUTREACH.md`)
- **Thursday 10 AM:** Post to r/SaaS (template in `docs/BETA_OUTREACH.md`)
- **Whenever:** Reply to anyone who DMed, send onboarding email (in `docs/ONBOARDING_EMAILS.md`)

---

## STEP 7: END OF DAY — LOG RESULTS

Fill in `docs/LAUNCH_RESULTS.md`:
```
HN Points: [X]
HN Comments: [X]
Beta Signups: [X] (sqlite3 billingwatch.db "SELECT COUNT(*) FROM beta_signups;")
Outreach Responses: [X]
Notable Comments/Feedback: [copy paste key ones]
Live URL: [what you used]
```

---

## IF NOTHING HAPPENS

That's normal. HN is random. Next steps:
1. **Wait 48h** — sometimes posts get traction late
2. **Post to IH Wednesday anyway** — different audience
3. **DM your 10 targets regardless** — don't wait for HN momentum
4. **Ask on IH:** "Show HN flopped — what would make you install a self-hosted Stripe monitor?"
5. **Ship one improvement based on today's feedback** — then repost in 2 weeks

The product works. The first launch rarely converts. Keep shipping.

---

## QUICK REFERENCE — Key Files

| File | Contents |
|------|----------|
| `docs/SHOW_HN_FINAL.md` | HN post + first comment (copy-paste ready) |
| `docs/COLD_OUTREACH_DMS.md` | 5 personalized DMs |
| `docs/OUTREACH_TARGETS.md` | 5 more DMs (Twitter/IH founders) |
| `docs/ONBOARDING_EMAILS.md` | 3-email sequence for new beta signups |
| `docs/API_DOCS.md` | API reference (for technical HN audience) |
| `LULU_SETUP.md` | LuLu + cloudflared setup steps |
| `docs/LAUNCH_RESULTS.md` | Fill this in tonight |

---

*Lucky — built at 2:41 AM so you don't have to think at 8:50 AM. Go get some sleep.*
