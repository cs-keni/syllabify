"""
Schedule API: engine input for scheduling teammate.
Returns normalized JSON (courses, meeting_times, work_items, term) per parser-schedule-integration.md.
"""
import os
from datetime import datetime, time, timedelta

from flask import Blueprint, jsonify, request

from app.api.auth import decode_token, get_db
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


def _parse_pref_time(s: str | None, default_h: int, default_m: int) -> time:
    """Parse 'HH:MM' from preferences; return time(default_h, default_m) if invalid."""
    if not s or not isinstance(s, str):
        return time(default_h, default_m)
    s = s.strip()[:5]
    try:
        parts = s.split(":")
        if len(parts) == 2:
            h, m = int(parts[0], 10), int(parts[1], 10)
            if 0 <= h <= 23 and 0 <= m <= 59:
                return time(h, m)
    except (ValueError, TypeError):
        pass
    return time(default_h, default_m)


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
    GET /api/schedule/terms/:term_id/study-times
    Optional: ?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD to filter by date range.
    Returns study time blocks for the term. Without date params, returns all.
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
    use_date_filter = bool(start_date and end_date)

    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        if use_date_filter:
            cur.execute(
                """
                SELECT st.id, st.start_time, st.end_time, st.notes,
                       st.is_locked, st.assignment_id, st.course_id,
                       c.course_name, c.color AS course_color
                FROM StudyTimes st
                JOIN Terms t ON t.id = st.term_id
                LEFT JOIN Courses c ON st.course_id = c.id
                WHERE st.term_id = %s AND t.user_id = %s
                  AND st.start_time < %s AND st.end_time > %s
                ORDER BY st.start_time
                """,
                (term_id, user_id, end_date + " 00:00:00", start_date + " 00:00:00"),
            )
        else:
            cur.execute(
                """
                SELECT st.id, st.start_time, st.end_time, st.notes,
                       st.is_locked, st.assignment_id, st.course_id,
                       c.course_name, c.color AS course_color
                FROM StudyTimes st
                JOIN Terms t ON st.term_id = t.id
                LEFT JOIN Courses c ON st.course_id = c.id
                WHERE st.term_id = %s AND t.user_id = %s
                ORDER BY st.start_time
                """,
                (term_id, user_id),
            )
        rows = cur.fetchall()
        study_times = []
        for r in rows:
            study_times.append({
                "id": r["id"],
                "start_time": r["start_time"].isoformat() if r.get("start_time") else None,
                "end_time": r["end_time"].isoformat() if r.get("end_time") else None,
                "notes": r.get("notes"),
                "is_locked": bool(r["is_locked"]) if r.get("is_locked") is not None else False,
                "assignment_id": r.get("assignment_id"),
                "course_id": r.get("course_id"),
                "course_name": r.get("course_name"),
                "course_color": r.get("course_color"),
            })
        return jsonify({"study_times": study_times}), 200
    finally:
        conn.close()


