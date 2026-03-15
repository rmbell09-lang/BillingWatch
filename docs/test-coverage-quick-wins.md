# BillingWatch — Fastest Test Coverage Wins
Generated: 2026-03-12 00:10 ET

## Ranked by Effort vs. Impact

---

### 🥇 WIN #1 — Fix Python 3.9 compat (event_store.py)
**Effort:** 1 line | **Impact:** Unblocks 2 test files immediately

- File: `src/storage/event_store.py`, line 224
- Change: `float | None` → `Optional[float]` (Optional already imported)
- Effect: `test_e2e_charge_failure.py` and `test_event_store_integration.py` go from
  "cannot import" to runnable — instant coverage boost with zero new test writing

---

### 🥈 WIN #2 — Fix timing bug in test_no_alert_normal_revenue
**Effort:** 1 line | **Impact:** 1 failing test → passing (100% pass rate)

- File: `tests/test_revenue_drop.py` (timing-sensitive test)
- Change: `time.time() - 3600` → `time.time()`
- Effect: Test was only failing at UTC midnight boundary. Trivial fix.

---

### 🥉 WIN #3 — Add anomalies.py route tests
**Effort:** ~2-3 hrs | **Impact:** HIGH risk gap closed, core API tested

- File: `src/api/routes/anomalies.py` (126 lines)
- Simple CRUD-like routes: list alerts, mark false positive, query by type/window
- Pattern: mock `EventStore` + `FalsePositiveStore`, assert JSON shape
- Likely 10-15 tests, straightforward FastAPI TestClient setup
- **Why first of the API routes:** imports anomalies.py already mock-friendly;
  no Stripe signature verification complexity

---

### WIN #4 — Add webhooks.py route tests
**Effort:** ~4-5 hrs | **Impact:** CRITICAL path (Stripe ingestion)

- File: `src/api/routes/webhooks.py` (208 lines)
- More complex: need to mock `stripe.Webhook.construct_event()` + signature header
- Suggested test cases:
  - Valid event → routed to correct detector
  - Invalid signature → 400
  - Unknown event type → silently ignored
  - Each of the 7 detector routes triggered correctly
- Best done after Win #3 (shares test infrastructure)

---

### WIN #5 — Add event_processor.py tests
**Effort:** ~3-4 hrs (after Win #1) | **Impact:** HIGH — core event pipeline

- File: `src/workers/event_processor.py` (155 lines)
- Blocked on Win #1 (Python compat) — fix that first or tests cannot import
- Pattern: mock EventStore, inject test events, assert processor state changes

---

## Recommended Sequence
1. Fix event_store.py compat (5 min) → run tests → 2 more files now collected
2. Fix timing bug in test (5 min) → 91→92 passing
3. Draft anomalies route tests (2-3 hrs)
4. Draft webhooks route tests (4-5 hrs)
5. Draft event_processor tests (3-4 hrs)

**Total fastest path to meaningful coverage:** ~10 hrs of focused work
**Quick wins 1+2 alone:** ~10 minutes, zero risk
