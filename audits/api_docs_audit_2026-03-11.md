# API_DOCS.md Completeness Audit
**Date:** 2026-03-11  
**Auditor:** Lucky (task-runner)  
**Method:** Grepped all `@router.*` and `@app.*` decorators across `src/api/` and cross-referenced against `docs/API_DOCS.md`

---

## Findings

### ❌ Version Mismatch
- **Docs say:** v1.0.0  
- **Code says:** v1.2.0 (`create_app()` and `/health` handler both return `"version": "1.2.0"`)

### ❌ `/health` Response Mismatch
- **Docs show:** `{"status": "ok", "service": "BillingWatch"}`  
- **Actual response includes:** `version`, `uptime_seconds`, `detector_count`, `last_event_at`

### ❌ Demo Run Endpoint — Wrong Signature
- **Docs show:** `GET /demo/run/{scenario_id}` (path parameter)
- **Actual:** `GET /demo/run?scenario=<name>` (query parameter)

### ❌ Entirely Undocumented Router: `/config`
- `GET  /config/thresholds` — returns all current thresholds + defaults
- `PATCH /config/thresholds` — update thresholds at runtime, reloads detectors live

### ❌ Undocumented Anomaly Endpoints
- `PATCH /anomalies/{alert_id}/false-positive` — mark alert as false positive
- `DELETE /anomalies/{alert_id}/false-positive` — unmark false positive
- `GET /anomalies/summary` IS documented but response is richer (now includes `false_positives` stats)

### ❌ Undocumented Metrics Endpoint
- `GET /metrics/detectors` — exists but not documented (docs only cover `/webhooks/detectors`)

### ❌ Entirely Undocumented Router: `/dashboard`
- `GET /dashboard` — HTML UI
- `GET /dashboard/summary` — JSON summary

### ❌ Entirely Undocumented Router: `/beta`
- `POST /beta/feedback` (status 201)
- `GET  /beta/feedback`
- `GET  /beta/feedback/summary`

### ❌ Entirely Undocumented Router: `/onboarding`
- `GET /onboarding/` — setup checklist

### ⚠️ Detector Count Language
- Docs say "All 7 detectors" in the table header, but code sets `detector_count = 10`
- Docs do mention 3 extra detectors in a footnote (`currency_mismatch`, `plan_downgrade_data_loss`, `timezone_billing_error`) — should be explicit in table

---

## Summary
| Category | Count |
|----------|-------|
| Version errors | 2 |
| Response schema mismatches | 2 |
| Entirely undocumented routers | 3 (/config, /beta, /onboarding) |
| Undocumented endpoints in documented routers | 3 |
| Wrong endpoint signature | 1 |
| **Total gaps/errors** | **11** |

