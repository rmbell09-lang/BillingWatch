# BillingWatch — LuLu Firewall Setup for Deploy

> For Ray. Do these steps before running `DEPLOY_NOW.sh`.

---

## Step 1: Allow `api.cloudflare.com` in LuLu

BillingWatch uses `cloudflared` to create a Cloudflare Tunnel. LuLu blocks outbound by default — you need to add a rule for Cloudflare's API and tunnel endpoints.

**In LuLu:**
1. Open LuLu from menu bar
2. Go to **Rules**
3. Click **+** to add a new rule
4. Set:
   - **Process:** `/opt/homebrew/bin/cloudflared` (or wherever Homebrew installed it — run `which cloudflared` to confirm)
   - **Direction:** Outbound
   - **Action:** Allow
   - **Endpoint:** Any (or add these specific domains):
     - `api.cloudflare.com`
     - `*.cloudflareaccess.com`
     - `*.argotunnel.com`
     - `*.cftunnel.com`

> **Why these domains?** `cloudflared` contacts `api.cloudflare.com` to register/authenticate the tunnel, then uses Argotunnel infrastructure (`*.argotunnel.com`, `*.cftunnel.com`) to route traffic.

Alternatively: when you first run `cloudflared tunnel login`, LuLu will prompt you with a connection alert — just click **Allow** and check "Remember this decision."

---

## Step 2: Install cloudflared (if not already installed)

```bash
brew install cloudflare/cloudflare/cloudflared
cloudflared --version  # confirm install
```

LuLu may prompt when Homebrew fetches the binary — allow it.

---

## Step 3: Test outbound is working

```bash
curl -s https://api.cloudflare.com/client/v4/user/tokens/verify \
  -H "Authorization: Bearer YOUR_CF_API_TOKEN" | python3 -m json.tool
```

If LuLu is blocking it, you'll get a connection timeout. If allowed, you'll get a JSON response (even an auth error is fine — it means the connection got through).

---

## Step 4: Run the deploy

Once LuLu allows cloudflared outbound:

```bash
cd ~/Projects/BillingWatch
CF_API_TOKEN=your_token_here CF_ACCOUNT_ID=your_account_id_here python3 deploy_cf.py
```

Or use the quick test tunnel (no CF creds needed):
```bash
# Terminal 1 — start BillingWatch backend
python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8001

# Terminal 2 — expose via cloudflared (temporary URL)
cloudflared tunnel --url http://localhost:8001
```

Cloudflare will print a URL like `https://abc123.trycloudflare.com` — use that as your Stripe webhook endpoint for testing.

---

## What You Need to Provide (Lucky needs these to finish the deploy)

| Item | Where to get it |
|------|----------------|
| `CF_API_TOKEN` | dash.cloudflare.com → My Profile → API Tokens → Create Token (Templates: Edit Cloudflare Pages, or custom with Pages:Edit + Account:Read) |
| `CF_ACCOUNT_ID` | Visible on right sidebar of dash.cloudflare.com home |
| Stripe webhook secret | After you add the BillingWatch URL as a webhook in Stripe Dashboard → Webhooks |

---

## Notes

- **LuLu prompt timing:** The first `cloudflared` outbound connection triggers a LuLu alert. Be ready to click Allow when you run any cloudflared command.
- **Persistent vs temp tunnel:** The deploy script uses a persistent tunnel (survives restarts). The quick test above uses a temp URL that changes every run.
- **Port 8001:** BillingWatch FastAPI backend runs on localhost:8001. The tunnel forwards external HTTPS → localhost:8001.
- **Landing page:** Runs separately on localhost:8080. Only the webhook endpoint (8001) needs to be publicly exposed for Stripe.
