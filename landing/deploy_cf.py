#!/usr/bin/env python3
"""Deploy to Cloudflare Pages. Reads CF creds from Keychain."""
import subprocess, os, json, urllib.request, urllib.parse, hashlib, mimetypes, io

def get_keychain(service, account):
    try:
        r = subprocess.run(["security","find-generic-password","-s",service,"-a",account,"-w"],
                          capture_output=True, text=True, check=True)
        return r.stdout.strip()
    except:
        return None

def cf_api(method, path, data=None, token=None, raw_body=None, content_type="application/json"):
    url = "https://api.cloudflare.com/client/v4" + path
    headers = {"Authorization": "Bearer " + token}
    body = None
    if raw_body:
        headers["Content-Type"] = content_type
        body = raw_body
    elif data:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        err = e.read().decode()[:500]
        print("CF API error " + str(e.code) + ": " + err)
        return None

def collect_files(base_dir):
    files = {}
    for root, dirs, filenames in os.walk(base_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fn in filenames:
            if fn.startswith(".") or fn.endswith(".py") or fn.endswith(".sh") or fn.endswith(".json"):
                continue
            full = os.path.join(root, fn)
            rel = "/" + os.path.relpath(full, base_dir)
            with open(full, "rb") as f:
                content = f.read()
            mime = mimetypes.guess_type(fn)[0] or "application/octet-stream"
            files[rel] = {"content": content, "mime": mime}
    return files

def deploy(project_name, base_dir, token, account):
    files = collect_files(base_dir)
    print("Deploying " + str(len(files)) + " files to " + project_name + ".pages.dev...")
    for path in sorted(files.keys()):
        print("  " + path)

    # Create project (ignore error if exists)
    cf_api("POST", "/accounts/" + account + "/pages/projects",
           {"name": project_name, "production_branch": "main"}, token)

    # For CF Pages Direct Upload, we need to use the v2 deploy endpoint
    # First, get upload URL
    boundary = "----FormBoundary7MA4YWxk"
    body_parts = []
    for path, info in files.items():
        body_parts.append(("--" + boundary).encode())
        header = 'Content-Disposition: form-data; name="' + path + '"; filename="' + path + '"'
        body_parts.append(header.encode())
        body_parts.append(("Content-Type: " + info["mime"]).encode())
        body_parts.append(b"")
        body_parts.append(info["content"])
    body_parts.append(("--" + boundary + "--").encode())
    multipart_body = b"\r\n".join(body_parts)

    upload_url = "/accounts/" + account + "/pages/projects/" + project_name + "/deployments"
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "multipart/form-data; boundary=" + boundary,
    }
    url = "https://api.cloudflare.com/client/v4" + upload_url
    req = urllib.request.Request(url, data=multipart_body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            result = json.loads(r.read())
            if result.get("success"):
                print("")
                print("Deployed! URL: https://" + project_name + ".pages.dev")
                return True
            else:
                print("Deploy response: " + json.dumps(result.get("errors", [])))
                return False
    except urllib.error.HTTPError as e:
        err = e.read().decode()[:500]
        print("Deploy error " + str(e.code) + ": " + err)
        return False

def main():
    token = get_keychain("BillingWatch-CF-Token", "luckyai")
    account = get_keychain("BillingWatch-CF-AccountID", "luckyai")
    if not token or not account:
        print("ERROR: CF credentials not in Keychain")
        return

    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_name = os.path.basename(base_dir)
    if project_name == "storefront":
        project_name = "qc-storefront"
    elif project_name == "landing":
        project_name = "billingwatch"

    deploy(project_name, base_dir, token, account)

if __name__ == "__main__":
    main()
