# Auth routes: login, security setup (one-time), me.
# Client login: syllabify-client / ineedtocutmytoenails422. Token is JWT.
# Security answers stored in UserSecurityAnswers; security_setup_done on Users.
#
# DISCLAIMER: Project structure may change. Functions may be added, removed, or
# modified. This describes the general idea as of the current state.

import os
import jwt
import bcrypt
from flask import Blueprint, request, jsonify

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
DEV_USERNAME = "syllabify-client"
DEV_PASSWORD = "ineedtocutmytoenails422"


def get_db():
    """Returns a MySQL connection using DB_* environment variables."""
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


def hash_password(password):
    """Hashes a plaintext password with bcrypt. Returns the hash as a string."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(password, password_hash):
    """Returns True if the password matches the bcrypt hash; False otherwise."""
    if not password_hash:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def ensure_dev_user(cursor):
    """Ensures the dev user exists in the DB. Creates it if missing. Returns (user_id, password_hash, security_setup_done)."""
    cursor.execute("SELECT id, password_hash, security_setup_done FROM Users WHERE username = %s", (DEV_USERNAME,))
    row = cursor.fetchone()
    if row:
        return row[0], row[1], bool(row[2])
    hashed = hash_password(DEV_PASSWORD)
    cursor.execute(
        "INSERT INTO Users (username, password_hash, security_setup_done) VALUES (%s, %s, FALSE)",
        (DEV_USERNAME, hashed),
    )
    uid = cursor.lastrowid
    return uid, hashed, False


def token_for_user(user_id, username):
    """Creates a JWT token containing user_id and username. Used for auth headers."""
    # JWT spec expects "sub" to be a string; PyJWT raises InvalidSubjectError for int
    return jwt.encode(
        {"sub": str(user_id), "username": username},
        SECRET_KEY,
        algorithm="HS256",
    )


def decode_token(auth_header):
    """Extracts and decodes JWT from 'Authorization: Bearer <token>'. Returns payload dict or None if invalid."""
    import logging
    log = logging.getLogger(__name__)
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:].strip()
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        log.warning("JWT decode failed: token expired")
        return None
    except jwt.InvalidSignatureError:
        log.warning("JWT decode failed: invalid signature (SECRET_KEY mismatch?)")
        return None
    except jwt.InvalidTokenError as e:
        log.warning("JWT decode failed: %s", type(e).__name__)
        return None


@bp.route("/login", methods=["POST"])
def login():
    """Accepts username/password, validates against dev user, returns JWT and security_setup_done."""
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400
    if username != DEV_USERNAME or password != DEV_PASSWORD:
        return jsonify({"error": "invalid credentials"}), 401
    conn = get_db()
    try:
        cur = conn.cursor()
        user_id, _, security_setup_done = ensure_dev_user(cur)
        conn.commit()
        token = token_for_user(user_id, DEV_USERNAME)
        # Ensure token is str for JSON (PyJWT can vary by version)
        token_str = token if isinstance(token, str) else token.decode("utf-8")
        return jsonify({"token": token_str, "username": DEV_USERNAME, "security_setup_done": security_setup_done})
    finally:
        conn.close()


@bp.route("/security-setup", methods=["POST"])
def security_setup():
    """Saves security questions/answers for the current user and marks security_setup_done. Requires JWT."""
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        # Log only whether header was sent (do not log the token)
        import logging
        logging.getLogger(__name__).info(
            "security-setup 401: Authorization header present=%s",
            bool(auth and auth.startswith("Bearer ")),
        )
        return jsonify({"error": "unauthorized"}), 401
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json() or {}
    questions = data.get("questions")
    if not questions or not isinstance(questions, list) or len(questions) < 1:
        return jsonify({"error": "at least one question and answer required"}), 400
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM UserSecurityAnswers WHERE user_id = %s", (user_id,))
        for qa in questions[:5]:
            q = (qa.get("question") or "").strip()
            a = (qa.get("answer") or "").strip()
            if q and a:
                ah = hash_password(a)
                cur.execute(
                    "INSERT INTO UserSecurityAnswers (user_id, question_text, answer_hash) VALUES (%s, %s, %s)",
                    (user_id, q[:500], ah),
                )
        cur.execute("UPDATE Users SET security_setup_done = TRUE WHERE id = %s", (user_id,))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()


@bp.route("/me", methods=["GET"])
def me():
    """Returns current user info (username, security_setup_done) from JWT. Requires valid token."""
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return jsonify({"error": "unauthorized"}), 401
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        return jsonify({"error": "unauthorized"}), 401
    username = payload.get("username", "")
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT security_setup_done FROM Users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        security_setup_done = bool(row[0]) if row else False
        return jsonify({"username": username, "security_setup_done": security_setup_done})
    finally:
        conn.close()
