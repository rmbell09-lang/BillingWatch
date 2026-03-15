# HN Launch Metrics — BillingWatch
**Generated:** 2026-03-11 03:11 AM ET  
**Launch:** Show HN — March 10, 2026 @ 9:00 AM EDT

---

## Beta Signups

| Metric | Count |
|--------|-------|
| Total signups (all-time) | 3 |
| **Post-launch signups (since Mar 10 9AM EDT)** | **0** |
| Pre-launch signups (test/seed) | 3 |

### Signup Breakdown
| ID | Email | Feedback | Timestamp (UTC) | Status |
|----|-------|----------|-----------------|--------|
| 1 | test@test.com | "yes - detected a webhook lag spike" | 2026-03-10 08:49 | Pre-launch test |
| 2 | _(empty)_ | _(none)_ | 2026-03-10 09:13 | Pre-launch test |
| 3 | _(empty)_ | startup_test | 2026-03-10 09:13 | Pre-launch test |

> **Note:** All 3 signups are pre-launch test entries (before 9AM EDT cutoff). Zero organic signups captured from HN traffic so far. Landing page was live and returning 200 at time of report.

---

## API Health (at report time)

| Check | Status |
|-------|--------|
| API | ✅ UP |
| Version | 1.2.0 |
| Uptime | 11h 42m |
| Landing page (port 8080) | ✅ UP (HTTP 200) |

---

## Webhook Events Processed

| Metric | Count |
|--------|-------|
| Total events processed | 108 |
| **Events since HN launch** | **42** |
| Events last hour (3AM check) | 0 |

### Event Type Breakdown (all-time)
| Type | Count |
|------|-------|
| charge.failed | 45 |
| charge.dispute.created | 30 |
| charge.refunded | 16 |
| payment_intent.succeeded | 10 |
| charge.succeeded | 3 |
| customer.subscription.deleted | 2 |
| invoice.payment_failed | 2 |

> Most events appear to be test/demo data from pre-launch validation runs.

---

## Launch Day Summary

- **Outcome:** HN post went live March 10. Zero organic beta signups captured.
- **Infrastructure:** Fully operational — API up, landing page serving, webhook processing working.
- **Signal:** 42 webhook events processed post-launch window, but likely test traffic, not real user webhooks.
- **Follow-up needed:** Check HN post engagement (comments/upvotes). Consider whether beta form was discoverable on landing page.

---

*Source: `billingwatch.db` (beta_feedback + events tables), `scripts/launch_monitor.sh`*
