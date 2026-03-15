# BillingWatch — 14-Day Beta Follow-Up Email

**When to send:** Day 14 after signup (automated or manual)
**Subject:** 14 days in — what did BillingWatch catch for you?
**From:** Ray (personal founder address)
**Tone:** Direct, curious, low-pressure

---

## Email

**Subject:** 14 days in — what did BillingWatch catch for you?

Hey {name},

Two weeks ago you signed up for the BillingWatch beta. You've had enough time to see real webhook traffic run through it, so I want to check in properly.

Three quick questions:

**1. What pain did it actually catch?**
Did any detectors fire? Silent lapses, charge failure spikes, webhook lag? I'm collecting real anomaly stories to sharpen the detectors — even "nothing fired, which was reassuring" is useful data.

**2. What would make it 10x better?**
Not fishing for compliments. If there's a Stripe problem you've hit that BillingWatch didn't catch, or an alert that was too noisy, or a setup step that was confusing — I want to know. This is the feedback window that shapes the product.

**3. Would you pay for this?**
No commitment, no awkwardness. I'm figuring out pricing now. If BillingWatch caught something real, I'll be launching a paid tier ($29–49/mo range) with multi-tenant support, a managed cloud option, and priority alerting. If that's interesting to you, say so and I'll lock in a beta-alumni rate.

Reply directly to this email or hit me with a quick one-liner — anything works.

One more thing: if BillingWatch has been running quietly in the background without catching anything, check your webhook delivery logs. Sometimes the setup misses a Stripe event category and the detectors never see enough signal. Happy to debug with you.

— Ray

P.S. If you're done with the beta and want to unsubscribe from future emails, just reply "unsubscribe" — no hard feelings.

---

## Notes for Sending

- Personalize `{name}` before sending
- If sending manually, check `billingwatch.db` for user's signup date and first anomaly timestamp
- High-signal users (anomaly_count > 0): prioritize for personal replies
- Zero-anomaly users: lead with the P.S. debugging note in opening paragraph instead
- Upgrade interest responses → tag in CRM, follow up within 24h with pricing preview

---

## Upgrade Interest Follow-Up (if user says yes to question 3)

**Subject:** Re: 14 days in — here's what I'm building

Hey {name},

Thanks for the interest in the paid tier. Here's where I'm at:

**Launching:** ~Q2 2026
**Tiers (draft):**
- **Solo** ($29/mo): single Stripe account, all 10 detectors, email + webhook alerts
- **Team** ($49/mo): up to 5 Stripe accounts, Slack integration, alert routing by detector
- **Managed** (TBD): hosted version, no self-hosting required

Beta alumni pricing: 40% off first 12 months if you commit before launch. No payment now — I'll send a link when it's ready.

Want me to put you on the early-access list?

— Ray
