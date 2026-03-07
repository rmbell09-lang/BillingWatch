# Security Scan — API Key Audit
Date: March 6, 2026 — 5:41 AM ET
Scope: All projects in ~/Projects/ (BillingWatch, InkForge, TradeSight, Mission Control)
Performed by: Lucky (automated heartbeat scan)

---

## Scan Method

Grepped all .env, .py, .json, .yaml, .yml, .sh, .conf, .cfg, .ini files for patterns:
- sk_live_ (Stripe live secret)
- sk_test_ (Stripe test secret, real 24+ char values)
- rk_live_ (Stripe restricted key)
- pk_live_ (Stripe publishable live)
- whsec_ (Stripe webhook secret, real 24+ char values)
- sk-ant- (Anthropic API keys)
- sk-proj- (OpenAI project keys)
- OPENAI_API_KEY with real values
- ANTHROPIC_API_KEY with real values

Excluded: .venv/, .git/, __pycache__, .pytest_cache

---

## Results by Project

### BillingWatch — CLEAN
- .env — contains STRIPE_SECRET_KEY=sk_test_PLACEHOLDER (placeholder, not real)
- .env.dev — only contains STRIPE_WEBHOOK_SECRET=dev (dev placeholder)
- .env.example — sk_live_... (template placeholder, not a real key)
- src/keychain.py — Keychain-first architecture confirmed. Uses macOS security CLI
  to pull secrets, falls back to env vars only if Keychain lookup fails.
- src/api/routes/webhooks.py — reads from env var only (expected for dev/Docker)

### InkForge — CLEAN
- No .env files found with real keys
- src/config.py — no hardcoded secrets
- config/intelligence.yaml — provider names only, no keys

### TradeSight — CLEAN
- .env files — no real keys found
- src/config.py — uses get_openai_api_key() (Keychain helper function)
- src/utils/keychain.py — Keychain integration confirmed

### Mission Control — CLEAN
- No .env files with real keys found

---

## Keychain Architecture Verification

BillingWatch (src/keychain.py):
  Priority 1: macOS Keychain via security find-generic-password CLI
  Priority 2: Env var fallback (dev only, never in production)
  Service name: BillingWatch
  Keys managed: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, DB_PASSWORD, SMTP_PASS

TradeSight (src/utils/keychain.py):
  Same pattern — Keychain first, env fallback
  Keys managed: OPENAI_API_KEY, ALPACA_API_KEY, ALPACA_SECRET_KEY

---

## Findings Summary

| Project       | Real Keys Found | Keychain Used | Status |
|---------------|----------------|---------------|--------|
| BillingWatch  | None           | Yes           | CLEAN  |
| InkForge      | None           | Partial (env) | CLEAN  |
| TradeSight    | None           | Yes           | CLEAN  |
| Mission Control | None         | N/A           | CLEAN  |

---

## Action Items

NONE REQUIRED. All scanned projects are clean of plaintext API keys.

Recommendations (non-urgent):
1. InkForge: Add a Keychain helper for OPENAI_API_KEY for consistency with other projects.
2. BillingWatch: Confirm production .env never gets committed with real whsec_ values.
3. All projects: Add .env.local to .gitignore if not already present (spot-checked — BillingWatch has it).

---

## VERDICT: ALL CLEAR — No plaintext API keys found in any project config files.
