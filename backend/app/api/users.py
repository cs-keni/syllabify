"""User profile and settings. GET/PUT /api/users/me."""
import re

from flask import Blueprint, jsonify, request

from app.api.auth import decode_token, get_db

bp = Blueprint("users", __name__, url_prefix="/api/users")

EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@bp.route("/me", methods=["GET"])
def get_me():
    """Return current user's profile."""
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
            "SELECT id, username, email, security_setup_done FROM Users WHERE id = %s",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "user not found"}), 404
        if row.get("email") is None:
            row["email"] = None
        return jsonify({
            "id": row["id"],
            "username": row["username"],
            "email": row["email"],
            "security_setup_done": bool(row.get("security_setup_done")),
        })
    finally:
        conn.close()


@bp.route("/me", methods=["PUT"])
def put_me():
    """Update current user's profile (email)."""
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return jsonify({"error": "unauthorized"}), 401
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json() or {}
    if "email" not in data:
        return get_me()
    raw = data.get("email")
    email = (raw or "").strip() or None
    if email is not None:
        if len(email) > 255:
            return jsonify({"error": "email too long"}), 400
        if not EMAIL_REGEX.match(email):
            return jsonify({"error": "invalid email format"}), 400
        conn = get_db()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT id FROM Users WHERE email = %s AND id != %s",
                (email, user_id),
            )
            if cur.fetchone():
                return jsonify({"error": "email already in use"}), 400
            cur.execute("UPDATE Users SET email = %s WHERE id = %s", (email, user_id))
            conn.commit()
        finally:
            conn.close()
    else:
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE Users SET email = NULL WHERE id = %s", (user_id,))
            conn.commit()
        finally:
            conn.close()

    return get_me()


@bp.route("/me/preferences", methods=["GET"])
def get_preferences():
    """Return user preferences. Create default row if none."""
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
            "SELECT work_start, work_end, preferred_days, max_hours_per_day FROM UserPreferences WHERE user_id = %s",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            cur.execute(
                "INSERT INTO UserPreferences (user_id) VALUES (%s)",
                (user_id,),
            )
            conn.commit()
            return jsonify({
                "work_start": "09:00",
                "work_end": "17:00",
                "preferred_days": "MO,TU,WE,TH,FR",
                "max_hours_per_day": 8,
            })
        return jsonify({
            "work_start": row["work_start"] or "09:00",
            "work_end": row["work_end"] or "17:00",
            "preferred_days": row["preferred_days"] or "MO,TU,WE,TH,FR",
            "max_hours_per_day": int(row["max_hours_per_day"]) if row["max_hours_per_day"] is not None else 8,
        })
    finally:
        conn.close()


@bp.route("/me/preferences", methods=["PUT"])
def put_preferences():
    """Update user preferences."""
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return jsonify({"error": "unauthorized"}), 401
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json() or {}
    work_start = (data.get("work_start") or "09:00").strip()[:5]
    work_end = (data.get("work_end") or "17:00").strip()[:5]
    preferred_days = data.get("preferred_days")
    if isinstance(preferred_days, list):
        preferred_days = ",".join(str(d).strip()[:2].upper() for d in preferred_days if d)
    preferred_days = (preferred_days or "MO,TU,WE,TH,FR").strip()[:50]
    max_hours = data.get("max_hours_per_day")
    try:
        max_hours = max(1, min(24, int(max_hours))) if max_hours is not None else 8
    except (TypeError, ValueError):
        max_hours = 8

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO UserPreferences (user_id, work_start, work_end, preferred_days, max_hours_per_day)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE work_start = VALUES(work_start), work_end = VALUES(work_end),
                preferred_days = VALUES(preferred_days), max_hours_per_day = VALUES(max_hours_per_day)
            """,
            (user_id, work_start, work_end, preferred_days, max_hours),
        )
        conn.commit()
    finally:
        conn.close()

    return get_preferences()
