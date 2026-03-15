# BillingWatch — Next Tasks (v1.2 Roadmap)
*Updated: 2026-03-10 post-audit (Lucky task runner)*

Priority order. Top = highest impact on revenue/adoption.

## Already Shipped (This Cycle)
- [x] GET /metrics/detectors — per-detector alert hit counts + severity breakdown
- [x] GET /dashboard/summary — combined health snapshot (events + alerts + detectors)
- [x] HN objection reply templates (docs/HN_REPLY_TEMPLATES.md)
- [x] All 3 launch posts updated with /metrics/detectors feature proof
- [x] Historical Dashboard UI — dashboard_ui.py route, Chart.js, serves from /dashboard
- [x] False Positive Marking — PATCH /anomalies/{id}/false-positive + FP rate in /metrics/detectors
- [x] Slack/Discord Alert Channel — slack_discord.py, wired into AlertDispatcher
- [x] Beta Feedback Tracker — /beta/feedback POST endpoint (beta.py)

---

## 1. Cloudflare Workers Deploy (BLOCKER)
- **Why:** No live URL = no signups. Blocks all distribution.
- **Blocked on Ray:** CF creds + LuLu allow cloudflared. See LULU_SETUP.md.
- **Impact:** Unlocks everything downstream. This is the only thing that matters for Show HN.

## 2. Real Stripe Event Validation
- **Why:** Demo mode proves concept. Real test-mode Stripe events prove the product works.
- **What:** Connect Stripe test webhooks → verify all 10 detectors fire on real events.
- **Effort:** ~2 hours + Stripe CLI setup.
- **Impact:** Converts cool demo into "this actually works."
- **Note:** demo_events.py (scripts/) built for local simulation. Real Stripe test-mode not yet validated.

## 3. Multi-Tenant + Pricing (v2)
- **Why:** Can't charge without billing. Single-tenant blocks SaaS.
- **What:** API key auth, per-tenant storage, Free/Pro/$9/mo tiers.
- **Effort:** ~8 hours. Schema + auth middleware + Stripe billing integration.
- **Impact:** Revenue. Required for paid model.
- **Note:** MULTI_TENANT_SPEC.md is written. Implementation not started.

---

*For Ray: most impactful thing right now = deploy (#1). Everything else Lucky can build while blocked.*

---

## Unblocked Work (no CF, no Stripe CLI) — Added 2026-03-11

### 4. Rate Limiting on Webhook Endpoint
- **Why:** Security before launch. Prevents abuse/flooding.
- **What:** Add per-IP token bucket or rate limit middleware to /webhook
- **Effort:** ~1 hour
- **Agent:** lucky

### 5. CSV Export
- **Why:** Compliance/audit use case. Adds value for paying customers.
- **What:** GET /export/anomalies?start=&end= — streams CSV from existing DB
- **Effort:** ~1-2 hours
- **Agent:** lucky
- **Spec:** docs/V12_FEATURE_SPEC.md Feature 3

### 6. Email Digest (Stub)
- **Why:** Retention feature. Users need passive monitoring without checking dashboard.
- **What:** Build digest logic + schedule. Stub SMTP, plug in creds later.
- **Effort:** ~2-3 hours
- **Agent:** lucky
- **Spec:** docs/V12_FEATURE_SPEC.md Feature 1

### 7. Test Coverage Pass
- **Why:** Quality gate before v1.2 push. Know whats green before deploy.# BillingWatch — Unblocked Features Audit
*Audited: 2026-03-11 by Lucky task runner*

## Blocked (skip until Ray resolves)
- **CF Workers Deploy** — needs CF creds + LuLu allow rule (Ray)
- **Real Stripe Event Validation** — needs Stripe CLI + live test-mode setup (Ray)
- **Stripe payment link / billing** — can create manual Stripe dashboard link (no CLI), but requires Stripe account access (Ray)

## UNBLOCKED — Ready to Build (no CF, no Stripe CLI)

### 1. CSV Export (Light, ~1-2h, lucky)
- Export anomalies/events/alerts as CSV from existing DB
- Add GET /export/anomalies?start=&end= endpoint
- No external deps, pure backend
- Spec: docs/V12_FEATURE_SPEC.md Feature 3

### 2. Email Digest (Medium, ~2-3h, lucky)
- Weekly/daily email summary of anomaly hits
- Needs SMTP config (can default to local/dummy for now, stub with flag)
- Spec: docs/V12_FEATURE_SPEC.md Feature 1
- Can ship the logic + schedule, plug in real email creds later

### 3. Rate Limiting on Webhook Endpoint (Light, ~1h, lucky)
- Prevent abuse on /webhook ingestion
- Simple in-memory token bucket or per-IP counter
- No external deps, improves security posture before launch

### 4. Test Coverage Pass (Light, ~1-2h, lucky)
- tests/ directory exists but coverage unknown
- Run existing tests, identify gaps
- Add any obvious missing unit tests for detectors

### 5. Directory Submissions (Light, no-code, jinx)
- docs/DIRECTORY_SUBMISSION_LIST.md and SAAS_DIRECTORIES.md exist
- Jinx can draft submission copy per directory
- No CF or Stripe needed — just copy + links

### 6. Multi-Tenant API Key Auth Scaffold (Heavy, ~6-8h, lucky)
- MULTI_TENANT_SPEC.md written, not started
- Schema + per-key auth middleware + tenant isolation
- Complexity guard: requires full coding session with Ray

## Recommendation
Ship in this order (unblocked, lowest risk first):
1. Rate limiting (quick win, security)
2. CSV export (adds value, no deps)
3. Email digest (shipper feature, can stub email)
4. Test pass (quality gate before v1.2 push)
5. Directory submissions → assign to Jinx

Skip multi-tenant until CF is live and there are real signups to justify it.
