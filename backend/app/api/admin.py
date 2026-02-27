"""Admin endpoints. Requires is_admin."""
import os

from flask import Blueprint, jsonify, request

from app.api.auth import (
    _validate_password_strength,
    decode_token,
    get_db,
    hash_password,
)
from app.audit import log_admin_action

bp = Blueprint("admin", __name__, url_prefix="/api/admin")

# Bootstrap admins via env: ADMIN_USERNAMES=user1,user2 (always treated as admin)
_ADMIN_USERNAMES = set(
    u.strip().lower()
    for u in (os.getenv("ADMIN_USERNAMES") or "").split(",")
    if u.strip()
)


def _is_admin(username: str) -> bool:
    """True if user is admin (DB is_admin=1 or in ADMIN_USERNAMES)."""
    if not username:
        return False
    un = str(username).strip().lower()
    if un in _ADMIN_USERNAMES:
        return True
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT is_admin FROM Users WHERE LOWER(username) = %s", (un,)
        )
        row = cur.fetchone()
        return bool(row and row.get("is_admin"))
    finally:
        conn.close()


def _get_username(conn, user_id: int) -> str | None:
    """Get username by user id."""
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT username FROM Users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    return row["username"] if row else None


def require_admin():
    """Returns (user_id, username) if admin, else None."""
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return None
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        return None
    username = (payload.get("username") or "").strip()
    return (user_id, username) if _is_admin(username) else None


@bp.route("/users", methods=["GET"])
def list_users():
    """List all users. Admin only."""
    if not require_admin():
        return jsonify({"error": "forbidden"}), 403
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, username, email, security_setup_done, is_admin, is_disabled FROM Users ORDER BY id"
        )
        rows = cur.fetchall()
        users = []
        for r in rows:
            users.append({
                "id": r["id"],
                "username": r["username"],
                "email": r.get("email"),
                "security_setup_done": bool(r.get("security_setup_done")),
                "is_admin": bool(r.get("is_admin")),
                "is_disabled": bool(r.get("is_disabled")),
            })
        return jsonify({"users": users})
    finally:
        conn.close()


@bp.route("/users", methods=["POST"])
def create_user():
    """Create a new user (admin only). For class roster, etc. User should change password on first login."""
    import re

    admin = require_admin()
    if not admin:
        return jsonify({"error": "forbidden"}), 403
    admin_id, admin_username = admin
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username:
        return jsonify({"error": "username is required"}), 400
    if not password:
        return jsonify({"error": "password is required"}), 400
    if len(username) < 3 or len(username) > 50:
        return jsonify({"error": "username must be 3-50 characters"}), 400
    if not re.match(r"^[a-zA-Z0-9_-]+$", username):
        return jsonify({"error": "username may only contain letters, numbers, underscore, and hyphen"}), 400
    ok, err = _validate_password_strength(password)
    if not ok:
        return jsonify({"error": err}), 400

    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id FROM Users WHERE username = %s", (username,))
        if cur.fetchone():
            return jsonify({"error": "username already taken"}), 400

        hashed = hash_password(password)
        cur.execute(
            "INSERT INTO Users (username, password_hash, security_setup_done, is_admin) VALUES (%s, %s, FALSE, FALSE)",
            (username, hashed),
        )
        user_id = cur.lastrowid
        conn.commit()
        log_admin_action(
            admin_id, admin_username, "create_user",
            target_user_id=user_id, target_username=username,
        )
        return jsonify({"id": user_id, "username": username}), 201
    finally:
        conn.close()


@bp.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    """Get user details including term/course/assignment counts. Admin only."""
    if not require_admin():
        return jsonify({"error": "forbidden"}), 403
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, username, email, security_setup_done, is_admin, is_disabled FROM Users WHERE id = %s",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "user not found"}), 404
        user_data = {
            "id": row["id"],
            "username": row["username"],
            "email": row.get("email"),
            "security_setup_done": bool(row.get("security_setup_done")),
            "is_admin": bool(row.get("is_admin")),
            "is_disabled": bool(row.get("is_disabled")),
        }
        # Term, course, assignment counts
        cur.execute("SELECT COUNT(*) as n FROM Terms WHERE user_id = %s", (user_id,))
        user_data["terms_count"] = cur.fetchone()["n"]
        cur.execute(
            "SELECT COUNT(*) as n FROM Courses c JOIN Terms t ON c.term_id = t.id WHERE t.user_id = %s",
            (user_id,),
        )
        user_data["courses_count"] = cur.fetchone()["n"]
        cur.execute(
            "SELECT COUNT(*) as n FROM Assignments a JOIN Courses c ON a.course_id = c.id "
            "JOIN Terms t ON c.term_id = t.id WHERE t.user_id = %s",
            (user_id,),
        )
        user_data["assignments_count"] = cur.fetchone()["n"]
        return jsonify(user_data)
    finally:
        conn.close()


