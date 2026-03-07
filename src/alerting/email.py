"""Email alerting for BillingWatch.

Sends anomaly alerts via SMTP. Reads config from environment variables.

Required env vars:
    ALERT_EMAIL_FROM    - sender address
    ALERT_EMAIL_TO      - recipient address (comma-separated for multiple)
    SMTP_HOST           - SMTP server hostname
    SMTP_PORT           - SMTP server port (default: 587)
    SMTP_USER           - SMTP username
    SMTP_PASS           - SMTP password
    SMTP_USE_TLS        - "true" (default) or "false"
"""
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from ..detectors.base import Alert

logger = logging.getLogger(__name__)

SEVERITY_EMOJI = {
    "critical": "🚨",
    "high": "🔴",
    "medium": "🟡",
    "low": "🟢",
}


def _build_html(alert: Alert) -> str:
    """Render a clean HTML email body for the alert."""
    emoji = SEVERITY_EMOJI.get(alert.severity, "⚠️")
    meta_rows = "".join(
        f"<tr><td style='padding:4px 8px;color:#666;'>{k}</td>"
        f"<td style='padding:4px 8px;font-family:monospace;'>{v}</td></tr>"
        for k, v in alert.metadata.items()
    )
    meta_table = (
        f"<table style='border-collapse:collapse;margin-top:12px;'>{meta_rows}</table>"
        if meta_rows
        else ""
    )
    return f"""
<html><body style="font-family:sans-serif;max-width:640px;margin:0 auto;padding:20px;">
  <h2 style="margin-bottom:4px;">{emoji} BillingWatch Alert</h2>
  <p style="color:#888;font-size:13px;margin-top:0;">{alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
  <div style="background:#f8f8f8;border-left:4px solid #e44;padding:12px 16px;border-radius:4px;">
    <strong style="font-size:16px;">{alert.title}</strong>
    <p style="margin:8px 0 0;">{alert.message}</p>
  </div>
  <p style="color:#555;font-size:12px;">Detector: <code>{alert.detector}</code> &nbsp;|&nbsp; Severity: <strong>{alert.severity.upper()}</strong></p>
  {meta_table}
  <hr style="border:none;border-top:1px solid #eee;margin-top:24px;">
  <p style="color:#aaa;font-size:11px;">BillingWatch &mdash; Stripe anomaly detection</p>
</body></html>
"""


def _build_text(alert: Alert) -> str:
    """Plain-text fallback for the alert email."""
    lines = [
        f"BillingWatch Alert — {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"Detector : {alert.detector}",
        f"Severity : {alert.severity.upper()}",
        f"Title    : {alert.title}",
        f"",
        alert.message,
    ]
    if alert.metadata:
        lines.append("")
        lines.append("Details:")
        for k, v in alert.metadata.items():
            lines.append(f"  {k}: {v}")
    return "\n".join(lines)


class EmailAlerter:
    """Delivers BillingWatch alerts via SMTP email."""

    def __init__(
        self,
        from_addr: Optional[str] = None,
        to_addrs: Optional[List[str]] = None,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_pass: Optional[str] = None,
        use_tls: bool = True,
    ):
        self.from_addr = from_addr or os.environ.get("ALERT_EMAIL_FROM", "")
        to_raw = to_addrs or os.environ.get("ALERT_EMAIL_TO", "")
        self.to_addrs: List[str] = (
            [a.strip() for a in to_raw.split(",") if a.strip()]
            if isinstance(to_raw, str)
            else to_raw
        )
        self.smtp_host = smtp_host or os.environ.get("SMTP_HOST", "")
        self.smtp_port = smtp_port or int(os.environ.get("SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.environ.get("SMTP_USER", "")
        self.smtp_pass = smtp_pass or os.environ.get("SMTP_PASS", "")
        tls_env = os.environ.get("SMTP_USE_TLS", "true").lower()
        self.use_tls = use_tls if use_tls is not True else (tls_env != "false")

    @property
    def is_configured(self) -> bool:
        return bool(self.from_addr and self.to_addrs and self.smtp_host)

    def send(self, alert: Alert) -> bool:
        """Send the alert. Returns True on success, False on failure."""
        if not self.is_configured:
            logger.warning("[email] Not configured — skipping alert: %s", alert.title)
            return False

        subject = f"[BillingWatch] {alert.severity.upper()}: {alert.title}"
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_addr
        msg["To"] = ", ".join(self.to_addrs)
        msg.attach(MIMEText(_build_text(alert), "plain"))
        msg.attach(MIMEText(_build_html(alert), "html"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()
                if self.smtp_user:
                    server.login(self.smtp_user, self.smtp_pass)
                server.sendmail(self.from_addr, self.to_addrs, msg.as_string())
            logger.info("[email] Alert sent: %s → %s", alert.title, self.to_addrs)
            return True
        except Exception as exc:
            logger.error("[email] Failed to send alert '%s': %s", alert.title, exc)
            return False

    def send_batch(self, alerts: List[Alert]) -> int:
        """Send multiple alerts. Returns count of successes."""
        return sum(1 for a in alerts if self.send(a))
