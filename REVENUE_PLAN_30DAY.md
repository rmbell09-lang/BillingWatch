# BillingWatch — 30-Day Post-Launch Revenue Plan
*Written: 2026-03-10 by Lucky | Clock starts: Day 1 = first live Cloudflare URL*

---

## North Star Metrics

| Metric | 30-Day Target |
|---|---|
| Beta signups (email captured) | 50 |
| Active beta installs (webhook connected) | 15 |
| Beta → paid conversions | 5 |
| MRR at Day 30 | $135 (5 × $27/mo) |
| Feedback responses received | 20 |

These are conservative. If HN post hits front page: 3× all numbers.

---

## Pricing (Current Hypothesis)

| Tier | Price | Limits | Target Buyer |
|---|---|---|---|
| Free | $0 | 1 Stripe account, 500 events/mo, email alerts only | Solo devs, side projects |
| Pro | $27/mo | 3 Stripe accounts, unlimited events, Slack + Discord | Small SaaS, indie hackers |
| Team | $79/mo | 10 accounts, priority support, webhook history 90d | Agencies, funded startups |

**Why $27:** $29 feels "picked from a hat." $27 is odd enough to signal thought. Anchors well against $79.

**Pricing experiment queue (run in order):**
1. Launch at $27 → measure conversion rate for 2 weeks
2. Test $19 vs $27 with outreach — manual A/B, alternate the pitch
3. If Team tier gets zero interest in 30 days → kill it, push Pro to $39

---

## Week-by-Week Plan

### Week 1 — Seed the Funnel (Days 1–7)
**Goal:** 20 signups, 5 webhook installs

- [ ] **Day 1:** Post Show HN using BETA_OUTREACH.md template. Post between 9–11 AM ET Tuesday or Wednesday.
- [ ] **Day 1:** Share in r/SaaS and r/stripe — separate posts, not cross-posts.
- [ ] **Day 2:** DM 10 indie hackers from IH who have Stripe-based products. Tight pitch: "Built a billing watchdog for Stripe — would you try it?"
- [ ] **Day 3:** Post Show IH on Indiehackers.com — full post.
- [ ] **Day 4–5:** Follow up with signups who haven't installed. One email, no nagging.
- [ ] **Day 6:** Drop in 5 Slack communities — SaaS founders, indie hackers, etc. Use #share-your-work or equivalent channels.
- [ ] **Day 7:** Review signups → identify top 3 most engaged → personal DM offering setup help.

### Week 2 — Activation Push (Days 8–14)
**Goal:** Get 10 of 20 signups to actually connect Stripe

- [ ] Email all beta signups: "Here's the 5-minute setup guide."
- [ ] Offer 1:1 onboarding call (30 min, free) to first 10 installs — closes the activation loop.
- [ ] Write 2 short posts: "What we caught in beta" (real detector hits) + "Why Stripe doesn't tell you this."
- [ ] Collect 5+ feedback responses via /beta/feedback endpoint or email reply.
- [ ] Watch for first organic conversion — if none by Day 14, drop Pro to $19 and test.

### Week 3 — Conversion (Days 15–21)
**Goal:** 3+ paid conversions

- [ ] Email active installs: "You've seen X alerts. That's $27/mo to never miss one."
- [ ] Add urgency: "Beta pricing ends April 1st — Pro locks at $27 forever for early users."
- [ ] Set up Stripe payment link — even a manual link is fine at this stage.
- [ ] For anyone who bounced after signup: one-line reactivation — "Did the install get stuck? I'll help."
- [ ] Post case study if any beta user allows it — anonymized is fine.
- [ ] Check: if conversion rate is below 10% of active users → run $19 test.

### Week 4 — Revenue Baseline and Iterate (Days 22–30)
**Goal:** 5 paid, $135 MRR, clear roadmap signal from users

- [ ] Calculate the full funnel: signups → install → paid. Write it down.
- [ ] Survey all paid users: "What would make you upgrade to Team?" Validates or kills the $79 tier.
- [ ] If any churn: call or DM them. One retention save is worth 3 new signups.
- [ ] Price experiment result: did $19 or $27 convert better? Lock in the winner.
- [ ] Write Month 2 plan based on real data — not this plan.

---

## Outreach Cadence (Master)

| Day | Action | Channel |
|---|---|---|
| 1 | Show HN post | Hacker News |
| 1 | r/SaaS and r/stripe posts | Reddit |
| 2 | 10 IH founder DMs | Indiehackers |
| 3 | Full IH post | Indiehackers |
| 4 | Follow-up signups with no install | Email |
| 6 | Slack community drops | Slack |
| 7 | DM top 3 engaged users | Direct |
| 8 | Setup guide email to all signups | Email |
| 10 | "What we caught" content post | IH + others |
| 15 | Conversion pitch to active installs | Email |
| 22 | Survey all paid users | Email |
| 28 | Month 2 plan kickoff | Internal |

---

## Pricing Experiments Detail

### Experiment A: $27 baseline (Days 1–14)
- Ship at $27 Pro.
- Track: how many active installs convert without any pitch email.
- Baseline conversion rate = organic paid / total installs.

### Experiment B: $19 test (Days 15–21, if A underperforms)
- Drop price to $19 in pitch emails only — landing page stays $27.
- "Beta rate: $19/mo for the first 20 customers, then $27."
- Compare conversion rate vs Experiment A.

### Experiment C: Annual plan (Day 21+)
- Offer $199/yr Pro if 5+ paid users exist.
- Annual upfront = instant MRR spike + lower churn.
- Only worth doing once monthly is proven.

---

## Blockers That Kill This Plan

1. **No live URL** — everything above is zero without Cloudflare deploy. Still Day 0.
2. **No Stripe payment link** — can hand-collect initially but does not scale past 3 customers.
3. **No email sending** — need SMTP configured. Verify this works before launch.

---

## What Success Looks Like at Day 30

| Outcome | MRR | Signal |
|---|---|---|
| Floor | $81 (3 paid) | Product proved. Keep building. |
| Target | $135 (5 paid) | Pricing validated. Write Month 2 plan. |
| Stretch | $270 (10 paid) | Real traction. Time to invest in content and proper billing. |

If we hit $270 MRR in 30 days from a Show HN post and some DMs, this thing has legs.

---

*Next review: Day 14 — targeting March 24 if Day 1 = March 10 launch*
