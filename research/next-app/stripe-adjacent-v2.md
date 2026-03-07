# Next App Research: Stripe-Adjacent Tools Still Unsolved (2026)

**Researched by:** Lucky
**Date:** 2026-03-07
**Method:** Live web research (Reddit r/SaaS, HN Algolia, real complaint threads)
**Context:** BillingWatch is live. What's the next self-hosted Stripe tool worth building?

---

## Research Sources

1. **r/SaaS thread** — "Built my SaaS using mostly AI - here's what broke in production" (top post, 2026)
   - Quote: "Billing logic that created accounting nightmares: Proration calculations, failed payment retries, subscription upgrades, and refund handling — one customer downgrading triggered THREE separate billing events."
   
2. **HN comment** — Stripe Billing launch thread (2018, but still referenced)
   - Quote: "What we really needed was detail about exactly what would happen if we configured dunning to retry — which objects get created, which webhooks fire at which points in the try/retry/give-up process. None of this is in the documentation."
   - Quote: "Address verifications are all-or-nothing. Either we skip them (worse for fraud) or we use them (customers who move and don't update get their subscription failed)."

3. **HN story** — B2B SaaS starter (open-source)
   - Highlights vendor lock-in pain: "Billing per invocation. Fine for prototypes, but costs unpredictable at scale."
   - Confirms demand for self-hosted, infrastructure-owned solutions

---

## Opportunity Matrix

### 1. Smart Dunning Orchestrator
**What:** Beyond Stripe's basic 4-retry dunning, build an intelligent retry engine that:
- Classifies failure reasons (insufficient funds vs. expired card vs. fraud vs. do-not-honor)
- Routes each failure type to a different recovery flow (timing, messaging, escalation)
- Tracks recovery rate per strategy
- Self-hosted, no SaaS fee

**Stripe's gap:** Documented extensively in HN comment above. Stripe gives you on/off dunning but zero intelligence about what actually happens under the hood. No strategy customization by failure type.

**Existing alternatives:** Churn Buster ($99+/mo SaaS), Recover (SaaS), Baremetrics Recover ($49+/mo)

**Self-hosted angle:** Strong. You own the retry logic. Your customer contact data never leaves your machine.

**Complaint frequency:** HIGH — every SaaS with >10 paying customers hits this.
**Build complexity:** MEDIUM — webhook-driven, builds directly on BillingWatch architecture.
**Estimated dev time:** 2-3 weeks (reuses BillingWatch detector framework)
**Revenue potential:** Churn Buster charges $99+/mo. Self-hosted equivalent with a one-time price = clear value prop.

**Score: 9/10**

---

### 2. Self-Hosted MRR Reconciliation Engine
**What:** Calculates TRUE MRR/ARR that matches your bank account, reconciling:
- Stripe's native MRR (includes trials, coupons, proration — often wrong)
- Actual revenue recognized (accounting standard)
- Churn, expansion, contraction breakdown
- Dispute/refund impact on historical metrics

**Stripe's gap:** Stripe's own MRR display diverges from accounting reality. Proration creates fractional charges that distort monthly numbers. Multiple founders on r/SaaS have noted their Stripe MRR and actual deposited cash never match.

**Existing alternatives:** Baremetrics ($50-$500/mo), ChartMogul ($49-$100+/mo), ProfitWell (acquired by Paddle)

**Self-hosted angle:** Very strong. Revenue numbers are your most sensitive data. Founders shouldn't pipe this to a SaaS.

**Complaint frequency:** HIGH — literally every founder tracking revenue.
**Build complexity:** HIGH — need to understand revenue recognition rules, handle edge cases (annual plans, proration math, disputes).
**Estimated dev time:** 4-6 weeks
**Revenue potential:** Replacing $50-100/mo subscriptions with a one-time purchase = strong LTV

**Score: 8/10**

---

### 3. Subscription Pause Manager
**What:** Handles the "pause my subscription" request that Stripe doesn't natively support:
- Stores pause state locally (Stripe has no native pause)
- Handles pause via trial period extension (cleanest Stripe hack)
- Sends configured pre-pause win-back email sequence
- Tracks pause→resume vs. pause→cancel conversion rates
- Auto-resumes on schedule

**Stripe's gap:** No native pause. Common workaround is free trial extension which has side effects, or custom metadata + cron job. Both are fragile and poorly documented.

**Complaint frequency:** MEDIUM — most common in B2C SaaS with seasonal users.
**Build complexity:** LOW-MEDIUM — thin Stripe API wrapper + state machine.
**Estimated dev time:** 1-2 weeks
**Revenue potential:** Lower — this is a feature, not a full product.

**Score: 6/10** — Could be a BillingWatch module, not a standalone app.

---

### 4. Proration Anomaly Detector (BillingWatch Extension)
**What:** Extends BillingWatch with a new detector that flags when upgrade/downgrade proration creates unexpected billing events — catches the "three billing events from one downgrade" class of bug.

**Note:** This is probably just a new BillingWatch detector, not a new app.

**Score: 5/10** — Add to BillingWatch roadmap, not standalone.

---

## Ranked Opportunities

| Rank | Opportunity | Score | Complexity | Timeline | Differentiator |
|---|---|---|---|---|---|
| 1 | Smart Dunning Orchestrator | 9/10 | Medium | 2-3 weeks | Self-hosted, free vs $99+/mo SaaS |
| 2 | MRR Reconciliation Engine | 8/10 | High | 4-6 weeks | Revenue data stays local |
| 3 | Subscription Pause Manager | 6/10 | Low | 1-2 weeks | Feature, not product |

---

## Recommendation

**BUILD NEXT: Smart Dunning Orchestrator**

Reasons:
1. Direct extension of BillingWatch's webhook architecture — reuses everything already built
2. Replaces $99-199/mo SaaS tools (Churn Buster, Recover) with self-hosted equivalent
3. HN + Reddit both confirm this is an active, ongoing pain point (not solved)
4. 2-3 week build timeline is realistic
5. Natural cross-sell to BillingWatch users ("You're monitoring failures — now recover them")

**Name ideas:** RecoverWatch / DunningAgent / RetryIQ / RevenueGuard

**MRR Reconciliation Engine** is a strong #2 but complexity is higher and requires deeper accounting knowledge. Worth building after Dunning Orchestrator ships.

---

## DECISION: ACT

Build Smart Dunning Orchestrator as next app. Start spec document after BillingWatch launch is complete and has initial users.

**Next step:** After BillingWatch gets first 3 beta users → start SPEC.md for dunning orchestrator.
