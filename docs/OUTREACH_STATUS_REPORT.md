# BillingWatch — Outreach Status Report
*Compiled by Lucky — March 11, 2026 12:15 AM ET*

## Executive Summary
**0 out of ~30 outreach actions executed.** Everything is blocked on a live URL (deploy via cloudflared or CF Pages). No prospects have been contacted. No posts have been submitted. No directory listings filed.

## Outreach Asset Inventory

### 1. Cold DMs — 10 Prospects Written (0 Sent)
| # | Target | Platform | Status | Blocked On |
|---|--------|----------|--------|------------|
| 1 | @filippanoski (Bazzly, $1K MRR) | IH DM | ❌ Not sent | Live URL |
| 2 | Generic $10K-$30K MRR founder | IH DM | ❌ Not sent | Live URL + personalization |
| 3 | Reddit GetRackz thread engagers | Reddit DM | ❌ Not sent | Live URL |
| 4 | Solo dev Stripe-to-QB | Reddit DM | ❌ Not sent | Live URL |
| 5 | Unknown 5th prospect | Reddit DM | ❌ Not sent | Live URL |
| 6 | @swizec (Stripe opinions) | Twitter DM | ❌ Not sent | Live URL |
| 7 | @marc_louvion (IH, multi-product) | IH DM | ❌ Not sent | Live URL |
| 8 | @dannypostmaa (serial builder) | Twitter DM | ❌ Not sent | Live URL |
| 9 | @csallen (IH founder) | IH DM | ❌ Not sent | Live URL |
| 10 | @levelsio ($4M+ ARR) | Twitter DM | ❌ Not sent | Live URL |

### 2. Platform Launch Posts — 3 Ready (0 Posted)
| Platform | Doc | Target Date | Status |
|----------|-----|-------------|--------|
| Show HN | SHOW_HN_FINAL.md | Mar 10 9AM (MISSED) | ❌ Not posted — no live URL |
| Indie Hackers | IH_POST.md | Mar 11 10AM | ❌ Not posted — no live URL |
| r/SaaS | REDDIT_SAAS_POST.md | Mar 12 10AM | ❌ Not posted — no live URL |

### 3. Community Posts — 8 Communities Mapped (0 Posted)
| Community | Priority | Post Angle | Status |
|-----------|----------|------------|--------|
| r/stripe (~50K) | ⭐ TOP | Problem-first: silent lapse story | ❌ Pending |
| r/SaaS (~150K) | ⭐ TOP | Question: what billing issue cost you? | ❌ Pending |
| r/webdev (~800K) | HIGH | Technical deep-dive: how I built it | ❌ Pending |
| r/Entrepreneur (~1.2M) | MEDIUM | Revenue loss story | ❌ Pending |
| r/startups | MEDIUM | Lessons from 3 billing failures | ❌ Pending |
| IH Main Feed | ⭐ TOP | Full origin story + beta ask | ❌ Pending |
| IH Stripe & Payments group | HIGH | Niche community, high intent | ❌ Pending |
| Dev.to | MEDIUM | Technical article (DEVTO_POST.md ready) | ❌ Pending |

### 4. Directory Submissions — 5+ Identified (0 Submitted)
| Directory | Priority | Cost | Time to List |
|-----------|----------|------|-------------|
| Product Hunt | TIER 1 | Free | Same day |
| SaaSHub | TIER 1 | Free | 1-3 days |
| AlternativeTo | TIER 1 | Free | 24-48h |
| BetaList | TIER 1 | Free ($129 fast) | 2-4 weeks |
| Capterra | TIER 1 | Free | 3-7 days |

### 5. Email Sequences Written (0 Deployed)
| Sequence | Doc | Status |
|----------|-----|--------|
| 3-email onboarding | ONBOARDING_EMAILS.md | ✅ Written, not deployed |
| Beta welcome | BETA_WELCOME_EMAIL.md | ✅ Written, not deployed |
| 14-day follow-up | BETA_FEEDBACK_EMAIL_14DAY.md | ✅ Written, not deployed |
| Upgrade drip (3 emails) | UPGRADE_EMAIL_SEQUENCE.md | ✅ Written, not deployed |
| Cold email sequence | COLD_EMAIL_SEQUENCE.md | ✅ Written (Jinx), not deployed |
| Testimonial requests | TESTIMONIAL_REQUEST_EMAIL.md | ✅ Written, not deployed |
| Community DM sequence | COMMUNITY_DM_SEQUENCE.md | ✅ Written, not deployed |

## Hit Rate
- **Prospects contacted:** 0 / 10
- **Posts published:** 0 / 3 scheduled
- **Communities posted to:** 0 / 8
- **Directories submitted:** 0 / 5
- **Emails sent:** 0

## Root Cause
**Single blocker: no live URL.** BillingWatch runs locally on Mac Mini (API port 8000, landing port 8080). CF deploy is blocked on:
1. LuLu must allow cloudflared binary outbound
2. Ray must run `cloudflared tunnel --url http://localhost:8080`

Every single outreach asset contains `[REPLACE WITH URL]` or `[LIVE_URL]` placeholder.

## Next 10 Priority Targets (Once Live)
| # | Target | Channel | Why First | Approach |
|---|--------|---------|-----------|----------|
| 1 | Show HN | HN | Highest signal, time-sensitive | Post SHOW_HN_FINAL.md immediately |
| 2 | r/stripe | Reddit | Highest intent audience | Problem-first post, link as footnote |
| 3 | IH Main Feed | IH | Bootstrapper audience, story format | Origin story + beta ask |
| 4 | @swizec | Twitter DM | Warm angle (Stripe complaints) | Personalized DM |
| 5 | @levelsio | Twitter DM | Massive reach if he engages | Anti-complexity pitch |
| 6 | Product Hunt | Directory | High launch-day traffic | Schedule Tue-Thu, engage all day |
| 7 | SaaSHub | Directory | SEO, appears in alternatives | Submit profile immediately |
| 8 | r/SaaS | Reddit | REDDIT_SAAS_POST.md ready | Question-format post |
| 9 | Dev.to | Blog | DEVTO_POST.md ready | Technical article |
| 10 | @marc_louvion | IH DM | Multi-product = billing surface area | Personalized DM |

## Recommendation
**Unblock the deploy.** Everything else is ready. The moment a live URL exists:
- Hour 1: Post Show HN + IH + r/stripe
- Hour 2-4: Send top 5 cold DMs
- Day 1: Submit to SaaSHub, AlternativeTo, Product Hunt
- Day 2-3: r/SaaS, Dev.to, community posts
- Week 1-2: Directory submissions, email sequences live
