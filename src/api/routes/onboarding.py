"""Onboarding checklist endpoint — step-by-step BillingWatch setup guide."""
import os
from fastapi import APIRouter
from typing import Dict, Any, List

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

_STEPS = [
    {
        "step": 1,
        "title": "Add Stripe Webhook",
        "status_key": "webhook_configured",
        "description": "In Stripe Dashboard → Developers → Webhooks, add your endpoint URL.",
        "endpoint": "POST /webhooks/stripe",
        "details": {
            "url_format": "https://YOUR_DOMAIN/webhooks/stripe",
            "events_to_select": [
                "charge.failed",
                "charge.succeeded",
                "charge.refunded",
                "customer.subscription.deleted",
                "customer.subscription.updated",
                "invoice.payment_failed",
                "invoice.payment_succeeded",
                "payment_intent.payment_failed",
                "payment_intent.succeeded"
            ],
            "note": "Copy the Stripe webhook signing secret — set it as STRIPE_WEBHOOK_SECRET env var."
        }
    },
    {
        "step": 2,
        "title": "Configure SMTP Alerts",
        "status_key": "smtp_configured",
        "description": "Set environment variables so BillingWatch can email you when anomalies fire.",
        "details": {
            "required_env_vars": {
                "SMTP_HOST": "e.g. smtp.gmail.com",
                "SMTP_PORT": "587",
                "SMTP_USER": "your email address",
                "SMTP_PASS": "app password (not account password)",
                "ALERT_EMAIL": "where to send alerts (can be same as SMTP_USER)"
            },
            "note": "Gmail: use an App Password (myaccount.google.com/apppasswords). 2FA must be enabled."
        }
    },
    {
        "step": 3,
        "title": "Optional: Slack / Discord Alerts",
        "status_key": "slack_or_discord_configured",
        "description": "Add a Slack or Discord webhook to get alerts in your team channel.",
        "details": {
            "slack": {
                "env_var": "SLACK_WEBHOOK_URL",
                "how_to_get": "Slack → Your App → Incoming Webhooks → Add New Webhook to Workspace"
            },
            "discord": {
                "env_var": "DISCORD_WEBHOOK_URL",
                "how_to_get": "Discord channel → Edit → Integrations → Webhooks → New Webhook → Copy URL"
            }
        }
    },
    {
        "step": 4,
        "title": "Tune Detector Thresholds",
        "status_key": "thresholds_reviewed",
        "description": "Default thresholds work for most SaaS — review and adjust for your traffic volume.",
        "endpoint": "GET /config/thresholds (coming in v1.2)",
        "details": {
            "key_defaults": {
                "charge_failure_rate_warning": "5% of charges in past hour",
                "charge_failure_rate_critical": "15% of charges in past hour",
                "revenue_drop_warning": "20% drop vs 7-day average",
                "revenue_drop_critical": "40% drop vs 7-day average",
                "webhook_lag_warning_seconds": 300,
                "webhook_lag_critical_seconds": 1800,
                "refund_rate_threshold": "10% of revenue"
            },
            "note": "If you process <100 charges/day, increase warning thresholds to reduce false positives."
        }
    },
    {
        "step": 5,
        "title": "Verify Detectors Are Running",
        "status_key": "detectors_verified",
        "description": "Send a test event and confirm the pipeline is working end-to-end.",
        "details": {
            "quick_test": "POST /demo/seed → injects 150+ synthetic events → check /anomalies/ for fired alerts",
            "cleanup_after_test": "DELETE /demo/seed removes all test data",
            "check_health": "GET /health should return {status: ok}",
            "check_metrics": "GET /metrics/detectors shows per-detector alert counts"
        }
    },
    {
        "step": 6,
        "title": "Monitor the Dashboard",
        "status_key": "dashboard_active",
        "description": "The dashboard gives you a real-time view of detector activity.",
        "details": {
            "dashboard_url": "GET /dashboard (Chart.js UI, auto-refreshes every 30s)",
            "api_summary": "GET /dashboard/summary (JSON health snapshot for integrations)",
            "what_to_watch": [
                "charge_failure_spike — spikes indicate Stripe payment issues",
                "webhook_lag — high lag means your endpoint is unreachable or slow",
                "silent_lapse — subscriptions cancelled without your system noticing",
                "revenue_drop — sudden MRR dips worth investigating"
            ]
        }
    }
]


def _check_configured() -> Dict[str, bool]:
    """Check which setup steps appear to be configured based on env vars."""
    return {
        "webhook_configured": bool(os.getenv("STRIPE_WEBHOOK_SECRET")),
        "smtp_configured": bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_USER")),
        "slack_or_discord_configured": bool(
            os.getenv("SLACK_WEBHOOK_URL") or os.getenv("DISCORD_WEBHOOK_URL")
        ),
        "thresholds_reviewed": False,  # manual step — always prompt
        "detectors_verified": False,   # manual step — always prompt
        "dashboard_active": True,      # always available
    }


@router.get("/", summary="Setup checklist")
async def get_onboarding() -> Dict[str, Any]:
    """
    Returns a step-by-step setup guide for BillingWatch.

    Each step includes instructions, required env vars, and a configured flag
    so you can track what's done. Steps 1-2 are required; rest are optional/recommended.
    """
    configured = _check_configured()
    steps_with_status = []
    completed = 0

    for step in _STEPS:
        key = step["status_key"]
        is_done = configured.get(key, False)
        if is_done:
            completed += 1
        steps_with_status.append({
            **step,
            "configured": is_done,
        })

    required_done = configured["webhook_configured"] and configured["smtp_configured"]

    return {
        "service": "BillingWatch",
        "version": "1.1.0",
        "setup_complete": required_done,
        "steps_completed": completed,
        "steps_total": len(_STEPS),
        "required_steps": ["webhook_configured", "smtp_configured"],
        "steps": steps_with_status,
        "next_step": next(
            (s for s in steps_with_status if not s["configured"]),
            None
        ),
        "docs": "/docs",
        "health": "/health",
        "quick_test": "POST /demo/seed"
    }