@bp.route("/study-times/<int:study_time_id>", methods=["DELETE"])
def delete_study_time(study_time_id):
    """DELETE /api/schedule/study-times/:id"""
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return jsonify({"error": "unauthorized"}), 401

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        return jsonify({"error": "unauthorized"}), 401

    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT st.id FROM StudyTimes st
            JOIN Terms t ON t.id = st.term_id
            WHERE st.id = %s AND t.user_id = %s
            """,
            (study_time_id, user_id),
        )
        if not cur.fetchone():
            return jsonify({"error": "Study time not found"}), 404

        cur.execute("DELETE FROM StudyTimes WHERE id = %s", (study_time_id,))
        conn.commit()
        return jsonify({"ok": True}), 200
    finally:
        conn.close()


def _load_user_prefs_for_scheduling(user_id: int) -> dict:
    """Load work_start, work_end, max_hours_per_day from UserPreferences. Returns defaults if missing."""
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT work_start, work_end, max_hours_per_day FROM UserPreferences WHERE user_id = %s",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return {"work_start": "08:00", "work_end": "22:00", "max_hours_per_day": 8}
        return {
            "work_start": row.get("work_start") or "08:00",
            "work_end": row.get("work_end") or "22:00",
            "max_hours_per_day": int(row["max_hours_per_day"]) if row.get("max_hours_per_day") is not None else 8,
        }
    finally:
        conn.close()


@bp.route("/terms/<int:term_id>/generate-study-times", methods=["POST"])
def generate_study_times_for_term(term_id):
    """
    Generate study times for the given term (scheduling algorithm).
    Uses UserPreferences: work_start/work_end = study window, max_hours_per_day = daily cap.
    For dev: test with curl -X POST -H "Authorization: Bearer <token>" <base>/api/schedule/terms/<term_id>/generate-study-times
    """
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return jsonify({"error": "unauthorized"}), 401
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        return jsonify({"error": "unauthorized"}), 401

    prefs = _load_user_prefs_for_scheduling(user_id)
    study_start = _parse_pref_time(prefs["work_start"], 8, 0)
    study_end = _parse_pref_time(prefs["work_end"], 22, 0)
    max_hours = max(1, min(24, prefs["max_hours_per_day"]))

    session = SessionLocal()
    try:
        created = generate_study_times(
            session, term_id,
            study_start=study_start,
            study_end=study_end,
            max_hours_per_day=max_hours,
        )
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


def _parse_datetime(value):
    if isinstance(value, datetime):
        return value
    if value is None:
        raise ValueError("missing datetime value")
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _to_db_datetime(dt: datetime) -> str:
    # Calendar and StudyTime tables store naive UTC-style timestamps.
    return dt.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")


@bp.route("/study-times/<int:study_time_id>", methods=["PATCH"])
def update_study_time(study_time_id):
    """Update a study time block with overlap validation."""
    user_id, err = _get_user(request)
    if err:
        return err

    body = request.get_json(silent=True) or {}
    conn = _get_db()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT st.id, st.start_time, st.end_time, st.term_id
               FROM StudyTimes st
               JOIN Terms t ON st.term_id = t.id
               WHERE st.id = %s AND t.user_id = %s""",
            (study_time_id, user_id),
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "not found"}), 404

        try:
            proposed_start = _parse_datetime(body.get("start_time", row["start_time"]))
            proposed_end = _parse_datetime(body.get("end_time", row["end_time"]))
        except ValueError:
            return jsonify({"error": "invalid datetime format"}), 422

        if proposed_start >= proposed_end:
            return jsonify({"error": "start_time must be before end_time"}), 422

        min_study_minutes = 15
        if (proposed_end - proposed_start) < timedelta(minutes=min_study_minutes):
            return jsonify({
                "error": "duration_too_short",
                "message": f"Study block must be at least {min_study_minutes} minutes",
            }), 422

        start_db = _to_db_datetime(proposed_start)
        end_db = _to_db_datetime(proposed_end)

        cur.execute(
            """SELECT id, title FROM CalendarEvents
               WHERE user_id = %s
                 AND event_kind = 'timed'
                 AND sync_status = 'active'
                 AND start_time < %s
                 AND end_time > %s
               LIMIT 1""",
            (user_id, end_db, start_db),
        )
        conflict_event = cur.fetchone()
        if conflict_event:
            return jsonify(
                {
                    "error": "conflict",
                    "message": f"Overlaps calendar event: {conflict_event['title']}",
                }
            ), 409

        cur.execute(
            """SELECT id FROM StudyTimes
               WHERE term_id = %s
                 AND is_locked = 1
                 AND id != %s
                 AND start_time < %s
                 AND end_time > %s
               LIMIT 1""",
            (row["term_id"], study_time_id, end_db, start_db),
        )
        if cur.fetchone():
            return jsonify(
                {"error": "conflict", "message": "Overlaps another locked study block"}
            ), 409

        updates = []
        params = []
        if "start_time" in body:
            updates.append("start_time = %s")
            params.append(start_db)
        if "end_time" in body:
            updates.append("end_time = %s")
            params.append(end_db)
        if "is_locked" in body:
            updates.append("is_locked = %s")
            params.append(1 if body["is_locked"] else 0)
        if "notes" in body:
            updates.append("notes = %s")
            params.append(body["notes"])

        if not updates:
            return jsonify({"error": "no fields to update"}), 400

        params.append(study_time_id)
        cur.execute(
            f"UPDATE StudyTimes SET {', '.join(updates)} WHERE id = %s",
            tuple(params),
        )
        conn.commit()
        return jsonify({"ok": True}), 200
    finally:
        if cur is not None:
            cur.close()
        conn.close()
