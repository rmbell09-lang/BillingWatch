#!/usr/bin/env python3
"""
BillingWatch CLI — launch the self-hosted Stripe billing anomaly detector.
"""
import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path


REPO_URL = "https://github.com/rmbell09-lang/BillingWatch"
DEFAULT_DIR = Path.home() / "BillingWatch"
DEFAULT_PORT = 8000


def main():
    print("🔍 BillingWatch — Self-Hosted Stripe Billing Anomaly Detector")
    print("=" * 60)

    bw_dir = Path(os.environ.get("BILLINGWATCH_DIR", str(DEFAULT_DIR)))
    port = int(os.environ.get("BILLINGWATCH_PORT", str(DEFAULT_PORT)))

    # Clone if not present
    if not bw_dir.exists():
        print(f"📥 Cloning BillingWatch to {bw_dir} ...")
        result = subprocess.run(
            ["git", "clone", REPO_URL, str(bw_dir)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"❌ Clone failed: {result.stderr}")
            print(f"   Manually clone: git clone {REPO_URL}")
            sys.exit(1)
        print("✅ Cloned successfully.")
    else:
        print(f"📂 Found BillingWatch at {bw_dir}")

    # Check for .env
    env_file = bw_dir / ".env"
    env_example = bw_dir / ".env.example"
    if not env_file.exists():
        if env_example.exists():
            print("⚠️  No .env found. Copy .env.example and add your Stripe webhook secret:")
            print(f"   cp {bw_dir}/.env.example {bw_dir}/.env")
        else:
            print("⚠️  No .env found. Create one with STRIPE_WEBHOOK_SECRET=whsec_...")
        print()

    # Prefer Docker if available
    docker_compose = bw_dir / "docker-compose.yml"
    docker_available = subprocess.run(
        ["docker", "--version"], capture_output=True
    ).returncode == 0

    if docker_available and docker_compose.exists():
        print(f"🐳 Starting with Docker on port {port} ...")
        print(f"   Dashboard: http://localhost:{port}")
        time.sleep(1)
        webbrowser.open(f"http://localhost:{port}")
        os.chdir(str(bw_dir))
        os.execvp("docker", ["docker", "compose", "up"])
    else:
        # Fallback: install deps + run uvicorn directly
        req_file = bw_dir / "requirements.txt"
        if req_file.exists():
            print("📦 Installing dependencies ...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(req_file), "-q"],
                check=True,
            )

        print(f"🚀 Starting BillingWatch on http://localhost:{port} ...")
        time.sleep(1)
        webbrowser.open(f"http://localhost:{port}")

        os.chdir(str(bw_dir))
        sys.path.insert(0, str(bw_dir))
        os.execv(
            sys.executable,
            [
                sys.executable, "-m", "uvicorn",
                "src.api.main:app",
                "--host", "0.0.0.0",
                "--port", str(port),
            ],
        )


if __name__ == "__main__":
    main()
