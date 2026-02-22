"""
Courses API: GET list, POST create (save after review), DELETE.
"""
import os

import mysql.connector
from flask import Blueprint, jsonify, request

from app.api.auth import decode_token

bp = Blueprint("courses", __name__, url_prefix="/api/courses")


def get_db():
    """MySQL connection using DB_* env vars."""
    port = os.getenv("DB_PORT", "3306")
    try:
        port = int(port)
    except (TypeError, ValueError):
        port = 3306
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "mysql"),
        port=port,
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        connection_timeout=15,
    )


def _require_user():
    """Extract and validate user_id from JWT. Returns (user_id, error_response) or (user_id, None)."""
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return None, (jsonify({"error": "unauthorized"}), 401)
    try:
        user_id = int(payload.get("sub"))
        return user_id, None
    except (TypeError, ValueError):
        return None, (jsonify({"error": "unauthorized"}), 401)


@bp.route("", methods=["GET"])
def list_courses():
    """GET /api/courses — list current user's courses with assignment counts."""
    user_id, err = _require_user()
    if err:
        return err
    conn = None
    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT c.id, c.name, (SELECT COUNT(*) FROM Assignments a WHERE a.course_id = c.id) AS assignment_count "
            "FROM Courses c WHERE c.owner_id = %s ORDER BY c.id DESC",
            (user_id,),
        )
        rows = cur.fetchall()
        courses = [
            {
                "id": r["id"],
                "name": r["name"],
                "assignment_count": r["assignment_count"] or 0,
            }
            for r in rows
        ]
        return jsonify({"courses": courses}), 200
    finally:
        if conn:
            conn.close()


@bp.route("", methods=["POST"])
def create_course():
    """
    POST /api/courses — save course + assignments after review.
    Body: { "course_name": "...", "assignments": [{ "name", "due"?, "hours"? }] }
    """
    user_id, err = _require_user()
    if err:
        return err
    data = request.get_json() or {}
    course_name = (data.get("course_name") or data.get("name") or "Course").strip()[:255]
    raw_assignments = data.get("assignments") or []

    conn = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Courses (name, owner_id) VALUES (%s, %s)",
            (course_name, user_id),
        )
        course_id = cur.lastrowid

        for a in raw_assignments:
            name = (a.get("name") or "").strip()[:255]
            if not name:
                continue
            due = a.get("due") or a.get("due_date")
            hours = a.get("hours")
            if hours is None:
                hours = 3
            try:
                hours = min(max(int(hours), 1), 10)
            except (TypeError, ValueError):
                hours = 3
            cur.execute(
                "INSERT INTO Assignments (assignment_name, work_load, due_date, course_id, schedule_id) "
                "VALUES (%s, %s, %s, %s, NULL)",
                (name, hours, due, course_id),
            )
        conn.commit()
        return jsonify({"id": course_id, "course_name": course_name}), 201
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@bp.route("/<int:course_id>", methods=["DELETE"])
def delete_course(course_id):
    """DELETE /api/courses/:id — remove course and its assignments. Owner only."""
    user_id, err = _require_user()
    if err:
        return err
    conn = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM Courses WHERE id = %s AND owner_id = %s",
            (course_id, user_id),
        )
        if not cur.fetchone():
            return jsonify({"error": "not found"}), 404
        cur.execute("DELETE FROM Assignments WHERE course_id = %s", (course_id,))
        cur.execute("DELETE FROM Courses WHERE id = %s", (course_id,))
        conn.commit()
        return jsonify({"ok": True}), 200
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()
