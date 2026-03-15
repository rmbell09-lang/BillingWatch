# BillingWatch — Webhook Handler Security Audit
**Date:** 2026-03-10  
**Auditor:** Lucky (automated review)  
**Scope:** `webhook_handler.py` + `src/api/routes/webhooks.py`  
**Focus:** Stripe signature verification, HMAC implementation, timing-safe comparisons

---

## Summary

**Overall risk: LOW.** The production-mode HMAC path is correctly implemented. The main risk is misconfiguration (missing env var silently enables dev bypass). No critical vulnerabilities found.

---

## Files Reviewed

| File | Role |
|------|------|
| `webhook_handler.py` | Standalone utility — validates signatures via custom HMAC |
| `src/api/routes/webhooks.py` | FastAPI route — uses official Stripe SDK construct_event() |

---

## HMAC Implementation (webhook_handler.py)

### PASS — Correct algorithm

Uses HMAC-SHA256, which matches Stripe's spec. Key is UTF-8 encoded. Digest returned as hex string via `hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()`.

### PASS — Timing-safe comparison

Uses `hmac.compare_digest()` for constant-time string comparison via:
`if not any(hmac.compare_digest(expected, sig) for sig in signatures)`

Correctly loops over all v1= signatures (Stripe can include multiple during key rotation).

Note: `any()` short-circuits on first match — this is fine. Each individual comparison is timing-safe. Short-circuit on success does not leak information.

### PASS — Signed payload format

`signed_payload = f"{timestamp}.".encode() + payload`

Matches Stripe spec exactly: `{timestamp}.{raw_payload}`. Payload kept as raw bytes (not re-serialized), preventing JSON normalization attacks.

### PASS — Replay attack protection

`if abs(now - timestamp) > tolerance:  # default 300s`

5-minute tolerance matches Stripe's recommended window. Timestamp extracted from the `t=` field of the header, not from the payload.

### PASS — Malformed header rejection

Rejects headers missing `t=` or `v1=` fields before attempting HMAC.

---

## FastAPI Route (src/api/routes/webhooks.py)

### PASS — Uses official Stripe SDK

Delegates to `stripe.Webhook.construct_event()` in production mode. Stripe's SDK internally uses `hmac.compare_digest()` and handles all edge cases. This is the correct approach.

### PASS — Missing header check

Rejects requests with no `Stripe-Signature` header before any processing.

---

## Issues Found

### MEDIUM — Dev bypass triggers on missing env var

**Location:** Both files  
**Risk:** If `STRIPE_WEBHOOK_SECRET` is not set in production, all webhooks pass without signature verification.

In webhook_handler.py: `if not secret or secret == "dev": return json.loads(payload)`
In webhooks.py route: `webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")` then falls through to dev mode if empty.

**Recommendation:** Add a startup check that raises if `STRIPE_WEBHOOK_SECRET` is unset in non-dev environments:

```python
if os.getenv("APP_ENV", "dev") != "dev":
    assert os.getenv("STRIPE_WEBHOOK_SECRET"), "STRIPE_WEBHOOK_SECRET must be set in production"
```

---

### LOW — SignatureVerificationError details leaked in 400 response

**Location:** `src/api/routes/webhooks.py`  
**Risk:** Error message from Stripe SDK forwarded to caller, hints at internal state.

**Current:** `detail=f"Webhook signature verification failed: {exc}"`  
**Recommended:** `detail="Webhook signature verification failed"` — log exc internally only.

---

### LOW — Dead code: _get_webhook_secret() never called

**Location:** `src/api/routes/webhooks.py`  
**Risk:** None directly, but the function exists as a guard but the route reads os.getenv() directly, bypassing the RuntimeError guard entirely.

**Recommendation:** Either call `_get_webhook_secret()` in the route handler or remove it.

---

### LOW — No rate limiting on /webhooks/stripe

**Location:** `src/api/routes/webhooks.py`  
**Risk:** Publicly accessible endpoint. Attacker could flood with invalid requests causing CPU/DB load.

**Recommendation:** Add IP-based rate limiting (e.g., slowapi) or restrict to Stripe's published IP ranges.

---

### INFO — In-memory alert log (max 500 entries)

**Risk:** Alerts lost on restart. Under high event volume, old alerts silently dropped.

**Recommendation:** Already tracked in MULTI_TENANT_SPEC.md. Persist alerts to SQLite alongside events.

---

### INFO — Duplicate signature logic

`webhook_handler.py` implements custom HMAC; the route uses Stripe SDK. Risk of divergence if the standalone file ever gets used in a non-test code path.

**Recommendation:** Document clearly that webhook_handler.py is dev/test only. The route's SDK usage is the production path.

---

## Verdict

| Check | Status |
|-------|--------|
| HMAC algorithm (SHA-256) | PASS |
| Timing-safe comparison | PASS |
| Replay attack protection | PASS |
| Signed payload format | PASS |
| Missing header rejection | PASS |
| Dev bypass on missing secret | FIX BEFORE PROD |
| Error message leakage | Low priority |
| Dead code _get_webhook_secret | Cleanup |
| Rate limiting | Nice-to-have |
| Alert persistence | Known gap |

**Action required before production:** Add startup assertion that `STRIPE_WEBHOOK_SECRET` is set when `APP_ENV != dev`. Everything else is low-priority polish.
