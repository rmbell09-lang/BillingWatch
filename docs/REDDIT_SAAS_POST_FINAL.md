# r/SaaS Launch Post — BillingWatch (FINAL)
**Subreddit:** r/SaaS
**Scheduled:** Thursday, March 12, 2026 @ 10:00 AM ET
**Ref param:** `?ref=reddit`
**URL:** billingwatch.pages.dev

---

## POST TITLE

```
I lost $800 in MRR before I noticed a silent payment failure. So I built a Stripe watchdog.
```

---

## POST BODY

```
Three Stripe retries. All failed. Subscription cancelled. I had no idea until I checked MRR the following week. Customer was already gone.

The frustrating part: Stripe's dashboard showed "cancelled" but there was no real-time alert. No email that surfaced clearly. Nothing that said "hey, this just broke."

So I built BillingWatch — a self-hosted Stripe anomaly detector that hooks into your webhook stream.

**What it catches:**

- Charge failure rate spikes (configurable threshold)
- Silent subscription lapses — payment fails, subscriber still shows "active"
- Webhook delivery lag — Stripe sends, your server doesn't process
- Duplicate charges (same customer, same amount, <5 min apart)
- Revenue drops vs 7-day rolling average
- Fraud / card testing spikes
- Currency mismatches between subscription and charge
- Negative invoices from broken promo stacking

**Setup:** Add one webhook URL in Stripe. BillingWatch receives every event, runs 10 detectors, and fires an alert the instant something trips. Email, Slack, or Discord — your pick.

**Why self-hosted:** Stripe data is sensitive — revenue numbers, customer emails, charge amounts. I didn't want that going through a third-party SaaS. The whole thing runs on your machine. No data leaves.

`GET /metrics/detectors` shows which detectors are firing and how often. Thresholds are tunable per detector, and you can mark false positives so they stop showing up.

---

Launching beta this week. Free access in exchange for two weeks of real use + honest feedback on what the detectors miss.

Landing page + signup: billingwatch.pages.dev?ref=reddit

**Question for this community:** What's your current setup for catching Stripe issues before they hit revenue? Datadog? Stripe Sigma? Something custom? Or do you just notice when MRR drops?
```

---

## FIRST COMMENT (post immediately after submission)

```
Some context on why rule-based vs ML:

The temptation was ML anomaly detection, but the labeled data problem is brutal — you need months of real Stripe data with confirmed anomalies to train anything useful. Rule-based is less sexy but it works on day one with zero training data.

The trickiest detector was silent subscription lapses. Stripe's retry timing is inconsistent and event ordering between invoice.payment_failed and customer.subscription.updated isn't guaranteed. Took a few iterations to get the detection window right without drowning in false positives.

Happy to dig into any of the detection logic if people are curious.
```

---

## PRE-POST CHECKLIST

- [ ] Confirm billingwatch.pages.dev is live and form submits
- [ ] Backend API health check passes
- [ ] Test `?ref=reddit` tracking
- [ ] Have GitHub repo link ready (beta users WILL ask)
- [ ] Schedule post for exactly 10:00 AM ET Thursday March 12

## ENGAGEMENT RULES

- Respond to every comment in first 2 hours (Reddit algorithm rewards early engagement)
- "Is this open source?" → Yes, link GitHub
- "How is this different from Stripe Radar?" → Radar is fraud-only. BillingWatch catches operational anomalies: silent lapses, webhook lag, revenue drops, duplicate charges.
- "Pricing?" → Free. Self-hosted forever. Beta = 2 weeks feedback.
- Don't over-explain. Short replies. Let them ask follow-ups.

---

## CHANGES FROM DRAFT

- Removed duplicate "Once running" paragraph
- Tightened hook (cut 2 sentences)
- Updated detector list to 10 (added currency mismatch)
- Replaced [LIVE_URL] with actual billingwatch.pages.dev
- Shortened CTA section
- Cleaned engagement notes
