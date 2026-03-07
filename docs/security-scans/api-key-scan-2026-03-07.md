# Weekly API Key Scan — 2026-03-07

**Scanned by:** Lucky (automated heartbeat)
**Time:** 4:11 PM ET Saturday, March 7, 2026
**Scope:** BillingWatch, InkForge, TradeSight, Mission Control

---

## Results Summary

| Project | .gitignore | .env Tracked? | Hardcoded Secrets? | Keychain Used? | Status |
|---|---|---|---|---|---|
| BillingWatch | ✅ Present | ❌ No (only .env.example) | ❌ None | ✅ Yes | CLEAN |
| InkForge | ⚠️ MISSING | N/A | ❌ None found | ➕ Env vars | NEEDS FIX |
| TradeSight | ✅ Present | ❌ No | ❌ None | ✅ Yes | CLEAN |
| Mission Control | ⚠️ MISSING | N/A | ❌ None found | ✅ Yes | NEEDS FIX |

---

## Findings

### 🟢 CLEAN — BillingWatch
- `.env` file exists but contains only placeholder values (`sk_test_PLACEHOLDER`, `dev`)
- `.gitignore` properly excludes: `.env`, `.env.dev`, `.env.*`, `.env.local`
- Only `.env.example` tracked in git
- Stripe secrets loaded via `src/keychain.py` using macOS Keychain
- **No action needed**

### 🟡 WARNING — InkForge
- **NO `.gitignore` file present** — if a `.env` file were created, it would be committed
- No `.env` files currently exist in the project
- OpenAI key read via `os.environ.get("OPENAI_API_KEY", "")` (env var, not hardcoded)
- No hardcoded tokens found in source files
- **Action: Create `.gitignore`** — DONE (see below)

### 🟢 CLEAN — TradeSight
- `.gitignore` properly excludes `.env`, `.env.*`, `*.key`, `secrets.json`
- Uses `src/utils/keychain.py` for all secrets (OpenAI, Alpaca, Polygon, Yahoo)
- No hardcoded tokens in tracked files
- **No action needed**

### 🟡 WARNING — Mission Control
- **NO `.gitignore` file present** — if a `.env` file were created, it would be committed
- No `.env` files currently exist in the project
- API keys loaded via `keychain.js` using macOS Keychain
- No hardcoded tokens found in tracked files
- **Action: Create `.gitignore`** — DONE (see below)

---

## Remediation Applied This Session

### InkForge .gitignore — CREATED
### Mission Control .gitignore — CREATED

---

## Recommendations
1. InkForge: Consider migrating OpenAI key from env var to macOS Keychain for consistency
2. All projects: Run this scan weekly (already scheduled as auto-generated task)

---

**DECISION: ACT** — Two .gitignore files created. Keychain usage is solid across all projects. No live credentials exposed. Low risk overall.
