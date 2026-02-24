from datetime import date, datetime

from flask import Blueprint, jsonify, request

from ..api.auth import decode_token, get_db

bp = Blueprint("courses", __name__)


def _owns_course(cur, course_id, user_id):
    """Returns course row if user owns it (via term), else None."""
    cur.execute(
        """
        SELECT c.id, c.course_name, c.term_id, c.study_hours_per_week, t.term_name
        FROM Courses c
        JOIN Terms t ON t.id = c.term_id
        WHERE c.id = %s AND t.user_id = %s
        """,
        (course_id, user_id),
    )
    return cur.fetchone()


@bp.route("/api/terms/<int:term_id>/courses", methods=["GET"])
def list_courses(term_id):
    """List courses for a term with assignment count."""
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return jsonify({"error": "unauthorized"}), 401

    user_id = int(payload.get("sub"))
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id FROM Terms WHERE id = %s AND user_id = %s",
            (term_id, user_id),
        )
        if not cur.fetchone():
            return jsonify({"error": "Term not found"}), 404

        cur.execute(
            """
            SELECT c.id, c.course_name, c.study_hours_per_week,
                   COUNT(a.id) AS assignment_count
            FROM Courses c
            LEFT JOIN Assignments a ON a.course_id = c.id
            WHERE c.term_id = %s
            GROUP BY c.id, c.course_name, c.study_hours_per_week
            ORDER BY c.id
            """,
            (term_id,),
        )
        return jsonify({"courses": cur.fetchall()})
    finally:
        conn.close()


@bp.route("/api/terms/<int:term_id>/courses", methods=["POST"])
def create_course(term_id):
    """Create a course under a term."""
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return jsonify({"error": "unauthorized"}), 401

    user_id = int(payload.get("sub"))
    data = request.get_json() or {}
    course_name = (data.get("course_name") or "").strip()
    if not course_name:
        return jsonify({"error": "course_name is required"}), 400
    study_hours_per_week = data.get("study_hours_per_week")
    if study_hours_per_week is not None:
        try:
            study_hours_per_week = int(study_hours_per_week)
            if study_hours_per_week < 0 or study_hours_per_week > 168:
                study_hours_per_week = None
        except (TypeError, ValueError):
            study_hours_per_week = None

    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id FROM Terms WHERE id = %s AND user_id = %s",
            (term_id, user_id),
        )
        if not cur.fetchone():
            return jsonify({"error": "Term not found"}), 404

        cur.execute(
            "INSERT INTO Courses (course_name, term_id, study_hours_per_week) VALUES (%s, %s, %s)",
            (course_name, term_id, study_hours_per_week),
        )
        course_id = cur.lastrowid
        conn.commit()
        return jsonify(
            {"id": course_id, "course_name": course_name, "study_hours_per_week": study_hours_per_week, "assignment_count": 0}
        ), 201
    finally:
        conn.close()


