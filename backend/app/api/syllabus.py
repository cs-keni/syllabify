"""
Syllabus API: POST /parse for file upload or pasted text.
Returns course_name, assignments (name, due_date, hours), confidence, raw_text.
Requires JWT. Persists Courses and Assignments on success.
"""
import os

import mysql.connector
from flask import Blueprint, request, jsonify

from app.api.auth import decode_token
from app.services.parsing_service import parse_file, parse_text

bp = Blueprint("syllabus", __name__, url_prefix="/api/syllabus")


def get_db():
    """MySQL connection using DB_* env vars (same pattern as auth)."""
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


@bp.route("/parse", methods=["POST"])
def parse():
    """
    Accept multipart/form-data (file) or application/json ({"text": "..."}).
    Returns { course_name, assignments, confidence?, raw_text? }.
    On success, inserts Course and Assignments; requires JWT.
    """
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return jsonify({"error": "unauthorized"}), 401
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        return jsonify({"error": "unauthorized"}), 401

    text = None
    file = None
    mode = request.args.get("mode", "rule")

    # JSON body: {"text": "..."}
    if request.is_json:
        data = request.get_json() or {}
        text = data.get("text")

    # Multipart: file upload
    if "file" in (request.files or {}):
        file = request.files.get("file")
        if file and file.filename:
            file = file

    if not text and not file:
        return jsonify({"error": "provide file or text"}), 400

    if file and text:
        return jsonify({"error": "provide either file or text, not both"}), 400

    try:
        if file:
            result = parse_file(file, mode=mode)
        else:
            result = parse_text(text or "", mode=mode)
    except Exception as e:
        return jsonify({"error": f"parse failed: {e}"}), 500

    course_name = result.get("course_name") or "Course"
    assignments = result.get("assignments") or []

    # Persist to DB
    conn = None
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO Courses (name, owner_id) VALUES (%s, %s)",
            (course_name[:255], user_id),
        )
        course_id = cur.lastrowid

        for a in assignments:
            name = (a.get("name") or "").strip()[:255]
            if not name:
                continue
            due = a.get("due_date")  # YYYY-MM-DD string or None
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
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"database error: {e}"}), 500
    finally:
        if conn:
            conn.close()

    # Build response (omit raw_text if confidence is high per spec)
    resp = {
        "course_name": course_name,
        "assignments": assignments,
    }
    if result.get("confidence"):
        resp["confidence"] = result["confidence"]
    if result.get("raw_text") is not None:
        resp["raw_text"] = result["raw_text"]

    return jsonify(resp), 200
