from datetime import datetime

from flask import Blueprint, jsonify, request

from ..api.auth import decode_token, get_db

bp = Blueprint("courses", __name__)


def _owns_course(cur, course_id, user_id):
    """Returns course row if user owns it (via term), else None."""
    cur.execute(
        """
        SELECT c.id, c.course_name, c.term_id, t.term_name
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
            SELECT c.id, c.course_name,
                   COUNT(a.id) AS assignment_count
            FROM Courses c
            LEFT JOIN Assignments a ON a.course_id = c.id
            WHERE c.term_id = %s
            GROUP BY c.id, c.course_name
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
            "INSERT INTO Courses (course_name, term_id) VALUES (%s, %s)",
            (course_name, term_id),
        )
        course_id = cur.lastrowid
        conn.commit()
        return jsonify(
            {"id": course_id, "course_name": course_name, "assignment_count": 0}
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
            SELECT id, assignment_name, work_load, notes, start_date, due_date
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

        course["assignments"] = assignments
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

            cur.execute(
                """
                INSERT INTO Assignments
                  (assignment_name, work_load, notes, start_date, due_date, course_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (name, work_load, a.get("notes") or None, now, due_dt, course_id),
            )
            inserted += 1

        conn.commit()
        return jsonify({"ok": True, "inserted": inserted}), 201
    finally:
        conn.close()
