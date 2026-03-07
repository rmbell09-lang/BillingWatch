# BillingWatch — Landing Page Copy + Pricing Strategy

## Target Customer

**Who:** SaaS founders and engineers running Stripe-powered businesses ($5K–$100K MRR)
**Pain:** Finding out about billing bugs from angry customers or Stripe dashboards — hours or days late
**Job to be done:** Know about billing anomalies immediately, before they become churn or chargebacks

---

## Landing Page Copy

### Hero Section

**Headline:**
> Your Stripe billing is on autopilot. BillingWatch makes sure it doesn't crash.

**Subheadline:**
> Real-time anomaly detection for Stripe webhooks. Catch duplicate charges, payment failures, and silent lapses before your customers do.

**CTA:** [Get Early Access] — [See how it works ↓]

**Social proof (placeholder):**
> "We caught a duplicate charge bug that was hitting 3% of upgrades — within 10 minutes of it starting." — Beta user

---

### Problem Section

**Headline:** Billing bugs are invisible until they're expensive

- 💸 A failed dunning flow silently lets subscriptions lapse — you find out at month-end
- 🔁 A promo code bug creates negative invoices — Stripe processes them without question
- 💳 Card testing fraud spikes your dispute rate — you get notified after the damage is done
- 🐢 Webhook processing stalls — events pile up, your app is blind, customers are confused

**Subtext:** You're probably already monitoring uptime and error rates. But nobody's watching your billing stream.

---

### Solution Section

**Headline:** 7 detectors. Zero blind spots.

| What BillingWatch watches | What it means for you |
|--------------------------|----------------------|
| Charge failure spike (>15%) | Dunning failure or payment method issue — catch it before churn |
| Duplicate charge | Same customer charged twice — know before they dispute |
| Fraud spike | Card testing or stolen cards — stop the bleeding immediately |
| Negative invoice | Broken promo stacking — your revenue numbers just got weird |
| Revenue drop (>15%) | Something's wrong upstream — find out in minutes, not days |
| Silent subscription lapse | Active sub, no payment — invisible churn accumulating |
| Webhook lag (>10 min) | Your event pipeline is backed up — your app is flying blind |

---

### How It Works

**Headline:** Drop in. Connect Stripe. Get alerts.

**Step 1:** Point your Stripe webhook at BillingWatch  
**Step 2:** BillingWatch validates every event and runs it through all 7 detectors  
**Step 3:** Get alerted via email or webhook when something looks wrong  

No code changes. No SDK to install. No dashboard to babysit.

---

### Pricing Strategy

#### Philosophy
- Price against the cost of a single billing bug (one undetected duplicate charge dispute = $15 chargeback + potential account flag)
- Charge on MRR range — larger businesses have more at stake and more events
- Simple tiers, no per-event pricing (complexity kills conversions)

#### Recommended Tiers

**Hobby — $0/mo**
- Up to 500 events/month
- All 7 detectors
- Email alerts only
- 1 Stripe account
- No SLA
- *Goal: Get people in, prove value*

**Starter — $29/mo**
- Up to 10,000 events/month
- All 7 detectors
- Email + webhook alerts
- 1 Stripe account
- 30-day event history
- *Target: <$10K MRR SaaS*

**Pro — $99/mo**
- Up to 100,000 events/month
- All 7 detectors + custom thresholds
- Email + webhook + Slack alerts
- 3 Stripe accounts
- 90-day event history
- Monthly anomaly digest report
- *Target: $10K–$100K MRR SaaS*

**Scale — $299/mo**
- Unlimited events
- Custom detector rules
- Priority support
- Unlimited Stripe accounts
- 1-year event history
- API access for custom integrations
- *Target: $100K+ MRR or multi-product*

#### Pricing Rationale
- $29 Starter: BillingWatch pays for itself if it catches one extra dunning failure per month (avg subscription $30+)
- $99 Pro: For a $50K MRR business, one caught duplicate charge dispute saves more than the monthly fee
- Annual discount: 2 months free (16% off) to reduce churn
- Beta pricing: First 20 customers lock in Starter at $19/mo or Pro at $69/mo for life

---

### CTA Section

**Headline:** Stop finding out about billing bugs from your customers.

**Subtext:** BillingWatch watches your Stripe stream 24/7 so you don't have to.

**Primary CTA:** [Start Free — No Credit Card] → links to signup  
**Secondary CTA:** [See a live demo] → screen recording of alert firing

---

### FAQ

**Q: Do I need to change my Stripe setup?**  
A: Just add a webhook endpoint. That's it.

**Q: What if I already use Stripe Radar?**  
A: Radar catches fraud at the authorization level. BillingWatch catches anomalies in your billing *patterns* — stuff Radar doesn't see.

**Q: Is my Stripe data safe?**  
A: We only receive webhook event payloads — the same data Stripe sends to any endpoint. We never store card numbers or customer PII beyond what's in the event.

**Q: What if I want a detector Stripe doesn't support?**  
A: Pro and Scale plans support custom detector rules. Tell us what you want to catch.

---

## Beta Positioning

For the first 10–20 customers, lean on:

1. **Free access during beta** — in exchange for feedback and a testimonial
2. **White-glove onboarding** — 30-min call to configure and explain the detectors
3. **Lifetime discount** — beta customers lock in 30% off forever
4. **Co-design** — "What billing edge case keeps you up at night?" → build it

This gets testimonials, product feedback, and word-of-mouth before paid launch.

---

## Positioning vs Alternatives

| Alternative | Why BillingWatch wins |
|-------------|----------------------|
| DIY Stripe webhook monitoring | Takes weeks to build, needs maintenance |
| Stripe Radar | Fraud only, no operational anomalies |
| Datadog/Grafana | Requires instrumentation, expensive, overkill |
| Watching the Stripe dashboard | Reactive, not proactive |
| Nothing | Most common — and most risky |

**One-liner:** "The billing watchdog for Stripe-powered SaaS — catches what Stripe won't tell you."
