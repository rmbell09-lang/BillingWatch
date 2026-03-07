#!/usr/bin/env python3
"""Deploy BillingWatch landing page to Cloudflare Pages.
Usage: CF_API_TOKEN=xxx CF_ACCOUNT_ID=yyy python3 deploy_cf.py
"""
import os, sys, zipfile, io, json, urllib.request, pathlib

API_TOKEN = os.environ.get('CF_API_TOKEN')
ACCOUNT_ID = os.environ.get('CF_ACCOUNT_ID')
PROJECT_NAME = 'billingwatch'
LANDING_DIR = pathlib.Path(__file__).parent

if not API_TOKEN or not ACCOUNT_ID:
    print('ERROR: Set CF_API_TOKEN and CF_ACCOUNT_ID env vars first.')
    print('See DEPLOY_INSTRUCTIONS.md for details.')
    sys.exit(1)

HEADERS = {'Authorization': f'Bearer {API_TOKEN}'}

def cf_request(method, path, data=None, headers=None):
    url = f'https://api.cloudflare.com/client/v4{path}'
    h = {**HEADERS, **(headers or {})}
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())

# 1. Ensure project exists
print(f'[1/3] Checking Cloudflare Pages project "{PROJECT_NAME}"...')
res = cf_request('GET', f'/accounts/{ACCOUNT_ID}/pages/projects/{PROJECT_NAME}')
if not res.get('success'):
    print(f'      Project not found, creating...')
    res = cf_request('POST', f'/accounts/{ACCOUNT_ID}/pages/projects',
        data=json.dumps({'name': PROJECT_NAME, 'production_branch': 'master'}).encode(),
        headers={'Content-Type': 'application/json'})
    if not res.get('success'):
        print('ERROR creating project:', res)
        sys.exit(1)
    print(f'      Created: https://{PROJECT_NAME}.pages.dev')
else:
    print(f'      Found: https://{PROJECT_NAME}.pages.dev')

# 2. Bundle landing dir into zip
print('[2/3] Bundling landing files...')
buf = io.BytesIO()
with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
    for f in LANDING_DIR.rglob('*'):
        if f.is_file() and f.suffix in ('.html', '.css', '.js', '.png', '.ico', '.svg', '.txt'):
            zf.write(f, f.relative_to(LANDING_DIR))
buf.seek(0)
print(f'      Bundle size: {len(buf.getvalue()):,} bytes')

# 3. Direct upload deployment
print('[3/3] Deploying to Cloudflare Pages...')
import urllib.parse
boundary = 'billingwatch_deploy_boundary'
body = (
    f'--{boundary}\r\nContent-Disposition: form-data; name="manifest"\r\n\r\n{{"/_worker.js":""}}\r\n'
    f'--{boundary}\r\nContent-Disposition: form-data; name="files"; filename="bundle.zip"\r\nContent-Type: application/zip\r\n\r\n'
).encode() + buf.getvalue() + f'\r\n--{boundary}--\r\n'.encode()

res = cf_request('POST',
    f'/accounts/{ACCOUNT_ID}/pages/projects/{PROJECT_NAME}/deployments',
    data=buf.getvalue(),
    headers={'Content-Type': 'application/zip'})

if res.get('success'):
    d = res.get('result', {})
    url = d.get('url', f'https://{PROJECT_NAME}.pages.dev')
    print(f'SUCCESS! Deployed to: {url}')
else:
    print('Deployment response:', json.dumps(res, indent=2))
    print('\nNOTE: For direct upload, you may need to use wrangler:')
    print(f'  export PATH=/opt/homebrew/bin:~/.npm-global/bin:/usr/bin:/usr/local/bin:/home/openclaw/.local/bin:/bin:/home/openclaw/.npm-global/bin:/home/openclaw/bin:/home/openclaw/.volta/bin:/home/openclaw/.asdf/shims:/home/openclaw/.bun/bin:/home/openclaw/.nvm/current/bin:/home/openclaw/.fnm/current/bin:/home/openclaw/.local/share/pnpm')
    print(f'  CLOUDFLARE_API_TOKEN={API_TOKEN} wrangler pages deploy {LANDING_DIR} --project-name={PROJECT_NAME}')
