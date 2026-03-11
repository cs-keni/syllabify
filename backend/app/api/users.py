"""User profile and settings. GET/PUT /api/users/me."""
import re

from flask import Blueprint, jsonify, request

from app.api.auth import decode_token, get_db

bp = Blueprint("users", __name__, url_prefix="/api/users")

EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
ALLOWED_AVATARS = {"red", "green", "blue"}


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
        try:
            cur.execute(
                """SELECT id, username, email, avatar, avatar_url, banner_url, description, security_setup_done
                   FROM Users WHERE id = %s""",
                (user_id,),
            )
        except Exception as e:
            if "unknown column" in str(e).lower():
                cur.execute(
                    "SELECT id, username, email, avatar, security_setup_done FROM Users WHERE id = %s",
                    (user_id,),
                )
            else:
                raise
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "user not found"}), 404
        if row.get("email") is None:
            row["email"] = None
        avatar = row.get("avatar")
        if avatar not in ALLOWED_AVATARS:
            avatar = None
        out = {
            "id": row["id"],
            "username": row["username"],
            "email": row["email"],
            "avatar": avatar,
            "security_setup_done": bool(row.get("security_setup_done")),
        }
        if "avatar_url" in row:
            out["avatar_url"] = (row["avatar_url"] or "").strip() or None
        if "banner_url" in row:
            out["banner_url"] = (row["banner_url"] or "").strip() or None
        if "description" in row:
            out["description"] = (row["description"] or "").strip() or None
        return jsonify(out)
    finally:
        conn.close()


@bp.route("/me", methods=["PUT"])
def put_me():
    """Update current user's profile (email/avatar)."""
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return jsonify({"error": "unauthorized"}), 401
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json() or {}
    has_email = "email" in data
    has_avatar = "avatar" in data
    has_avatar_url = "avatar_url" in data
    has_banner_url = "banner_url" in data
    has_description = "description" in data
    if not any([has_email, has_avatar, has_avatar_url, has_banner_url, has_description]):
        return get_me()
    email = None
    if has_email:
        raw = data.get("email")
        email = (raw or "").strip() or None
        if email is not None:
            if len(email) > 255:
                return jsonify({"error": "email too long"}), 400
            if not EMAIL_REGEX.match(email):
                return jsonify({"error": "invalid email format"}), 400

    avatar = None
    if has_avatar:
        raw_avatar = (data.get("avatar") or "").strip().lower()
        avatar = raw_avatar or None
        if avatar is not None and avatar not in ALLOWED_AVATARS:
            return jsonify({"error": "invalid avatar"}), 400

    def _valid_url(s, max_len=500):
        if not s or not isinstance(s, str):
            return None
        s = s.strip()[:max_len]
        if not s:
            return None
        if s.startswith(("http://", "https://")) and len(s) <= max_len:
            return s
        if s.startswith("/api/uploads/") and len(s) <= max_len:
            return s
        return None

    avatar_url = None
    if has_avatar_url:
        avatar_url = _valid_url(data.get("avatar_url"))
        if data.get("avatar_url") and avatar_url is None:
            return jsonify({"error": "avatar_url must be a valid URL or uploaded image path"}), 400

    banner_url = None
    if has_banner_url:
        banner_url = _valid_url(data.get("banner_url"))
        if data.get("banner_url") and banner_url is None:
            return jsonify({"error": "banner_url must be a valid URL or uploaded image path"}), 400

    description = None
    if has_description:
        description = (data.get("description") or "").strip()[:2000] or None

    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        if has_email and email is not None:
            cur.execute(
                "SELECT id FROM Users WHERE email = %s AND id != %s",
                (email, user_id),
            )
            if cur.fetchone():
                return jsonify({"error": "email already in use"}), 400

        update_clauses = []
        params = []
        if has_email:
            update_clauses.append("email = %s")
            params.append(email)
        if has_avatar:
            update_clauses.append("avatar = %s")
            params.append(avatar)
        if has_avatar_url:
            update_clauses.append("avatar_url = %s")
            params.append(avatar_url)
        if has_banner_url:
            update_clauses.append("banner_url = %s")
            params.append(banner_url)
        if has_description:
            update_clauses.append("description = %s")
            params.append(description)
        params.append(user_id)
        try:
            cur.execute(
                f"UPDATE Users SET {', '.join(update_clauses)} WHERE id = %s",
                tuple(params),
            )
        except Exception as e:
            if "Unknown column" in str(e):
                return jsonify({"error": "Database migration required. Run 014_user_profile_banner_description.sql"}), 503
            raise
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
            "SELECT work_start, work_end, preferred_days, max_hours_per_day, timezone FROM UserPreferences WHERE user_id = %s",
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
                "timezone": None,
            })
        return jsonify({
            "work_start": row["work_start"] or "09:00",
            "work_end": row["work_end"] or "17:00",
            "preferred_days": row["preferred_days"] or "MO,TU,WE,TH,FR",
            "max_hours_per_day": int(row["max_hours_per_day"]) if row["max_hours_per_day"] is not None else 8,
            "timezone": row.get("timezone"),
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
    timezone = (data.get("timezone") or "").strip()[:64] or None

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO UserPreferences (user_id, work_start, work_end, preferred_days, max_hours_per_day, timezone)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE work_start = VALUES(work_start), work_end = VALUES(work_end),
                preferred_days = VALUES(preferred_days), max_hours_per_day = VALUES(max_hours_per_day),
                timezone = VALUES(timezone)
            """,
            (user_id, work_start, work_end, preferred_days, max_hours, timezone),
        )
        conn.commit()
    finally:
        conn.close()

    return get_preferences()
