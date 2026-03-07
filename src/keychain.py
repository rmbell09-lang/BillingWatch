"""Keychain utilities for BillingWatch -- macOS production secrets."""
import subprocess
import os
import logging

logger = logging.getLogger(__name__)
SERVICE = "BillingWatch"


def get_secret(account: str, fallback_env: str = None) -> str:
    """Read a secret from macOS Keychain, with env var fallback."""
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", SERVICE, "-a", account, "-w"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            logger.debug(f"Loaded {account} from Keychain")
            return result.stdout.strip()
    except Exception as e:
        logger.warning(f"Keychain lookup failed for {account}: {e}")

    if fallback_env:
        val = os.environ.get(fallback_env, "")
        if val:
            logger.info(f"Using env var {fallback_env} for {account}")
            return val

    logger.warning(f"No value found for {account} (Keychain or env)")
    return ""


def get_stripe_secret_key() -> str:
    return get_secret("STRIPE_SECRET_KEY", "STRIPE_SECRET_KEY")


def get_stripe_webhook_secret() -> str:
    return get_secret("STRIPE_WEBHOOK_SECRET", "STRIPE_WEBHOOK_SECRET")


def get_db_password() -> str:
    return get_secret("DBEPASSWORD", "DB_PASSWORD")


def get_smtp_pass() -> str:
    return get_secret("SMTP_PASS", "SMTP_PASS")


def check_keychain_health() -> dict:
    """Return status of all expected Keychain entries."""
    return {
        "STRIPE_SECRET_KEY": bool(get_stripe_secret_key()),
        "STRIPE_WEBHOOK_SECRET": bool(get_stripe_webhook_secret()),
        "DB_PASSWORD": bool(get_db_password()),
        "SMTP_PASS": bool(get_smtp_pass()),
    }
