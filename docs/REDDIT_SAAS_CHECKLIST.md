# BillingWatch — r/SaaS Thursday Launch Checklist
*Created: 2026-03-10. Post Thursday March 12, 2026 at 10:00 AM ET*

---

## Pre-Post Steps (Wednesday night after IH post)

- [ ] **Note HN traction** (from LAUNCH_RESULTS.md):
  - If HN **50+ points**: Add to post body — *"Launched on HN Tuesday, 50+ upvotes — opening beta wider."*
  - If HN flopped: Don't mention. Start fresh.
- [ ] **Note IH engagement**: Check IH post from Wednesday — any notable feedback to weave in?
- [ ] **URL check**: Verify billingwatch.pages.dev (or current live URL) loads and beta form submits
- [ ] **Ref param**: Confirm `?ref=reddit` is in post URL

---

## Post Day — Thursday March 12, 9:50 AM ET

- [ ] Open: https://www.reddit.com/r/SaaS/submit
- [ ] **Post type**: Text (not link — text posts get more engagement on r/SaaS)
- [ ] **Title** (copy exactly):
  ```
  I lost $800 in MRR before I noticed a silent payment failure. So I built a Stripe watchdog.
  ```
- [ ] **Body**: paste from `~/Projects/BillingWatch/docs/REDDIT_SAAS_POST_FINAL.md` (update URL if different from billingwatch.pages.dev)
- [ ] **Post at exactly 10:00 AM ET** (r/SaaS traffic peaks 10AM-2PM ET weekdays)
- [ ] **Immediately post first comment** (already written in REDDIT_SAAS_POST_FINAL.md — ML vs rule-based context)
- [ ] Copy post URL → add to `docs/LAUNCH_RESULTS.md`

---

## First 2 Hours (Critical Engagement Window)

Reply to all comments. Keep replies SHORT. Let them ask follow-ups. Stock answers:

| Question | Reply |
|----------|-------|
| Open source? | Yes — [GitHub link] |
| Different from Stripe Radar? | Radar = fraud. BillingWatch = operational: silent lapses, webhook lag, revenue drops, duplicate charges. |
| Pricing? | Free. Self-hosted forever. Beta = 2 weeks honest feedback. |
| SaaS hosted version? | On the roadmap. Beta is self-hosted first to validate real usage patterns. |
| How to set up? | One webhook URL in Stripe. Add the server. 5 minutes. See QUICKSTART.md. |

---

## Success Metrics

| Metric | Good | Great |
|--------|------|-------|
| Upvotes (24h) | 20+ | 60+ |
| Comments | 10+ | 30+ |
| Beta signups via Reddit | 3+ | 10+ |
| Karma from first comment | 5+ | 20+ |

---

## Related Files
- Full post: `docs/REDDIT_SAAS_POST_FINAL.md`
- HN results: `docs/LAUNCH_RESULTS.md`
- IH checklist: `docs/IH_LAUNCH_CHECKLIST.md`
