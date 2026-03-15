# HN Reply Templates — BillingWatch Show HN

Ready-to-adapt replies for common HN objections. Don't copy-paste — use the angle and adapt to the specific comment.

---

## "Too niche — who actually needs this?"

**Angle:** Every SaaS with recurring billing has had a billing bug they didn't catch. The question isn't IF, it's when.

> Fair question. We built this because we've personally been burned by billing bugs — duplicate charges that went unnoticed for weeks, currency mismatches during expansion, timezone issues around renewal boundaries. These aren't hypothetical. Stripe's own status page shows incidents regularly. The problem is most teams only find out when a customer complains (or churns). BillingWatch catches it in real-time so you don't have to wait for the angry email.

---

## "Why not just use Datadog / Sentry / existing monitoring?"

**Angle:** Generic monitoring doesn't understand billing semantics. Datadog alerts on metrics, not business logic.

> Datadog is great for infra monitoring — CPU spikes, error rates, latency. But it doesn't know that charging someone $99.99 twice in 30 seconds is a duplicate, or that a USD subscription suddenly getting billed in EUR is a currency mismatch. BillingWatch has 10 purpose-built detectors that understand Stripe billing semantics. You could build custom Datadog monitors for each of these, but that's essentially rebuilding BillingWatch inside your monitoring stack.

---

## "What about pricing? / Is this worth paying for?"

**Angle:** One caught duplicate charge pays for years of BillingWatch. The ROI math is trivial.

> A single undetected duplicate charge that leads to a chargeback costs you $15-25 in fees plus the refund, plus customer trust damage. A billing bug that affects 1% of renewals for even a week on a $50 MRR product with 500 customers is $2,500 in refunds + support time. BillingWatch is designed to catch these in real-time, before they become chargebacks. The pricing will reflect that — we're keeping it accessible for indie SaaS and startups.

---

## "Can't I just write a script for this?"

**Angle:** You can. Most people say that then never do it. And when they do, they miss edge cases.

> Absolutely. The first version of BillingWatch was exactly that — a script. Then we added duplicate detection. Then currency checking. Then timezone edge cases. Then webhook lag monitoring. Then silent lapse detection. Then we realized we'd built a product. The 10 detectors we ship today represent patterns we've seen cause real revenue loss. You can definitely build it yourself — but the question is whether your time is better spent on your actual product.

---

## "How does this compare to Stripe's built-in fraud detection?"

**Angle:** Stripe Radar catches fraud. BillingWatch catches YOUR bugs. Different problems entirely.

> Stripe Radar is excellent at catching fraudulent payments — stolen cards, suspicious patterns from bad actors. BillingWatch catches something different: legitimate billing operations that have gone wrong on YOUR side. Things like your code accidentally sending duplicate charges, subscription renewals happening in the wrong currency after a migration, or charges being processed at midnight UTC when the customer's timezone means they should renew tomorrow. These aren't fraud — they're bugs in your billing integration. Stripe can't detect those because from Stripe's perspective, your API calls look intentional.

---

## "Show me a real example / Does this actually work?"

**Angle:** Point to the demo mode and detector list.

> We ship a demo mode that generates realistic Stripe events and runs all 10 detectors against them. You can see exactly what gets caught: `POST /demo/run` fires a batch and shows detected anomalies in real-time. The detectors cover: charge failure spikes, duplicate charges, fraud spikes, negative invoices, revenue drops, silent subscription lapses, webhook lag, currency mismatches, timezone billing errors, and plan downgrade data loss. Each one was built because we've seen it happen in production.

---

## "Is this open source?"

**Angle:** Yes, and that's intentional.

> Yes — the core detection engine is fully open source. We believe billing integrity shouldn't be locked behind a paywall. The hosted version (coming soon) adds dashboards, alerting integrations, and historical analysis, but the detection logic is yours to inspect, fork, and extend.

---

## "What's your stack?"

**Angle:** Keep it simple and technical.

> Python + FastAPI for the API, SQLite for event storage (designed for easy swap to Postgres), 10 detector modules that each implement a simple interface. Stripe webhooks come in, get stored, then each detector runs against recent events and flags anomalies. SMTP alerts for now, Slack/PagerDuty planned. The whole thing runs locally in minutes — no cloud dependencies for the self-hosted version.

