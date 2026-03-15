# BillingWatch — Unblocked Features Audit
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
