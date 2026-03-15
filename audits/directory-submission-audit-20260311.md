# BillingWatch — Directory Submission Audit
*Audited: 2026-03-11 by Lucky (task runner)*

## Status: NOTHING SUBMITTED YET
All submissions blocked on live URL. CF deploy needs Ray's credentials (PRE-LAUNCH-STATUS.md).

---

## Critical Issue: TWO CONFLICTING FILES + TWO DIFFERENT PRODUCT FRAMINGS

### File 1: `docs/DIRECTORY_SUBMISSION_LIST.md` (24 directories, Mar 10)
- **Framing:** "Stop paying for SaaS you don't use" — subscription management for end users
- More comprehensive, better tier organization

### File 2: `docs/DIRECTORY_SUBMISSIONS.md` (older)
- **Framing:** "AI-powered billing anomaly detection for Stripe" — developer tool, self-hosted
- Has status tracking table (all empty)

These are different products targeting different audiences. Need to align on positioning before submitting or we land in wrong categories.

---

## Directory Coverage Comparison

### In File 1 only (not in File 2):
- Capterra, G2, GetApp, Software Advice (Gartner ecosystem — high B2B value)
- Slant, ToolFinder, Futurepedia, SaaSGenius, Crozdesk, Trustpilot, Sourceforge, BetaList

### In File 2 only (not in File 1):
- DevHunt (dev tool launches — highly relevant for Stripe anomaly detector framing)
- StackShare (tech stack — relevant for dev tool angle)
- Crunchbase, AngelList, Wellfound (investor-facing)
- StartupBase, SideProjectors, All Top Startups, Uneed

### Combined unique count: ~35+ directories across both files

---

## Recommended Submission Priority (Once Live URL Exists)

**Week 1:**
1. SaaSHub — strong "alternatives" SEO
2. G2 — B2B buyer intent, enormous SEO
3. AlternativeTo — critical for discovery
4. Product Hunt — coordinate launch day (Tue/Wed/Thu)
5. BetaList — early adopters

**Week 2:**
6. Capterra + GetApp + Software Advice (Gartner trio)
7. DevHunt + Uneed (dev community)
8. Show HN — Ray posts manually per PRE-LAUNCH-STATUS.md
9. Indie Hackers product listing

**Week 3+:**
10. MicroLaunch, Launching Next, Startup Stash
11. Crunchbase, AngelList
12. StackShare

---

## Assets Status (Unconfirmed)
- [ ] Logo 240x240px PNG
- [ ] Screenshots (3-5 product shots)
- [ ] Demo GIF/video
- [ ] Canonical long description (two versions exist — pick one)

Verify assets before starting the submission sprint.

---

## Action Items for Ray

1. **Decide positioning**: Developer tool (Stripe anomaly detector) vs SaaS spend management? Different audience, different directories.
2. **CF deploy first** — no live URL = can't submit anywhere
3. **Merge the two directory files** into one canonical list with status tracking
4. **Confirm assets are ready** before submission sprint

---

## Files Audited
- `docs/DIRECTORY_SUBMISSION_LIST.md`
- `docs/DIRECTORY_SUBMISSIONS.md`
- `scripts/submit_directories.py` (exists, functionality unverified)
