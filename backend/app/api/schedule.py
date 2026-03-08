"""
Schedule API: engine input for scheduling teammate.
Returns normalized JSON (courses, meeting_times, work_items, term) per parser-schedule-integration.md.
"""
from flask import Blueprint, jsonify, request

from app.api.auth import decode_token, get_db
from app.db.session import SessionLocal
from app.services.schedule_input_builder import build_engine_input
from app.services.scheduling_service import generate_study_times

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


@bp.route("/terms/<int:term_id>/study-times", methods=["GET"])
def get_study_times_for_term(term_id):
    """
    GET /api/schedule/terms/:term_id/study-times?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
    Returns study time blocks for the term in the given date range.
    """
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return jsonify({"error": "unauthorized"}), 401

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        return jsonify({"error": "unauthorized"}), 401

    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    if not start_date or not end_date:
        return jsonify({"error": "start_date and end_date query params required (YYYY-MM-DD)"}), 400

    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        # end_date is exclusive (e.g. week 8-14 uses end_date=15)
        cur.execute(
            """
            SELECT st.id, st.start_time, st.end_time, st.notes
            FROM StudyTimes st
            JOIN Terms t ON t.id = st.term_id
            WHERE st.term_id = %s AND t.user_id = %s
              AND st.start_time < %s AND st.end_time > %s
            ORDER BY st.start_time
            """,
            (term_id, user_id, end_date + " 00:00:00", start_date + " 00:00:00"),
        )
        rows = cur.fetchall()
        study_times = []
        for r in rows:
            study_times.append({
                "id": r["id"],
                "start_time": r["start_time"].isoformat() if r.get("start_time") else None,
                "end_time": r["end_time"].isoformat() if r.get("end_time") else None,
                "notes": r.get("notes"),
            })
        return jsonify({"study_times": study_times}), 200
    finally:
        conn.close()


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
