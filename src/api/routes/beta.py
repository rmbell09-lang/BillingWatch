"""Beta Feedback Tracker — POST /beta/feedback endpoint.

Stores structured beta user feedback in SQLite for Ray to review.
Table: beta_feedback(id, email, caught_anything, missing_detectors, referral, raw_text, submitted_at)

Usage:
    POST /beta/feedback  { "email": "...", "caught_anything": "yes - silent lapse", "missing_detectors": "...", "referral": "...", "raw_text": "..." }
    GET  /beta/feedback  — list all feedback (for Ray's review)
"""
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi.responses import JSONResponse
from pydantic import BaseModel

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/beta", tags=["beta"])

_DB_PATH = Path(__file__).parent.parent.parent.parent / "billingwatch.db"

_CREATE_FEEDBACK_TABLE = """
CREATE TABLE IF NOT EXISTS beta_feedback (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    email              TEXT,
    caught_anything    TEXT,
    missing_detectors  TEXT,
    referral           TEXT,
    raw_text           TEXT,
    submitted_at       REAL    NOT NULL
);
"""

_CREATE_FEEDBACK_INDEX = "CREATE INDEX IF NOT EXISTS idx_beta_feedback_submitted ON beta_feedback(submitted_at DESC);"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_table():
    conn = _get_conn()
    try:
        conn.execute(_CREATE_FEEDBACK_TABLE)
        conn.execute(_CREATE_FEEDBACK_INDEX)
        conn.commit()
    finally:
        conn.close()


_init_table()


class FeedbackSubmission(BaseModel):
    email: Optional[str] = None
    caught_anything: Optional[str] = None        # "yes - [description]" or "no"
    missing_detectors: Optional[str] = None      # what they wish BillingWatch caught
    referral: Optional[str] = None               # who they'd refer
    raw_text: Optional[str] = None               # freeform / additional notes


@router.post("/feedback", status_code=201)
@limiter.limit("5/minute")
async def submit_feedback(request: Request, body: FeedbackSubmission):
    """
    Submit beta user feedback.
    Called from onboarding email Day 7 reply or in-product prompt.
    """
    now = time.time()
    conn = _get_conn()
    try:
        cursor = conn.execute(
            """
            INSERT INTO beta_feedback (email, caught_anything, missing_detectors, referral, raw_text, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                body.email,
                body.caught_anything,
                body.missing_detectors,
                body.referral,
                body.raw_text,
                now,
            ),
        )
        conn.commit()
        feedback_id = cursor.lastrowid
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save feedback: {exc}")
    finally:
        conn.close()

    return {
        "id": feedback_id,
        "status": "received",
        "message": "Thanks for the feedback — Ray reads every response.",
        "submitted_at": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
    }


@router.get("/feedback")
async def list_feedback(limit: int = 50):
    """
    List all beta feedback (newest first). For Ray to review via curl or MC.

    Example:
        curl http://localhost:8080/beta/feedback
    """
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM beta_feedback ORDER BY submitted_at DESC LIMIT ?",
            (min(limit, 200),),
        ).fetchall()
    finally:
        conn.close()

    entries = [dict(row) for row in rows]
    for e in entries:
        ts = e.get("submitted_at")
        if ts:
            e["submitted_at_iso"] = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

    return {
        "count": len(entries),
        "feedback": entries,
    }


@router.get("/feedback/summary")
async def feedback_summary():
    """
    Quick summary stats for the beta feedback log.
    """
    conn = _get_conn()
    try:
        total = conn.execute("SELECT COUNT(*) FROM beta_feedback").fetchone()[0]
        caught = conn.execute(
            "SELECT COUNT(*) FROM beta_feedback WHERE caught_anything IS NOT NULL AND caught_anything != '' AND LOWER(caught_anything) != 'no'"
        ).fetchone()[0]
        with_referral = conn.execute(
            "SELECT COUNT(*) FROM beta_feedback WHERE referral IS NOT NULL AND referral != ''"
        ).fetchone()[0]
        latest = conn.execute(
            "SELECT email, submitted_at FROM beta_feedback ORDER BY submitted_at DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()

    return {
        "total_submissions": total,
        "caught_something": caught,
        "provided_referral": with_referral,
        "latest_email": dict(latest) if latest else None,
    }
