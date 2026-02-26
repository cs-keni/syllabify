"""Admin endpoints. Requires is_admin."""
from flask import Blueprint, jsonify, request

from app.api.auth import decode_token, get_db

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


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
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, username FROM Users WHERE id = %s AND is_admin = 1", (user_id,))
        row = cur.fetchone()
        return (row["id"], row["username"]) if row else None
    finally:
        conn.close()


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


@bp.route("/users/<int:user_id>/reset-security", methods=["PUT"])
def reset_security(user_id):
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
