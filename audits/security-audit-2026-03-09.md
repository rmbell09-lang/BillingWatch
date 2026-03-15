# BillingWatch Security Audit — March 9, 2026

## Tool: pip-audit

## Vulnerabilities Found

### starlette 0.38.6 (transitive via fastapi==0.115.0)

| ID | Severity | Fix Version |
|----|----------|-------------|
| GHSA-f96h-pmfr-66vw | High | 0.40.0 |
| GHSA-2c2j-9gv5-cj73 | High | 0.47.2 |

**CVE Details:**
- GHSA-f96h-pmfr-66vw: DoS via malformed multipart form data
- GHSA-2c2j-9gv5-cj73: Header injection vulnerability

## Fixes Applied

Updated `requirements.txt`:
- `fastapi==0.115.0` → `fastapi==0.128.8` (latest stable)
- `uvicorn[standard]==0.30.0` → `uvicorn[standard]==0.32.1`
- Added explicit `starlette>=0.47.2` pin (both CVEs fixed)
- Updated stripe, sqlalchemy, redis, pydantic, httpx, pytest to latest stable versions

## Status
All known vulnerabilities addressed in requirements.txt. BillingWatch not yet deployed — no live exposure. Apply when deploying with `pip install -r requirements.txt`.
