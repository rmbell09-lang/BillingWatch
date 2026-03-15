# BillingWatch — Show HN Final Post
*Ready to post at 9:00 AM ET Tuesday March 10, 2026*

---

## ⚠️ BEFORE POSTING — Ray's Checklist

1. **Get the live URL** (pick one):
   - **Option A (fastest, no CF creds needed):** Run `cloudflared tunnel --url http://localhost:8080` — LuLu must allow cloudflared first (see `LULU_SETUP.md`). Cloudflare prints a temp URL like `https://abc123.trycloudflare.com`. Use that.
   - **Option B (persistent):** Deploy with `CF_API_TOKEN` + `CF_ACCOUNT_ID` per `LULU_SETUP.md`.

2. **Replace `[LIVE_URL]`** below with your actual URL + `?ref=hn`

3. **Test the form** — go to the URL, submit a test email, confirm it writes to `billingwatch.db`

4. **Post to HN:** https://news.ycombinator.com/submit

---

## HN Submission Title

```
Show HN: BillingWatch – self-hosted Stripe anomaly detector (webhook lag, silent lapses, card testing)
```

## HN Submission URL

```
[LIVE_URL]?ref=hn
```

---

## First Comment (post immediately after submission)

```
Hey HN,

I built BillingWatch after getting hit by a silent subscription lapse that cost me ~$800 before I noticed. Stripe's dashboard doesn't alert you when payment retries exhaust silently.

BillingWatch runs 7 real-time detectors against your Stripe webhook stream:
- Charge failure rate spikes (configurable threshold)
- Silent subscription lapses (payment failed → subscriber still active)
- Webhook delivery lag (webhooks arriving late = events you're missing)
- Duplicate charge detection
- Revenue drop detection (7-day rolling average, 15% drop threshold)
- Fraud spike detection
- Negative invoice patterns

Setup: drop one URL into your Stripe webhook dashboard.

Once running, hit `GET /metrics/detectors` to see per-detector alert hit counts and severity breakdown in real time — useful for calibrating thresholds to your traffic volume. That's it. No OAuth, no SaaS subscription. Your Stripe data never leaves your machine.

Landing page / beta signup: [LIVE_URL]?ref=hn

Happy to answer questions about the detection logic — some of the edge cases in Stripe's retry behavior are surprisingly interesting.
```

---

## Timing Notes

- **Optimal HN window:** 9:00–10:00 AM ET on a weekday
- **Today's window opens:** 9:00 AM ET (March 10, 2026) — ~9 hours from now
- **LuLu setup takes 5 min** — do it before 8:55 AM
- **Temp cloudflared URL is fine** for beta signups (form writes to local DB)

---

## If the URL isn't ready by 9 AM

Options:
1. **Delay 24h** — post Wednesday 9 AM instead (still good timing)
2. **Use Formspree** as a fallback email collector — no backend needed, instant setup
3. **Use a "Coming Soon" Carrd page** — 5 min to set up, captures emails

---

## Follow-up Plan (if traction)

- Check HN comments every 30 min for first 2 hours
- Reply to every comment within the first hour (HN rewards engagement)
- DM engaged commenters with beta access link
- IH post goes Wednesday 10 AM, r/SaaS goes Thursday 10 AM (templates in `BETA_OUTREACH.md`)
