"""Email digest builder for BillingWatch.

Compiles a summary of recent anomaly alerts into a digest email and
delivers it via SMTP (same credentials as EmailAlerter).

Usage:
    from src.alerting.digest import DigestBuilder
    builder = DigestBuilder()
    result = builder.send_digest(alerts, window_label="Last 24 hours")
"""

import logging
import os
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

SEVERITY_ORDER = ["critical", "high", "medium", "low"]
SEVERITY_COLOR = {
    "critical": "#cc0000",
    "high": "#e44444",
    "medium": "#e8a800",
    "low": "#4caf50",
}
SEVERITY_EMOJI = {
    "critical": "🚨",
    "high": "🔴",
    "medium": "🟡",
    "low": "🟢",
}


def _group_by_severity(alerts: List[dict]) -> Dict[str, List[dict]]:
    groups: Dict[str, List[dict]] = {s: [] for s in SEVERITY_ORDER}
    for a in alerts:
        sev = a.get("severity", "low")
        if sev in groups:
            groups[sev].append(a)
        else:
            groups["low"].append(a)
    return {k: v for k, v in groups.items() if v}


def _build_digest_html(
    alerts: List[dict],
    window_label: str,
    generated_at: datetime,
) -> str:
    if not alerts:
        return f"""
<html><body style="font-family:sans-serif;max-width:640px;margin:0 auto;padding:20px;">
  <h2>📋 BillingWatch Digest — {generated_at.strftime('%Y-%m-%d %H:%M UTC')}</h2>
  <p style="color:#555;">Window: <strong>{window_label}</strong></p>
  <div style="background:#f0f8f0;border-left:4px solid #4caf50;padding:12px 16px;border-radius:4px;">
    <strong>✅ All clear</strong> — No anomalies detected in this window.
  </div>
  <hr style="border:none;border-top:1px solid #eee;margin-top:24px;">
  <p style="color:#aaa;font-size:11px;">BillingWatch &mdash; Stripe anomaly detection</p>
</body></html>"""

    groups = _group_by_severity(alerts)
    total = len(alerts)

    # Summary bar
    summary_parts = []
    for sev in SEVERITY_ORDER:
        count = len(groups.get(sev, []))
        if count:
            emoji = SEVERITY_EMOJI[sev]
            summary_parts.append(f"{emoji} {count} {sev}")
    summary_str = " &nbsp;|&nbsp; ".join(summary_parts)

    # Alert rows
    rows_html = ""
    for sev in SEVERITY_ORDER:
        for a in groups.get(sev, []):
            color = SEVERITY_COLOR[sev]
            emoji = SEVERITY_EMOJI[sev]
            title = a.get("title", "Unknown alert")
            detector = a.get("detector", "")
            triggered = a.get("triggered_at", "")
            message = a.get("message", "")
            rows_html += f"""
  <div style="border:1px solid #eee;border-left:4px solid {color};border-radius:4px;padding:10px 14px;margin-bottom:8px;">
    <div style="display:flex;justify-content:space-between;align-items:center;">
      <strong>{emoji} {title}</strong>
      <span style="font-size:11px;color:#888;">{triggered}</span>
    </div>
    <div style="font-size:12px;color:#666;margin-top:4px;">{message}</div>
    <div style="font-size:11px;color:#aaa;margin-top:4px;">Detector: <code>{detector}</code></div>
  </div>"""

    return f"""
<html><body style="font-family:sans-serif;max-width:640px;margin:0 auto;padding:20px;">
  <h2 style="margin-bottom:4px;">📋 BillingWatch Digest</h2>
  <p style="color:#888;font-size:13px;margin-top:0;">{generated_at.strftime('%Y-%m-%d %H:%M UTC')} &nbsp;|&nbsp; Window: {window_label}</p>
  <div style="background:#fff8e1;border-left:4px solid #ffc107;padding:10px 14px;border-radius:4px;margin-bottom:16px;">
    <strong>{total} anomal{"y" if total == 1 else "ies"} detected</strong> &nbsp; {summary_str}
  </div>
  {rows_html}
  <hr style="border:none;border-top:1px solid #eee;margin-top:24px;">
  <p style="color:#aaa;font-size:11px;">BillingWatch &mdash; Stripe anomaly detection</p>
</body></html>"""


def _build_digest_text(
    alerts: List[dict],
    window_label: str,
    generated_at: datetime,
) -> str:
    lines = [
        f"BillingWatch Digest — {generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
        f"Window: {window_label}",
        "",
    ]
    if not alerts:
        lines.append("✅ All clear — No anomalies detected in this window.")
        return "\n".join(lines)

    lines.append(f"{len(alerts)} anomaly/anomalies detected:")
    lines.append("")
    groups = _group_by_severity(alerts)
    for sev in SEVERITY_ORDER:
        for a in groups.get(sev, []):
            emoji = SEVERITY_EMOJI[sev]
            lines.append(
                f"{emoji} [{sev.upper()}] {a.get('title','?')} — {a.get('detector','?')} @ {a.get('triggered_at','?')}"
            )
            if a.get("message"):
                lines.append(f"   {a['message']}")
    return "\n".join(lines)


class DigestBuilder:
    """Builds and sends BillingWatch email digests via SMTP."""

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
            else list(to_raw)
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

    def build_preview(
        self,
        alerts: List[dict],
        window_label: str = "Last 24 hours",
        generated_at: Optional[datetime] = None,
    ) -> dict:
        """Build digest content without sending. Always works regardless of SMTP config."""
        ts = generated_at or datetime.now(timezone.utc)
        return {
            "html": _build_digest_html(alerts, window_label, ts),
            "text": _build_digest_text(alerts, window_label, ts),
            "alert_count": len(alerts),
            "window_label": window_label,
            "generated_at": ts.isoformat(),
            "smtp_configured": self.is_configured,
        }

    def send_digest(
        self,
        alerts: List[dict],
        window_label: str = "Last 24 hours",
        generated_at: Optional[datetime] = None,
    ) -> dict:
        """Build and send digest. Returns result dict with sent/skipped/error."""
        ts = generated_at or datetime.now(timezone.utc)
        preview = self.build_preview(alerts, window_label, ts)

        if not self.is_configured:
            logger.info("[digest] SMTP not configured — digest built but not sent.")
            return {**preview, "sent": False, "reason": "smtp_not_configured"}

        total = len(alerts)
        subject = (
            f"[BillingWatch Digest] {total} anomal{'y' if total == 1 else 'ies'} — {window_label}"
            if total > 0
            else f"[BillingWatch Digest] All clear — {window_label}"
        )

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_addr
        msg["To"] = ", ".join(self.to_addrs)
        msg.attach(MIMEText(preview["text"], "plain"))
        msg.attach(MIMEText(preview["html"], "html"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()
                if self.smtp_user:
                    server.login(self.smtp_user, self.smtp_pass)
                server.sendmail(self.from_addr, self.to_addrs, msg.as_string())
            logger.info("[digest] Sent digest (%d alerts) → %s", total, self.to_addrs)
            return {**preview, "sent": True, "recipients": self.to_addrs}
        except Exception as exc:
            logger.error("[digest] Failed to send digest: %s", exc)
            return {**preview, "sent": False, "reason": str(exc)}
