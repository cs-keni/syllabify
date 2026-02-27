"""Admin endpoints. Requires is_admin."""
import os

from flask import Blueprint, jsonify, request

from app.api.auth import decode_token, get_db, hash_password, _validate_password_strength

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
    if not require_admin():
        return jsonify({"error": "forbidden"}), 403
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
        return jsonify({"ok": True})
    finally:
        conn.close()


@bp.route("/users/<int:user_id>/set-admin", methods=["PUT"])
def set_admin(user_id):
    """Set or remove admin role for a user. Admin only. Cannot demote yourself."""
    admin = require_admin()
    if not admin:
        return jsonify({"error": "forbidden"}), 403
    admin_id, _ = admin
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
        return jsonify({"ok": True, "is_admin": bool(is_admin)})
    finally:
        conn.close()


@bp.route("/users/<int:user_id>/set-password", methods=["PUT"])
def admin_set_password(user_id):
    """Set a user's password (admin only). For account recovery. User should change it on next login."""
    if not require_admin():
        return jsonify({"error": "forbidden"}), 403
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
        return jsonify({"ok": True})
    finally:
        conn.close()


@bp.route("/users/<int:user_id>/reset-security", methods=["PUT"])
    """Reset security setup for a user. Admin only."""
    if not require_admin():
        return jsonify({"error": "forbidden"}), 403
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM UserSecurityAnswers WHERE user_id = %s", (user_id,))
        cur.execute("UPDATE Users SET security_setup_done = FALSE WHERE id = %s", (user_id,))
        n = cur.rowcount
        conn.commit()
        if n == 0:
            return jsonify({"error": "user not found"}), 404
        return jsonify({"ok": True})
    finally:
        conn.close()