@bp.route("/users/<int:user_id>/disable", methods=["PUT"])
def disable_user(user_id):
    """Set is_disabled for a user. Admin only."""
    admin = require_admin()
    if not admin:
        return jsonify({"error": "forbidden"}), 403
    admin_id, admin_username = admin
    data = request.get_json() or {}
    disabled = data.get("disabled")
    if disabled is None:
        return jsonify({"error": "disabled is required"}), 400
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE Users SET is_disabled = %s WHERE id = %s", (bool(disabled), user_id))
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "user not found"}), 404
        target_username = _get_username(conn, user_id)
        log_admin_action(
            admin_id, admin_username,
            "enable_user" if not disabled else "disable_user",
            target_user_id=user_id, target_username=target_username,
        )
        return jsonify({"ok": True})
    finally:
        conn.close()


@bp.route("/users/<int:user_id>/set-admin", methods=["PUT"])
def set_admin(user_id):
    """Set or remove admin role for a user. Admin only. Cannot demote yourself."""
    admin = require_admin()
    if not admin:
        return jsonify({"error": "forbidden"}), 403
    admin_id, admin_username = admin
    if user_id == admin_id:
        return jsonify({"error": "cannot change your own admin status"}), 400
    data = request.get_json() or {}
    is_admin = data.get("is_admin")
    if is_admin is None:
        return jsonify({"error": "is_admin is required"}), 400
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE Users SET is_admin = %s WHERE id = %s", (bool(is_admin), user_id))
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "user not found"}), 404
        target_username = _get_username(conn, user_id)
        log_admin_action(
            admin_id, admin_username,
            "set_admin" if is_admin else "revoke_admin",
            target_user_id=user_id, target_username=target_username,
            details="granted" if is_admin else "revoked",
        )
        return jsonify({"ok": True, "is_admin": bool(is_admin)})
    finally:
        conn.close()


@bp.route("/users/<int:user_id>/set-password", methods=["PUT"])
def admin_set_password(user_id):
    """Set a user's password (admin only). For account recovery. User should change it on next login."""
    admin = require_admin()
    if not admin:
        return jsonify({"error": "forbidden"}), 403
    admin_id, admin_username = admin
    data = request.get_json() or {}
    new_password = data.get("new_password") or ""
    if not new_password:
        return jsonify({"error": "new_password is required"}), 400
    ok, err = _validate_password_strength(new_password)
    if not ok:
        return jsonify({"error": err}), 400
    conn = get_db()
    try:
        cur = conn.cursor()
        hashed = hash_password(new_password)
        cur.execute("UPDATE Users SET password_hash = %s WHERE id = %s", (hashed, user_id))
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "user not found"}), 404
        target_username = _get_username(conn, user_id)
        log_admin_action(
            admin_id, admin_username, "admin_password_reset",
            target_user_id=user_id, target_username=target_username,
        )
        return jsonify({"ok": True})
    finally:
        conn.close()


@bp.route("/maintenance", methods=["GET"])
def get_maintenance_admin():
    """Get maintenance status. Admin only (or use public GET /api/maintenance)."""
    if not require_admin():
        return jsonify({"error": "forbidden"}), 403
    from app.maintenance import get_maintenance_status

    enabled, message = get_maintenance_status()
    return jsonify({"enabled": enabled, "message": message})


@bp.route("/maintenance", methods=["PUT"])
def put_maintenance():
    """Set maintenance mode. Admin only."""
    admin = require_admin()
    if not admin:
        return jsonify({"error": "forbidden"}), 403
    admin_id, admin_username = admin
    data = request.get_json() or {}
    enabled = data.get("enabled")
    if enabled is None:
        return jsonify({"error": "enabled is required"}), 400
    message = (data.get("message") or "").strip() or "Syllabify is undergoing maintenance. Please try again later."
    from app.maintenance import set_maintenance

    if not set_maintenance(bool(enabled), message[:500]):
        return jsonify({"error": "failed to update maintenance settings"}), 500
    log_admin_action(
        admin_id, admin_username, "set_maintenance",
        details=f"enabled={enabled} message={message[:100]}",
    )
    return jsonify({"ok": True, "enabled": bool(enabled), "message": message})


