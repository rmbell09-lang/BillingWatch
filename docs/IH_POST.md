# BillingWatch — IndieHackers Launch Post
*Post Wednesday March 11, 2026 at 10:00 AM ET*
*Before posting: replace [LIVE_URL] with your actual URL + ?ref=ih*

---

## URL
https://www.indiehackers.com/post/new

## Title (copy exactly)
```
I built a self-hosted Stripe watchdog after a silent lapse wiped out $800 in MRR
```

## Body (copy-paste below the line, replace [LIVE_URL])

---

A few months ago I had a subscriber's card fail silently. Stripe retried three times over 7 days, all failed, cancelled the subscription — and never actually told me in a way that surfaced in my dashboard.

I noticed when MRR dropped. By then it was too late to recover that customer.

So I built BillingWatch.

**What it does:**
Watches your Stripe webhook stream in real time. Runs 7 detectors:
- Charge failure rate (configurable alert threshold)
- Silent lapses (failed payments with active subscribers)
- Webhook lag monitoring
- Duplicate charge detection
- Revenue drop alerts
- Fraud spike detection
- Negative invoice patterns

**How it works:**
You add one webhook endpoint to Stripe. BillingWatch receives every event, runs the detectors, and fires alerts (email, webhook, Slack — your choice) the moment something looks wrong.

Once running, `GET /metrics/detectors` gives you a real-time breakdown of which detectors are firing and at what severity — useful for calibrating thresholds to your traffic volume.

**Why self-hosted:**
Your Stripe data is sensitive. Revenue numbers, customer emails, charge amounts — I didn't want any of that going to a SaaS I don't control.

Currently in private beta. Free access in exchange for 2 weeks of use + honest feedback.

→ [LIVE_URL]?ref=ih

What billing anomalies have you had to discover the hard way?

---

## After Posting
- Reply to every comment within 1 hour (IH rewards engagement)
- DM active IH founders using the DM template in `docs/BETA_OUTREACH.md` (Section "IH DM")
- Target: founders who posted recently about SaaS billing, MRR, or churn

## Timing Note
Post Wednesday March 11 at 10 AM ET — day after Show HN.
If HN gets traction (50+ points), reference it: "Posted on HN yesterday, got great feedback — now opening beta wider."
If HN flopped, don't mention it — start fresh.
