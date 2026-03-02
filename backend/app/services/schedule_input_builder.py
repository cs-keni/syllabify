"""
Build normalized schedule engine input from DB.
Teammate's scheduling engine can call this (or GET /api/schedule/engine-input) to get
everything needed: courses, meeting_times, work_items (from assignments), term, user_prefs.
See docs/parser-schedule-integration.md for the target schema.
"""
from app.api.auth import get_db


def _work_load_to_minutes(work_load: int) -> int:
    """work_load is 15-min blocks; convert to minutes."""
    return (work_load or 0) * 15


def build_engine_input(user_id: int, term_id: int | None = None, course_ids: list[int] | None = None) -> dict:
    """
    Build the normalized JSON the scheduling engine expects.
    If term_id is None, uses the active term. If course_ids is None, uses all courses in the term.
    """
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)

        # Resolve term
        if term_id:
            cur.execute(
                "SELECT id, term_name, start_date, end_date FROM Terms WHERE id = %s AND user_id = %s",
                (term_id, user_id),
            )
            term = cur.fetchone()
        else:
            cur.execute(
                "SELECT id, term_name, start_date, end_date FROM Terms WHERE user_id = %s AND is_active = 1",
                (user_id,),
            )
            term = cur.fetchone()
            if not term:
                cur.execute(
                    "SELECT id, term_name, start_date, end_date FROM Terms WHERE user_id = %s LIMIT 1",
                    (user_id,),
                )
                term = cur.fetchone()

        if not term:
            return {"error": "No term found", "courses": [], "user_prefs": _default_user_prefs()}

        term_id = term["id"]

        # Get courses in term
        if course_ids:
            placeholders = ",".join(["%s"] * len(course_ids))
            cur.execute(
                f"""
                SELECT c.id, c.course_name, c.study_hours_per_week, t.term_name, t.start_date, t.end_date
                FROM Courses c
                JOIN Terms t ON t.id = c.term_id
                WHERE c.term_id = %s AND c.id IN ({placeholders}) AND t.user_id = %s
                """,
                (term_id, *course_ids, user_id),
            )
        else:
            cur.execute(
                """
                SELECT c.id, c.course_name, c.study_hours_per_week, t.term_name, t.start_date, t.end_date
                FROM Courses c
                JOIN Terms t ON t.id = c.term_id
                WHERE c.term_id = %s AND t.user_id = %s
                """,
                (term_id, user_id),
            )
        courses_rows = cur.fetchall()

        courses_out = []
        for cr in courses_rows:
            cid = cr["id"]

            # Meetings (recurring format)
            cur.execute(
                """
                SELECT day_of_week, start_time_str, end_time_str, location, meeting_type
                FROM Meetings
                WHERE course_id = %s AND day_of_week IS NOT NULL
                """,
                (cid,),
            )
            meetings = cur.fetchall()
            meeting_times = [
                {
                    "day_of_week": m["day_of_week"],
                    "start_time": m["start_time_str"] or "",
                    "end_time": m["end_time_str"] or "",
                    "location": m["location"],
                    "type": m["meeting_type"] or "lecture",
                }
                for m in meetings
            ]

            # Assignments as work items
            cur.execute(
                """
                SELECT id, assignment_name, work_load, due_date, assignment_type
                FROM Assignments
                WHERE course_id = %s
                ORDER BY due_date
                """,
                (cid,),
            )
            assignments = cur.fetchall()
            work_items = [
                {
                    "id": str(a["id"]),
                    "title": a["assignment_name"],
                    "due": a["due_date"].isoformat() if a.get("due_date") else None,
                    "type": a["assignment_type"] or "assignment",
                    "est_minutes": _work_load_to_minutes(a.get("work_load") or 0),
                }
                for a in assignments
            ]

            courses_out.append({
                "id": str(cid),
                "course_code": cr["course_name"],
                "study_hours_per_week": cr.get("study_hours_per_week"),
                "meeting_times": meeting_times,
                "work_items": work_items,
            })

        start_date = term["start_date"].isoformat() if term.get("start_date") else None
        end_date = term["end_date"].isoformat() if term.get("end_date") else None

        return {
            "term": term["term_name"],
            "term_id": term_id,
            "start_date": start_date,
            "end_date": end_date,
            "timezone": "America/Los_Angeles",
            "courses": courses_out,
            "user_prefs": _default_user_prefs(),
        }
    finally:
        conn.close()


def _default_user_prefs() -> dict:
    """Defaults until UserPreferences table exists."""
    return {
        "work_start": "09:00",
        "work_end": "22:00",
        "preferred_days": ["MO", "TU", "WE", "TH", "FR"],
        "max_hours_per_day": 8,
    }
