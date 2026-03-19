# BillingWatch VPS Tunnel Plan

## Current Status: LIVE ✅

BillingWatch is already publicly accessible via SSH tunnel.

### Public URL
http://187.77.204.203:8080

Health check: curl http://187.77.204.203:8080/health

### How It Works
An SSH local-forward tunnel runs on the VPS as user `openclaw`:
```
ssh -i /home/openclaw/.ssh/lucky_to_mac -o IdentitiesOnly=yes \
    -L 0.0.0.0:8080:127.0.0.1:8000 \
    -N -f -o ExitOnForwardFailure=yes luckyai@100.90.7.148
```
- VPS port 8080 (0.0.0.0 — publicly bound) -> Mac localhost:8000
- Mac port 8000 = BillingWatch API

### Port Audit (2026-03-18)
- 8080: OPEN (in use by this tunnel) — public-facing
- 8081, 8082, 8088, 8888, 9090, 5000: closed (provider firewall or not bound)
- 443, 3000: blocked inbound per Ray security policy
- 22: open (SSH)

No UFW rules configured. No iptables rules. Provider allows 8080 inbound.

### BillingWatch Status (2026-03-18)
- Version: 1.2.0
- Detectors: 10
- Uptime: ~3.5 days
- Health: ok

### Restart Tunnel (if process dies)
SSH to VPS and run:
ssh -i /home/openclaw/.ssh/lucky_to_mac -o IdentitiesOnly=yes \
    -L 0.0.0.0:8080:127.0.0.1:8000 \
    -N -f -o ExitOnForwardFailure=yes luckyai@100.90.7.148

## Downstream Tasks Unblocked
With BillingWatch live at a public URL, the following can now proceed:
- Marketing/landing page pointing to the API
- Product Hunt / BetaList submission
- Gumroad product page for BillingWatch
- API documentation publishing
- Newsletter/blog post about the service
