from __future__ import annotations

import secrets
from datetime import datetime, time, timedelta

from app.services.ics_serializer import serialize_study_times_to_ics


def _new_feed_token() -> str:
    return secrets.token_urlsafe(32)


def _generate_unique_feed_token(cur, max_attempts: int = 10) -> str:
    for _ in range(max_attempts):
        candidate = _new_feed_token()
        cur.execute(
            "SELECT id FROM Users WHERE ical_feed_token = %s LIMIT 1",
            (candidate,),
        )
        if not cur.fetchone():
            return candidate
    raise RuntimeError("failed to generate unique feed token")


def get_or_create_feed_token(conn, user_id: int) -> tuple[str, bool]:
    """Return (token, enabled). Auto-creates token for first-time users."""
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """SELECT ical_feed_token, COALESCE(ical_feed_enabled, 1) AS ical_feed_enabled
           FROM Users WHERE id = %s""",
        (user_id,),
    )
    row = cur.fetchone()
    if not row:
        cur.close()
        raise ValueError("user not found")

    token = row.get("ical_feed_token")
    enabled = bool(row.get("ical_feed_enabled"))
    if token:
        cur.close()
        return token, enabled

    token = _generate_unique_feed_token(cur)
    cur.execute(
        """UPDATE Users
           SET ical_feed_token = %s,
               ical_feed_enabled = COALESCE(ical_feed_enabled, 1),
               ical_feed_token_updated_at = NOW()
           WHERE id = %s""",
        (token, user_id),
    )
    conn.commit()
    cur.close()
    return token, enabled


def rotate_feed_token(conn, user_id: int) -> str:
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id FROM Users WHERE id = %s", (user_id,))
    if not cur.fetchone():
        cur.close()
        raise ValueError("user not found")

    token = _generate_unique_feed_token(cur)
    cur.execute(
        """UPDATE Users
           SET ical_feed_token = %s, ical_feed_token_updated_at = NOW()
           WHERE id = %s""",
        (token, user_id),
    )
    conn.commit()
    cur.close()
    return token


def set_feed_enabled(conn, user_id: int, enabled: bool) -> None:
    cur = conn.cursor()
    cur.execute(
        "UPDATE Users SET ical_feed_enabled = %s WHERE id = %s",
        (1 if enabled else 0, user_id),
    )
    conn.commit()
    cur.close()


def get_export_horizon(conn, user_id: int, now_utc: datetime | None = None) -> tuple[datetime, datetime]:
    """MVP horizon: [today-14d, active_term_end] else [today-14d, today+120d]."""
    now_dt = now_utc or datetime.utcnow()
    start = (now_dt - timedelta(days=14)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    cur = conn.cursor(dictionary=True)
    cur.execute(
        """SELECT end_date FROM Terms
           WHERE user_id = %s AND is_active = 1
           ORDER BY end_date DESC
           LIMIT 1""",
        (user_id,),
    )
    row = cur.fetchone()
    cur.close()

    if row and row.get("end_date"):
        end_date = row["end_date"]
        end = datetime.combine(end_date, time(23, 59, 59))
    else:
        end = (now_dt + timedelta(days=120)).replace(
            hour=23, minute=59, second=59, microsecond=0
        )
    return start, end


def fetch_eligible_study_times(
    conn, user_id: int, horizon_start: datetime, horizon_end: datetime
) -> list[dict]:
    """Load app-owned StudyTimes only (no external events), scoped to active term and horizon."""
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """SELECT st.id, st.start_time, st.end_time, st.notes, st.is_locked,
                  st.assignment_id, st.course_id,
                  c.course_name, a.assignment_name
           FROM StudyTimes st
           JOIN Terms t ON st.term_id = t.id
           LEFT JOIN Courses c ON st.course_id = c.id
           LEFT JOIN Assignments a ON st.assignment_id = a.id
           WHERE t.user_id = %s
             AND t.is_active = 1
             AND st.start_time IS NOT NULL
             AND st.end_time IS NOT NULL
             AND st.end_time > st.start_time
             AND st.start_time <= %s
             AND st.end_time >= %s
           ORDER BY st.start_time ASC""",
        (user_id, horizon_end, horizon_start),
    )
    rows = cur.fetchall() or []
    cur.close()
    return rows


def build_ical_feed_for_user(conn, user_id: int) -> bytes:
    start, end = get_export_horizon(conn, user_id)
    study_times = fetch_eligible_study_times(conn, user_id, start, end)
    return serialize_study_times_to_ics(study_times)
