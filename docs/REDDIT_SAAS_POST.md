# r/SaaS Launch Post — BillingWatch
**Subreddit:** r/SaaS  
**Scheduled:** Thursday, March 12, 2026 @ 10:00 AM ET  
**Ref param:** `?ref=reddit`  
**URL to replace:** `[LIVE_URL]` → replace with live landing page URL before posting

---

## POST TITLE

```
I lost $800 in MRR before I noticed a silent payment failure. So I built a Stripe watchdog.
```

---

## POST BODY

```
Three Stripe retries. All failed. Subscription cancelled. I had no idea.

Found out when I looked at MRR the next week and it was down. By then the customer was gone.

The frustrating part: everything in Stripe's dashboard looked fine. The subscription showed as "cancelled" but there was no alert, no email that surfaced clearly, nothing that would've caught it in real time.

So I built BillingWatch — a self-hosted Stripe anomaly detector that runs against your webhook stream.

**What it watches:**
- Charge failure rate spikes (you set the threshold)
- Silent subscription lapses — payment fails, subscriber is still "active" in your system
- Webhook delivery lag — Stripe is sending, your server isn't processing
- Duplicate charges
- Revenue drop vs 7-day rolling average
- Fraud / card testing spikes
- Negative invoice patterns (bad promo code stacking, discount misconfigs)

**How it works:**
Add one URL to your Stripe webhook dashboard. BillingWatch receives every event, runs the detectors, fires an alert the instant something looks wrong. Email or webhook — your choice.

**Why self-hosted:**
Stripe data is sensitive. Revenue numbers, customer emails, charge amounts. I didn't want any of that going to a SaaS I don't control, so the whole thing runs on your own machine.

Once running, `GET /metrics/detectors` shows which detectors are firing and how often.

Once running,  shows which detectors are firing and how often — easy to tune thresholds to your traffic volume.

---

Launching beta this week. Free access in exchange for two weeks of real use + honest feedback on what the detectors miss.

Landing page + signup: [LIVE_URL]?ref=reddit

**Genuine question for this community:** What's your current setup for catching Stripe issues before they hit revenue? Datadog? Stripe Sigma? Something custom? Or just... you notice when MRR drops?
```

---

## FIRST COMMENT (post immediately after submission)

```
I'll add some context on why rule-based vs ML here:

The temptation was to do ML anomaly detection but the labeled data problem is brutal — you'd need months of real Stripe data with confirmed anomalies to train anything useful. Rule-based is less glamorous but it works on day one.

The trickiest detector was the silent lapse one. Stripe's retry timing is inconsistent and the event ordering between `invoice.payment_failed` and `customer.subscription.updated` isn't guaranteed. Took a few iterations to get that right without false positives.

Happy to dig into any of the detection logic if useful.
```

---

## PRE-POST CHECKLIST

- [ ] Replace `[LIVE_URL]` with actual live URL (e.g. `https://billingwatch.app`)
- [ ] Confirm landing page is publicly accessible and form submits
- [ ] Backend API health check passes
- [ ] Test `?ref=reddit` tracking works in DB
- [ ] Have GitHub repo link ready (beta users WILL ask for source)
- [ ] Schedule post for exactly 10:00 AM ET Thursday March 12

## ENGAGEMENT NOTES

- Respond to every comment in first 2 hours — Reddit algorithm rewards early engagement
- If someone asks "is this open source?" → yes, link GitHub repo
- If someone asks "how is this different from Stripe Radar?" → Radar is fraud-only; BillingWatch is operational anomalies (lapses, webhook lag, revenue drops)
- If someone asks for pricing → "Free self-hosted forever, beta access = 2 weeks feedback"
- Upvote-bait question at end ("how do YOU catch this?") is intentional — keep it in

---

*Generated: March 10, 2026 by Lucky | BillingWatch launch sequence*
