"""Assignment CRUD: PATCH /api/assignments/:id, DELETE /api/assignments/:id."""
from datetime import date, datetime

from flask import Blueprint, jsonify, request

from app.api.auth import decode_token, get_db

bp = Blueprint("assignments", __name__, url_prefix="/api/assignments")

VALID_TYPES = ("assignment", "midterm", "final", "quiz", "project", "participation")


def _owns_assignment(cur, assignment_id, user_id):
    """Returns assignment row if user owns it (via assignment -> course -> term), else None."""
    cur.execute(
        """
        SELECT a.id, a.assignment_name, a.work_load, a.notes, a.start_date, a.due_date, a.assignment_type, a.course_id
        FROM Assignments a
        JOIN Courses c ON c.id = a.course_id
        JOIN Terms t ON t.id = c.term_id
        WHERE a.id = %s AND t.user_id = %s
        """,
        (assignment_id, user_id),
    )
    return cur.fetchone()


@bp.route("/<int:assignment_id>", methods=["PATCH"])
def patch_assignment(assignment_id):
    """Update single assignment. Body: { assignment_name?, due_date?, hours?, type? }."""
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return jsonify({"error": "unauthorized"}), 401

    user_id = int(payload.get("sub"))
    data = request.get_json() or {}

    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        row = _owns_assignment(cur, assignment_id, user_id)
        if not row:
            return jsonify({"error": "Assignment not found"}), 404

        updates = []
        params = []

        if "assignment_name" in data:
            name = (data.get("assignment_name") or "").strip()
            if name:
                updates.append("assignment_name = %s")
                params.append(name)

        if "due_date" in data:
            due_raw = data.get("due_date")
            if due_raw is None or due_raw == "":
                updates.append("due_date = NULL")
            else:
                try:
                    due_dt = (
                        datetime.fromisoformat(str(due_raw).replace("Z", "+00:00"))
                        if due_raw
                        else None
                    )
                    if due_dt:
                        updates.append("due_date = %s")
                        params.append(due_dt)
                except (ValueError, TypeError):
                    pass

        if "hours" in data:
            try:
                hours = float(data.get("hours"))
                work_load = max(1, int(hours * 4))
                updates.append("work_load = %s")
                params.append(work_load)
            except (TypeError, ValueError):
                pass

        if "type" in data:
            atype = (data.get("type") or "assignment").strip().lower()
            if atype in VALID_TYPES:
                updates.append("assignment_type = %s")
                params.append(atype)

        if not updates:
            cur.execute(
                """
                SELECT id, assignment_name, work_load, notes, start_date, due_date, assignment_type
                FROM Assignments WHERE id = %s
                """,
                (assignment_id,),
            )
            out = cur.fetchone()
            if out.get("start_date"):
                out["start_date"] = out["start_date"].isoformat()
            if out.get("due_date"):
                out["due_date"] = out["due_date"].isoformat()
            out["hours"] = (out.get("work_load") or 0) / 4
            return jsonify(out)

        params.append(assignment_id)
        cur.execute(
            f"UPDATE Assignments SET {', '.join(updates)} WHERE id = %s",
            tuple(params),
        )
        conn.commit()

        cur.execute(
            """
            SELECT id, assignment_name, work_load, notes, start_date, due_date, assignment_type
            FROM Assignments WHERE id = %s
            """,
            (assignment_id,),
        )
        out = cur.fetchone()
        if out.get("start_date"):
            out["start_date"] = out["start_date"].isoformat()
        if out.get("due_date"):
            out["due_date"] = out["due_date"].isoformat()
        out["hours"] = (out.get("work_load") or 0) / 4
        return jsonify(out)
    finally:
        conn.close()


@bp.route("/<int:assignment_id>", methods=["DELETE"])
def delete_assignment(assignment_id):
    """Delete single assignment."""
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return jsonify({"error": "unauthorized"}), 401

    user_id = int(payload.get("sub"))

    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        if not _owns_assignment(cur, assignment_id, user_id):
            return jsonify({"error": "Assignment not found"}), 404

        cur.execute("DELETE FROM Assignments WHERE id = %s", (assignment_id,))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()
