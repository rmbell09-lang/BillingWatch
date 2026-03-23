"""Digest API — trigger and configure BillingWatch email digests.

POST /digest/send       — send (or preview) digest now
GET  /digest/config     — get digest schedule config
PUT  /digest/config     — update digest schedule config
"""

from datetime import datetime, timezone, timedelta
from typing import List, Literal, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, EmailStr, field_validator

from ...alerting.digest import DigestBuilder
from .webhooks import _alert_log  # shared in-memory alert log

router = APIRouter(prefix="/digest", tags=["digest"])

# ---------------------------------------------------------------------------
# In-memory digest config (persisted across requests, reset on restart)
# ---------------------------------------------------------------------------
_digest_config: dict = {
    "enabled": False,
    "frequency": "daily",          # "daily" | "weekly"
    "window_hours": 24,
    "to_addrs": [],                 # override recipients (empty = use env vars)
    "last_sent_at": None,
    "next_due_at": None,
}


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class DigestConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    frequency: Optional[Literal["daily", "weekly"]] = None
    window_hours: Optional[int] = None
    to_addrs: Optional[List[str]] = None

    @field_validator("window_hours")
    @classmethod
    def valid_window(cls, v):
        if v is not None and not (1 <= v <= 168):
            raise ValueError("window_hours must be between 1 and 168 (1 week)")
        return v


class DigestSendRequest(BaseModel):
    window_hours: int = 24
    preview_only: bool = False     # if True, build but don't send
    to_addrs: Optional[List[str]] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _filter_alerts(window_hours: int) -> List[dict]:
    """Return alerts from _alert_log within the last window_hours."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    result = []
    for a in _alert_log:
        triggered = a.get("triggered_at")
        if not triggered:
            result.append(a)
            continue
        try:
            if isinstance(triggered, str):
                # parse ISO string — handle with and without tz
                ts = datetime.fromisoformat(triggered.replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            elif isinstance(triggered, datetime):
                ts = triggered if triggered.tzinfo else triggered.replace(tzinfo=timezone.utc)
            else:
                result.append(a)
                continue
            if ts >= cutoff:
                result.append(a)
        except (ValueError, TypeError):
            result.append(a)
    return result


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/send")
async def send_digest(body: DigestSendRequest = DigestSendRequest()):
    """
    Build and send (or preview) a BillingWatch digest email.

    - **preview_only=true** builds the HTML/text but does NOT send — useful for testing.
    - **window_hours** controls how far back to look for alerts (default 24).
    - **to_addrs** overrides ALERT_EMAIL_TO env var for this send only.

    Example:
        curl -X POST http://localhost:8000/digest/send \\
             -H 'Content-Type: application/json' \\
             -d '{"window_hours": 24, "preview_only": false}'
    """
    alerts = _filter_alerts(body.window_hours)
    window_label = f"Last {body.window_hours} hour{'s' if body.window_hours != 1 else ''}"
    now = datetime.now(timezone.utc)

    builder_kwargs = {}
    if body.to_addrs:
        builder_kwargs["to_addrs"] = body.to_addrs

    builder = DigestBuilder(**builder_kwargs)

    if body.preview_only:
        result = builder.build_preview(alerts, window_label=window_label, generated_at=now)
        return {"mode": "preview", **result}

    result = builder.send_digest(alerts, window_label=window_label, generated_at=now)

    # Update last_sent_at in config if we actually sent
    if result.get("sent"):
        _digest_config["last_sent_at"] = now.isoformat()
        freq = _digest_config.get("frequency", "daily")
        hours_ahead = 24 if freq == "daily" else 168
        _digest_config["next_due_at"] = (now + timedelta(hours=hours_ahead)).isoformat()

    return {"mode": "send", **result}


@router.get("/config")
async def get_digest_config():
    """
    Return current digest schedule configuration.

    Example:
        curl http://localhost:8000/digest/config
    """
    return {"config": _digest_config}


@router.put("/config")
async def update_digest_config(body: DigestConfigUpdate):
    """
    Update digest schedule configuration.

    Example:
        curl -X PUT http://localhost:8000/digest/config \\
             -H 'Content-Type: application/json' \\
             -d '{"enabled": true, "frequency": "daily", "window_hours": 24}'
    """
    if body.enabled is not None:
        _digest_config["enabled"] = body.enabled
    if body.frequency is not None:
        _digest_config["frequency"] = body.frequency
    if body.window_hours is not None:
        _digest_config["window_hours"] = body.window_hours
    if body.to_addrs is not None:
        _digest_config["to_addrs"] = body.to_addrs

    return {"config": _digest_config, "updated": True}
