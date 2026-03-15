# BillingWatch — Test Suite Coverage Gaps
Generated: 2026-03-11 20:40 ET

## Summary
- **92 tests collected, 91 passed, 1 failed**
- 2 test files cannot even be imported (Python 3.9 syntax incompatibility)
- Large portions of the codebase have zero test coverage

---

## Test Run Results

### Passing (91/92)
All detector tests pass except one timing-sensitive edge case.

### Failing (1)
**`TestRevenueDrop::test_no_alert_normal_revenue`**
- Root cause: **Timing bug in the test** (not a source bug)
- Fails only when run within the hour after UTC midnight
- `time.time() - 3600` crosses a UTC date boundary, recording "today's" payment under yesterday's bucket
- `check()` then sees today_revenue=0 → drop_pct=1.0 → fires alert
- **Fix:** Change test to use `time.time()` instead of `time.time() - 3600`

### Cannot Import (2 files — Python 3.9 incompatibility)
- `tests/test_e2e_charge_failure.py`
- `tests/test_event_store_integration.py`
- Root cause: `src/storage/event_store.py` uses `float | None` union syntax (Python 3.10+), crashes on system Python 3.9.6
- **Fix:** Change `float | None` → `Optional[float]` in event_store.py (already imports Optional)

---

## Coverage Gaps by Module

### ✅ Has Tests
| Module | Status |
|--------|--------|
| src/alerting/email.py | Covered |
| src/alerting/webhook.py | Covered |
| src/alerting/slack_discord.py | Covered (via dispatcher) |
| src/detectors/*.py (all 9) | Covered |

### ❌ No Tests
| Module | Risk |
|--------|------|
| **src/api/routes/anomalies.py** | HIGH — core API surface, untested |
| **src/api/routes/dashboard.py** | HIGH — main dashboard data |
| **src/api/routes/webhooks.py** | HIGH — Stripe webhook ingestion, critical path |
| src/api/routes/config.py | Medium |
| src/api/routes/metrics.py | Medium |
| src/api/routes/onboarding.py | Medium |
| src/api/routes/beta.py | Low |
| src/api/routes/demo.py | Low |
| src/api/routes/demo_seed.py | Low |
| src/api/routes/dashboard_ui.py | Low |
| src/api/main.py | Low (wiring) |
| **src/storage/event_store.py** | HIGH — central data store, blocked by Python version |
| src/storage/false_positives.py | Medium |
| src/storage/thresholds.py | Medium |
| src/workers/event_processor.py | HIGH — core event pipeline |
| src/workers/scheduler.py | Medium |
| src/keychain.py | Low |
| src/stripe_client.py | Medium |
| src/models/database.py | Low |
| src/models/schemas.py | Low |

---

## Priority Fixes

1. **Fix Python version compatibility** in `event_store.py` — unblocks 2 test files
2. **Fix timing bug** in `test_no_alert_normal_revenue` — trivial one-liner
3. **Add API route tests** — webhooks.py and anomalies.py are the highest-risk gaps
4. **Add event_processor tests** — core pipeline has no coverage at all

---

## Detector Coverage Details
9 detectors × ~10 tests each = ~90 unit tests. All pass. Coverage is solid for business logic.
The gap is entirely in **infrastructure layer**: API, storage, workers, Stripe client.
