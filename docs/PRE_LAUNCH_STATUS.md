# BillingWatch — Pre-Show HN Status Report
*Generated: Sunday March 8, 2026 — 9:11 PM ET*
*Show HN: Tuesday March 10, 9:00 AM ET (37 hours away)*

---

## Current Live URL
**https://neck-dna-fotos-specialties.trycloudflare.com**
- Status: ✅ LIVE (HTTP 200, landing page loading)
- Type: Cloudflare Quick Tunnel (temporary)
- Running via: OpenClaw VPS sessions grand-trail (serve.py port 8090) + warm-daisy (cloudflared tunnel)
- Risk: URL changes if VPS reboots or OpenClaw sessions are killed
- Signup storage: SQLite on VPS (/tmp/billingwatch-landing/signups.db) — LOST on reboot

## Services Running
| Service | Location | Port | Status |
|---------|----------|------|--------|
| Landing page (VPS) | VPS | 8090 | ✅ Running (OpenClaw session) |
| Landing page (Mac) | Mac Mini | 8080 | ✅ Running (launchd) |
| FastAPI backend | Mac Mini | 8001 | ✅ Running (manual) |
| Cloudflare tunnel | VPS | — | ✅ Active |
| BillingWatch launchd | Mac Mini | — | ❌ Not loaded (needs Stripe keys) |

---

## What Ray Needs to Do (Ordered by Urgency)

### 🔴 CRITICAL — Needed before Show HN
**Option A: Deploy to Cloudflare Pages (Permanent URL)**
1. Get CLOUDFLARE_API_TOKEN from dash.cloudflare.com → My Profile → API Tokens
2. Get CF_ACCOUNT_ID from dash.cloudflare.com right sidebar
3. Add LuLu rule: allow outbound to api.cloudflare.com
4. Run: 
5. Or simpler: 

**Option B: Keep using temp URL for Show HN (higher risk)**
- The temp URL WORKS right now — just don't restart the VPS before Tuesday
- Replace [REPLACE WITH URL] in BETA_OUTREACH.md with: neck-dna-fotos-specialties.trycloudflare.com
- Risk: If URL dies during HN traffic, launch fails

### 🟡 IMPORTANT — Within 1 week
**Stripe Live Keys (Task #340)**
- 
- 
- Then: 

---

## Show HN Post Status

Template ready in: ~/Projects/BillingWatch/docs/BETA_OUTREACH.md

**Only thing missing: Replace [REPLACE WITH URL] with the live URL**

Title (ready):
> Show HN: BillingWatch – self-hosted Stripe anomaly detector (webhook lag, silent lapses, card testing)

---

## Week Launch Calendar
| Day | Platform | Time | Template |
|-----|----------|------|----------|
| Tuesday Mar 10 | Hacker News (Show HN) | 9:00 AM ET | BETA_OUTREACH.md #1 |
| Wednesday Mar 11 | Indie Hackers | 10:00 AM ET | BETA_OUTREACH.md #2 |
| Thursday Mar 12 | r/SaaS Reddit | 10:00 AM ET | BETA_OUTREACH.md #3 |

---

## Bottom Line
Everything is ready to post. The ONLY blocker is getting a permanent URL.
The temp URL works but is fragile. Recommend Option A (CF Pages) before sleeping Sunday night.
If that's not happening, use the temp URL and hope VPS stays up.