@bp.route("/settings", methods=["GET"])
def get_admin_settings():
    """Get registration and announcement. Admin only."""
    if not require_admin():
        return jsonify({"error": "forbidden"}), 403
    from app.admin_settings import get_announcement_banner, get_registration_enabled

    return jsonify({
        "registration_enabled": get_registration_enabled(),
        "announcement": get_announcement_banner(),
    })


@bp.route("/settings", methods=["PUT"])
def put_admin_settings():
    """Set registration and/or announcement. Admin only."""
    admin = require_admin()
    if not admin:
        return jsonify({"error": "forbidden"}), 403
    admin_id, admin_username = admin
    from app.admin_settings import (
        get_announcement_banner,
        get_registration_enabled,
        set_announcement_banner,
        set_registration_enabled,
    )

    data = request.get_json() or {}
    changed = []
    if "registration_enabled" in data:
        enabled = bool(data["registration_enabled"])
        if set_registration_enabled(enabled):
            changed.append("registration")
            log_admin_action(
                admin_id, admin_username, "set_registration",
                details=f"enabled={enabled}",
            )
    if "announcement" in data:
        text = (data.get("announcement") or "").strip()
        if set_announcement_banner(text):
            changed.append("announcement")
            log_admin_action(
                admin_id, admin_username, "set_announcement",
                details=text[:100] if text else "cleared",
            )
    return jsonify({
        "ok": True,
        "registration_enabled": get_registration_enabled(),
        "announcement": get_announcement_banner(),
    })


@bp.route("/audit-log", methods=["GET"])
def get_audit_log():
    """Audit log of admin actions. Admin only."""
    if not require_admin():
        return jsonify({"error": "forbidden"}), 403
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = max(0, int(request.args.get("offset", 0)))
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(
                """SELECT id, admin_user_id, admin_username, action, target_user_id,
                          target_username, details, created_at
                   FROM AdminAuditLog
                   ORDER BY created_at DESC
                   LIMIT %s OFFSET %s""",
                (limit, offset),
            )
        except Exception:
            return jsonify({"entries": []})
        rows = cur.fetchall()
        entries = []
        for r in rows:
            entries.append({
                "id": r["id"],
                "admin_user_id": r["admin_user_id"],
                "admin_username": r["admin_username"],
                "action": r["action"],
                "target_user_id": r["target_user_id"],
                "target_username": r["target_username"],
                "details": r.get("details"),
                "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
            })
        return jsonify({"entries": entries})
    finally:
        conn.close()


@bp.route("/stats", methods=["GET"])
def get_stats():
    """System stats for admin dashboard. Admin only."""
    if not require_admin():
        return jsonify({"error": "forbidden"}), 403
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT COUNT(*) as n FROM Users")
        total_users = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) as n FROM Users WHERE is_admin = 1")
        admin_count = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) as n FROM Users WHERE is_disabled = 1")
        disabled_count = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) as n FROM Terms")
        total_terms = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) as n FROM Courses")
        total_courses = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) as n FROM Assignments")
        total_assignments = cur.fetchone()["n"]
        return jsonify({
            "total_users": total_users,
            "admin_count": admin_count,
            "disabled_count": disabled_count,
            "total_terms": total_terms,
            "total_courses": total_courses,
            "total_assignments": total_assignments,
        })
    finally:
        conn.close()


@bp.route("/users/<int:user_id>/reset-security", methods=["PUT"])
def reset_security(user_id):
    """Reset security setup for a user. Admin only."""
    admin = require_admin()
    if not admin:
        return jsonify({"error": "forbidden"}), 403
    admin_id, admin_username = admin
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM UserSecurityAnswers WHERE user_id = %s", (user_id,))
        cur.execute("UPDATE Users SET security_setup_done = FALSE WHERE id = %s", (user_id,))
        n = cur.rowcount
        conn.commit()
        if n == 0:
            return jsonify({"error": "user not found"}), 404
        target_username = _get_username(conn, user_id)
        log_admin_action(
            admin_id, admin_username, "reset_security",
            target_user_id=user_id, target_username=target_username,
        )
        return jsonify({"ok": True})
    finally:
        conn.close()
