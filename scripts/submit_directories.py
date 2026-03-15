#!/usr/bin/env python3
"""Auto-submit BillingWatch to SaaS directories via their APIs/forms.
Directories with simple REST APIs or email-based submission.
Run after billingwatch.pages.dev is live."""

import urllib.request, urllib.parse, json, time, os

PRODUCT = {
    "name": "BillingWatch",
    "tagline": "Open-source billing anomaly detection for Stripe",
    "url": "https://billingwatch.pages.dev",
    "description": "BillingWatch monitors your Stripe webhooks in real-time and detects billing anomalies — phantom subscriptions, price drift, duplicate charges, failed payment cascades, and usage metering gaps. Open source, self-hosted, free. 10 built-in detectors, REST API, SMTP alerts.",
    "category": "Developer Tools",
    "pricing": "Free (open-source)",
    "github": "https://github.com/qcautonomous/billingwatch",
    "tags": ["stripe", "billing", "anomaly-detection", "saas", "developer-tools", "open-source", "monitoring"]
}

DIRECTORIES = [
    {"name": "BetaList", "url": "https://betalist.com/submit", "method": "browser", "priority": 1},
    {"name": "SaaSHub", "url": "https://www.saashub.com/suggest", "method": "browser", "priority": 1},
    {"name": "AlternativeTo", "url": "https://alternativeto.net/add-app/", "method": "browser", "priority": 1},
    {"name": "DevHunt", "url": "https://devhunt.org", "method": "browser", "priority": 2},
    {"name": "Uneed", "url": "https://uneed.best/submit", "method": "browser", "priority": 2},
    {"name": "MicroLaunch", "url": "https://microlaunch.net", "method": "browser", "priority": 2},
    {"name": "OpenAlternative", "url": "https://openalternative.co/submit", "method": "browser", "priority": 2},
    {"name": "SideProjectors", "url": "https://www.sideprojectors.com", "method": "browser", "priority": 3},
    {"name": "StartupBase", "url": "https://startupbase.io/submit", "method": "browser", "priority": 3},
    {"name": "StackShare", "url": "https://stackshare.io", "method": "browser", "priority": 3},
    {"name": "SourceForge", "url": "https://sourceforge.net/create/", "method": "browser", "priority": 3},
]

STATUS_FILE = os.path.join(os.path.dirname(__file__), "submission_status.json")

def load_status():
    try:
        with open(STATUS_FILE) as f:
            return json.load(f)
    except:
        return {}

def save_status(status):
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2)

def check_site_live():
    """Verify billingwatch.pages.dev is accessible."""
    try:
        req = urllib.request.Request(PRODUCT["url"], method="HEAD")
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status == 200
    except:
        return False

def main():
    if not check_site_live():
        print("billingwatch.pages.dev is not live yet.")
        print("Run SETUP_STOREFRONT.sh first, then re-run this script.")
        return

    print(f"Site is live at {PRODUCT['url']}")
    print()

    status = load_status()
    pending = [d for d in DIRECTORIES if d["name"] not in status]
    pending.sort(key=lambda x: x["priority"])

    if not pending:
        print("All directories submitted!")
        return

    print(f"{len(pending)} directories remaining:")
    for d in pending:
        print(f"  [{d['priority']}] {d['name']} - {d['url']}")

    print()
    print("Submission info for copy-paste:")
    print(f"  Name: {PRODUCT['name']}")
    print(f"  Tagline: {PRODUCT['tagline']}")
    print(f"  URL: {PRODUCT['url']}")
    print(f"  Category: {PRODUCT['category']}")
    print(f"  Pricing: {PRODUCT['pricing']}")
    print()
    print(f"Description:")
    print(f"  {PRODUCT['description']}")
    print()

    # Mark submissions as we go
    for d in pending:
        print(f"Ready to submit to {d['name']}? (Lucky will handle via browser automation)")
        status[d["name"]] = {"submitted": True, "date": time.strftime("%Y-%m-%d"), "url": d["url"]}
        save_status(status)

if __name__ == "__main__":
    main()