@bp.route("/api/courses/<int:course_id>", methods=["GET"])
def get_course(course_id):
    """Get course detail with its assignments."""
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return jsonify({"error": "unauthorized"}), 401

    user_id = int(payload.get("sub"))
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        course = _owns_course(cur, course_id, user_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        cur.execute(
            """
            SELECT id, assignment_name, work_load, notes, start_date, due_date, assignment_type
            FROM Assignments
            WHERE course_id = %s
            ORDER BY due_date
            """,
            (course_id,),
        )
        assignments = cur.fetchall()
        for a in assignments:
            if a.get("start_date"):
                a["start_date"] = a["start_date"].isoformat()
            if a.get("due_date"):
                a["due_date"] = a["due_date"].isoformat()

        cur.execute(
            """
            SELECT id, day_of_week, start_time_str, end_time_str, location, meeting_type
            FROM Meetings
            WHERE course_id = %s AND day_of_week IS NOT NULL
            """,
            (course_id,),
        )
        meetings = cur.fetchall()
        # Engine-friendly format: day_of_week, start_time, end_time, location, type
        meeting_times = [
            {
                "id": m["id"],
                "day_of_week": m["day_of_week"],
                "start_time": m["start_time_str"] or "",
                "end_time": m["end_time_str"] or "",
                "location": m["location"],
                "type": m["meeting_type"] or "lecture",
            }
            for m in meetings
        ]

        course["assignments"] = assignments
        course["meeting_times"] = meeting_times
        return jsonify(course)
    finally:
        conn.close()


@bp.route("/api/courses/<int:course_id>", methods=["DELETE"])
def delete_course(course_id):
    """Delete a course and cascade to assignments/meetings."""
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return jsonify({"error": "unauthorized"}), 401

    user_id = int(payload.get("sub"))
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        if not _owns_course(cur, course_id, user_id):
            return jsonify({"error": "Course not found"}), 404

        cur.execute("DELETE FROM Courses WHERE id = %s", (course_id,))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()


@bp.route("/api/courses/<int:course_id>/assignments", methods=["POST"])
def add_assignments(course_id):
    """Bulk-add assignments to an existing course after syllabus review."""
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return jsonify({"error": "unauthorized"}), 401

    user_id = int(payload.get("sub"))
    data = request.get_json() or {}
    items = data.get("assignments", [])
    if not items:
        return jsonify({"error": "assignments list is required"}), 400

    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        if not _owns_course(cur, course_id, user_id):
            return jsonify({"error": "Course not found"}), 404

        now = datetime.utcnow()
        inserted = 0
        for a in items:
            name = (a.get("name") or "").strip()
            if not name:
                continue
            hours = float(a.get("hours") or 0)
            work_load = max(1, int(hours * 4))  # 15-min increments
            due_raw = a.get("due") or a.get("due_date")
            try:
                due_dt = datetime.fromisoformat(due_raw) if due_raw else now
            except (ValueError, TypeError):
                due_dt = now

            atype = (a.get("type") or "assignment").strip().lower()
            if atype not in ("assignment", "midterm", "final", "quiz", "project", "participation"):
                atype = "assignment"

            # Fallback for empty due: use term end_date (for scheduling engine)
            if not due_raw and due_dt == now:
                cur.execute(
                    "SELECT t.end_date FROM Courses c JOIN Terms t ON t.id = c.term_id WHERE c.id = %s",
                    (course_id,),
                )
                row = cur.fetchone()
                if row and row.get("end_date"):
                    end_d = row["end_date"]
                    due_dt = (
                        datetime.combine(end_d, datetime.min.time())
                        if isinstance(end_d, date) and not isinstance(end_d, datetime)
                        else end_d
                    )

            cur.execute(
                """
                INSERT INTO Assignments
                  (assignment_name, work_load, notes, start_date, due_date, assignment_type, course_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (name, work_load, a.get("notes") or None, now, due_dt, atype, course_id),
            )
            inserted += 1

        conn.commit()
        return jsonify({"ok": True, "inserted": inserted}), 201
    finally:
        conn.close()


@bp.route("/api/courses/<int:course_id>/meetings", methods=["POST"])
def add_meetings(course_id):
    """Bulk-add recurring meeting times (from parsed syllabus) for scheduling engine."""
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return jsonify({"error": "unauthorized"}), 401

    user_id = int(payload.get("sub"))
    data = request.get_json() or {}
    items = data.get("meeting_times", [])

    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        if not _owns_course(cur, course_id, user_id):
            return jsonify({"error": "Course not found"}), 404

        # Delete existing meetings for this course (replace on save)
        cur.execute("DELETE FROM Meetings WHERE course_id = %s", (course_id,))

        inserted = 0
        for m in items:
            day = (m.get("day_of_week") or "").strip().upper()
            if not day or len(day) < 2:
                continue
            start_str = (m.get("start_time") or m.get("start_time_str") or "").strip()
            end_str = (m.get("end_time") or m.get("end_time_str") or "").strip()
            if not start_str or not end_str:
                continue
            loc = (m.get("location") or "").strip() or None
            mtype = (m.get("type") or m.get("meeting_type") or "lecture").strip()
            cur.execute(
                """
                INSERT INTO Meetings
                  (course_id, day_of_week, start_time_str, end_time_str, location, meeting_type)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (course_id, day[:2], start_str[:5], end_str[:5], loc, mtype[:50]),
            )
            inserted += 1

        conn.commit()
        return jsonify({"ok": True, "inserted": inserted}), 201
    finally:
        conn.close()
