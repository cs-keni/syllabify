"""
Schedule API: engine input for scheduling teammate.
Returns normalized JSON (courses, meeting_times, work_items, term) per parser-schedule-integration.md.
"""
import os

from flask import Blueprint, jsonify, request

from app.api.auth import decode_token
from app.db.session import SessionLocal
from app.services.schedule_input_builder import build_engine_input
from app.services.scheduling_service import generate_study_times


def _get_db():
    import mysql.connector
    port = os.getenv("DB_PORT", "3306")
    try:
        port = int(port)
    except (TypeError, ValueError):
        port = 3306
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=port,
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        connection_timeout=15,
    )


def _get_user(req):
    """Extract user_id from JWT. Returns (user_id, None) or (None, error_response)."""
    auth = req.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return None, (jsonify({"error": "unauthorized"}), 401)
    try:
        return int(payload.get("sub")), None
    except (TypeError, ValueError):
        return None, (jsonify({"error": "unauthorized"}), 401)

bp = Blueprint("schedule", __name__, url_prefix="/api/schedule")


@bp.route("/engine-input", methods=["GET"])
def get_engine_input():
    """
    GET /api/schedule/engine-input?term_id=1&course_ids=1,2,3
    Returns normalized input for the scheduling engine.
    term_id: optional; omit to use active term.
    course_ids: optional; comma-separated; omit for all courses in term.
    """
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return jsonify({"error": "unauthorized"}), 401

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        return jsonify({"error": "unauthorized"}), 401

    term_id = request.args.get("term_id", type=int)
    course_ids_str = request.args.get("course_ids", "")
    course_ids = None
    if course_ids_str:
        try:
            course_ids = [int(x.strip()) for x in course_ids_str.split(",") if x.strip()]
        except ValueError:
            return jsonify({"error": "invalid course_ids"}), 400

    result = build_engine_input(user_id, term_id=term_id, course_ids=course_ids)
    if "error" in result and result.get("error") == "No term found":
        return jsonify(result), 404
    return jsonify(result), 200


@bp.route("/terms/<int:term_id>/generate-study-times", methods=["POST"])
def generate_study_times_for_term(term_id):
    """
    Generate study times for the given term (scheduling algorithm).
    For dev: test with curl -X POST -H "Authorization: Bearer <token>" <base>/api/schedule/terms/<term_id>/generate-study-times
    """
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return jsonify({"error": "unauthorized"}), 401

    session = SessionLocal()
    try:
        created = generate_study_times(session, term_id)
        session.commit()
        return jsonify({
            "ok": True,
            "created_count": len(created),
            "study_times": [
                {"start_time": st.start_time.isoformat(), "end_time": st.end_time.isoformat()}
                for st in created
            ],
        }), 201
    except ValueError as e:
        session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 404
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@bp.route("/terms/<int:term_id>/study-times", methods=["GET"])
def get_study_times(term_id):
    """Return all study times for a term."""
    user_id, err = _get_user(request)
    if err:
        return err

    conn = _get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT st.id, st.start_time, st.end_time, st.notes,
                      st.is_locked, st.assignment_id, st.course_id,
                      c.course_name
               FROM StudyTimes st
               LEFT JOIN Courses c ON st.course_id = c.id
               WHERE st.term_id = %s
               ORDER BY st.start_time""",
            (term_id,),
        )
        rows = cur.fetchall()
        cur.close()

        study_times = []
        for r in rows:
            study_times.append({
                "id": r["id"],
                "start_time": r["start_time"].isoformat() if r["start_time"] else None,
                "end_time": r["end_time"].isoformat() if r["end_time"] else None,
                "notes": r["notes"],
                "is_locked": bool(r["is_locked"]) if r.get("is_locked") is not None else False,
                "assignment_id": r["assignment_id"],
                "course_id": r["course_id"],
                "course_name": r.get("course_name"),
            })

        return jsonify({"study_times": study_times})
    finally:
        conn.close()
