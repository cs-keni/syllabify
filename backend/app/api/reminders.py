"""
Due-date email reminders.
Call POST /api/reminders/send (requires X-Cron-Secret or admin JWT) to trigger
3-day and 1-day advance reminders for upcoming assignments.

Configure in .env:
  CRON_SECRET    — shared secret for the cron caller (no auth needed if set and matches)
  SMTP_HOST / SMTP_USER / SMTP_PASS / SMTP_FROM  — email delivery
"""
import logging
import os
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request

from app.api.auth import decode_token
from app.db.connection import get_db
from app.services.email_service import is_configured, send_email

bp = Blueprint("reminders", __name__, url_prefix="/api/reminders")
logger = logging.getLogger(__name__)

REMINDER_DAYS = [3, 1]
_APP_URL = os.getenv("FRONTEND_URL", "https://syllabify.app").rstrip("/")


def _authorized(req) -> bool:
    """Returns True if the request is from a trusted cron caller or an admin."""
    cron_secret = os.getenv("CRON_SECRET", "").strip()
    if cron_secret and req.headers.get("X-Cron-Secret", "") == cron_secret:
        return True
    payload = decode_token(req.headers.get("Authorization", ""))
    if not payload:
        return False
    from app.api.admin import _is_admin
    return _is_admin(payload.get("username", ""))


@bp.route("/send", methods=["POST"])
def send_reminders():
    """Trigger due-date email reminders. Auth: X-Cron-Secret header or admin JWT."""
    if not _authorized(request):
        return jsonify({"error": "unauthorized"}), 401

    if not is_configured():
        return jsonify({"ok": True, "sent": 0, "note": "SMTP not configured — no emails sent"}), 200

    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        now = datetime.now(tz=timezone.utc)
        sent = 0

        for days_ahead in REMINDER_DAYS:
            # Match assignments whose due_date falls within a ±12-hour window around the target day
            target = now + timedelta(days=days_ahead)
            window_start = (target - timedelta(hours=12)).date()
            window_end = (target + timedelta(hours=12)).date()

            cur.execute(
                """
                SELECT u.email, u.username,
                       a.assignment_name, a.due_date,
                       c.course_name
                FROM Assignments a
                JOIN Courses c ON a.course_id = c.id
                JOIN Terms t   ON c.term_id = t.id
                JOIN Users u   ON t.user_id = u.id
                WHERE DATE(a.due_date) BETWEEN %s AND %s
                  AND (a.is_completed = FALSE OR a.is_completed IS NULL)
                  AND u.email IS NOT NULL
                  AND u.email != ''
                """,
                (str(window_start), str(window_end)),
            )

            for row in cur.fetchall():
                try:
                    due_dt = datetime.fromisoformat(str(row["due_date"]))
                    due_str = due_dt.strftime("%A, %b %-d")
                except Exception:
                    due_str = str(row["due_date"])

                day_word = f"{days_ahead} day{'s' if days_ahead > 1 else ''}"
                subject = f"Due in {day_word}: {row['assignment_name']} ({row['course_name']})"
                html = f"""
<p style="font-family:sans-serif;color:#111">Hi {row['username']},</p>
<p style="font-family:sans-serif;color:#111">
  <strong>{row['assignment_name']}</strong> for
  <em>{row['course_name']}</em> is due in
  <strong>{day_word}</strong> — <strong>{due_str}</strong>.
</p>
<p style="font-family:sans-serif">
  <a href="{_APP_URL}/app/schedule" style="color:#0F8A4C">View your schedule →</a>
</p>
<p style="font-family:sans-serif;color:#888;font-size:12px">
  You received this because your Syllabify account has email notifications enabled.
</p>
"""
                if send_email(row["email"], subject, html):
                    sent += 1

        return jsonify({"ok": True, "sent": sent})
    finally:
        conn.close()


@bp.route("/status", methods=["GET"])
def reminder_status():
    """Returns whether email reminders are configured. Admin only."""
    payload = decode_token(request.headers.get("Authorization", ""))
    if not payload:
        return jsonify({"error": "unauthorized"}), 401
    from app.api.admin import _is_admin
    if not _is_admin(payload.get("username", "")):
        return jsonify({"error": "admin required"}), 403
    return jsonify({"configured": is_configured()})
