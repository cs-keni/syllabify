# Auth routes: login, register, security setup, me, change-password, Google OAuth.
# Tokens are short-lived JWTs (HS256). Expiry controlled by JWT_EXPIRY_DAYS env var.
# Security answers stored in UserSecurityAnswers; security_setup_done on Users.
#
# DISCLAIMER: Project structure may change. Functions may be added, removed, or
# modified. This describes the general idea as of the current state.

import os
import re
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from flask import Blueprint, jsonify, request

from app.db.connection import get_db
from app.extensions import limiter

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Google OAuth (optional; requires GOOGLE_CLIENT_ID)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
_JWT_EXPIRY_DAYS = int(os.getenv("JWT_EXPIRY_DAYS", "7"))


def hash_password(password):
    """Hashes a plaintext password with bcrypt. Returns the hash as a string."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(password, password_hash):
    """Returns True if the password matches the bcrypt hash; False otherwise."""
    if not password_hash:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))



def token_for_user(user_id, username):
    """Creates a signed JWT. Expires after JWT_EXPIRY_DAYS (default 7)."""
    # JWT spec expects "sub" to be a string; PyJWT raises InvalidSubjectError for int
    exp = datetime.now(tz=timezone.utc) + timedelta(days=_JWT_EXPIRY_DAYS)
    return jwt.encode(
        {"sub": str(user_id), "username": username, "exp": exp},
        SECRET_KEY,
        algorithm="HS256",
    )


def decode_token(auth_header):
    """Extracts and decodes JWT from 'Authorization: Bearer <token>'. Returns payload
    dict or None if invalid."""
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


def _derive_username_from_email(email):
    """Derive a valid username from email. Handles collisions."""
    if not email or "@" not in email:
        return None
    local = email.split("@")[0].lower()
    # Replace invalid chars (only a-zA-Z0-9_- allowed) with underscore
    username = re.sub(r"[^a-zA-Z0-9_-]", "_", local)
    if not username:
        username = "user"
    # Truncate to 50
    username = username[:50]
    return username


def _ensure_unique_username(cursor, base_username):
    """If base_username exists, append _1, _2, etc. until unique."""
    username = base_username
    suffix = 0
    while True:
        cursor.execute("SELECT id FROM Users WHERE username = %s", (username,))
        if not cursor.fetchone():
            return username
        suffix += 1
        username = f"{base_username}_{suffix}"[:50]


@bp.route("/google", methods=["POST"])
@limiter.limit("5 per minute")
def google_signin():
    """Accept Google ID token, validate, create/link user, return Syllabify JWT."""
    from app.admin_settings import get_registration_enabled
    from app.maintenance import get_maintenance_status

    if not GOOGLE_CLIENT_ID:
        return jsonify({"error": "Google sign-in is not configured"}), 503

    enabled, msg = get_maintenance_status()
    if enabled:
        return jsonify({"error": "maintenance", "message": msg}), 503

    data = request.get_json() or {}
    id_token_str = (data.get("id_token") or data.get("credential") or "").strip()
    if not id_token_str:
        return jsonify({"error": "id_token is required"}), 400

    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token

        idinfo = google_id_token.verify_oauth2_token(
            id_token_str, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Google ID token verification failed: %s", e)
        return jsonify({"error": "invalid Google token"}), 401

    google_id = idinfo.get("sub")
    email = (idinfo.get("email") or "").strip().lower()

    if not google_id:
        return jsonify({"error": "invalid Google token"}), 401

    if not get_registration_enabled():
        # Still allow login for existing users
        pass

    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)

        # 1. Find by google_id (already linked)
        try:
            cur.execute(
                "SELECT id, username, security_setup_done, is_admin FROM Users "
                "WHERE google_id = %s AND (is_disabled = FALSE OR is_disabled IS NULL)",
                (google_id,),
            )
        except Exception as e:
            if "Unknown column 'google_id'" in str(e):
                return jsonify({"error": "Database migration required. Run 011_google_oauth_calendar.sql"}), 503
            raise
        row = cur.fetchone()
        if row:
            user_id = row["id"]
            username = row["username"]
            security_setup_done = True  # Google users skip security setup
            is_admin = bool(row.get("is_admin"))
        else:
            # 2. Find by email (auto-link)
            if email:
                cur.execute(
                    "SELECT id, username, security_setup_done, is_admin FROM Users "
                    "WHERE LOWER(email) = %s AND (is_disabled = FALSE OR is_disabled IS NULL)",
                    (email,),
                )
                row = cur.fetchone()
                if row:
                    user_id = row["id"]
                    username = row["username"]
                    security_setup_done = bool(row.get("security_setup_done"))
                    is_admin = bool(row.get("is_admin"))
                    cur.execute(
                        "UPDATE Users SET google_id = %s WHERE id = %s",
                        (google_id, user_id),
                    )
                    conn.commit()
                else:
                    row = None

            # 3. New user
            if not row:
                if not get_registration_enabled():
                    return jsonify({
                        "error": "registration_closed",
                        "message": "Signups are currently closed. Contact an administrator.",
                    }), 403

                base_username = _derive_username_from_email(email) or "user"
                username = _ensure_unique_username(cur, base_username)

                cur.execute(
                    """INSERT INTO Users (username, email, password_hash, google_id, auth_provider, security_setup_done)
                       VALUES (%s, %s, NULL, %s, 'google', TRUE)""",
                    (username, email or None, google_id),
                )
                user_id = cur.lastrowid
                conn.commit()
                security_setup_done = True
                is_admin = False

        env_admins = set(
            u.strip().lower()
            for u in (os.getenv("ADMIN_USERNAMES") or "").split(",")
            if u.strip()
        )
        is_admin_user = is_admin or (username.strip().lower() in env_admins)

        token = token_for_user(user_id, username)
        token_str = token if isinstance(token, str) else token.decode("utf-8")
        return jsonify({
            "token": token_str,
            "username": username,
            "security_setup_done": security_setup_done,
            "is_admin": is_admin_user,
        })
    finally:
        conn.close()


@bp.route("/register", methods=["POST"])
@limiter.limit("5 per minute")
def register():
    """Create new user. No auto-login."""
    from app.admin_settings import get_registration_enabled
    from app.maintenance import get_maintenance_status

    enabled, msg = get_maintenance_status()
    if enabled:
        return jsonify({"error": "maintenance", "message": msg}), 503

    if not get_registration_enabled():
        return jsonify({
            "error": "registration_closed",
            "message": "Signups are currently closed. Contact an administrator.",
        }), 403

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
            "INSERT INTO Users (username, password_hash, security_setup_done) VALUES (%s, %s, FALSE)",
            (username, hashed),
        )
        user_id = cur.lastrowid
        conn.commit()
        return jsonify(
            {"id": user_id, "username": username, "security_setup_done": False}
        ), 201
    finally:
        conn.close()


@bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute")
def login():
    """Accepts username/password, validates against DB, returns JWT and
    security_setup_done."""
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400

    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(
                "SELECT id, username, password_hash, security_setup_done, is_admin FROM Users "
                "WHERE username = %s AND (is_disabled = FALSE OR is_disabled IS NULL)",
                (username,),
            )
        except Exception as e:
            if "is_disabled" in str(e) and "Unknown column" in str(e):
                cur.execute(
                    "SELECT id, username, password_hash, security_setup_done, is_admin FROM Users "
                    "WHERE username = %s",
                    (username,),
                )
            elif "is_admin" in str(e) and "Unknown column" in str(e):
                cur.execute(
                    "SELECT id, username, password_hash, security_setup_done FROM Users "
                    "WHERE username = %s AND (is_disabled = FALSE OR is_disabled IS NULL)",
                    (username,),
                )
            else:
                raise
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "invalid credentials"}), 401
        if not check_password(password, row.get("password_hash") or ""):
            return jsonify({"error": "invalid credentials"}), 401

        from app.maintenance import get_maintenance_status

        enabled, msg = get_maintenance_status()
        if enabled:
            is_admin = bool(row.get("is_admin")) if row.get("is_admin") is not None else False
            if not is_admin:
                return jsonify({"error": "maintenance", "message": msg}), 503

        user_id = row["id"]
        security_setup_done = bool(row.get("security_setup_done"))
        is_admin = bool(row.get("is_admin")) if row.get("is_admin") is not None else False
        # Also check ADMIN_USERNAMES env for admin designation
        env_admins = (
            os.environ.get("ADMIN_USERNAMES", "").strip().lower().split(",")
            if os.environ.get("ADMIN_USERNAMES")
            else []
        )
        is_admin_user = is_admin or (
            row.get("username", "").strip().lower() in env_admins
        )
        token = token_for_user(user_id, row["username"])
        token_str = token if isinstance(token, str) else token.decode("utf-8")
        return jsonify(
            {
                "token": token_str,
                "username": row["username"],
                "security_setup_done": security_setup_done,
                "is_admin": is_admin_user,
            }
        )
    finally:
        conn.close()


@bp.route("/security-setup", methods=["POST"])
def security_setup():
    """Saves security questions/answers for the current user and marks
    security_setup_done. Requires JWT."""
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
                    "INSERT INTO UserSecurityAnswers (user_id, question_text, "
                    "answer_hash) VALUES (%s, %s, %s)",
                    (user_id, q[:500], ah),
                )
        cur.execute(
            "UPDATE Users SET security_setup_done = TRUE WHERE id = %s", (user_id,)
        )
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()


def _validate_password_strength(password):
    """Returns (ok, error_message). Used for register and change-password."""
    if len(password) < 8:
        return False, "password must be at least 8 characters"
    if not re.search(r"[A-Z]", password):
        return False, "password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return False, "password must contain at least one number"
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]", password):
        return False, "password must contain at least one special character (!@#$%^&* etc.)"
    return True, None


@bp.route("/change-password", methods=["POST"])
def change_password():
    """Change password. Requires JWT and current_password verification."""
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return jsonify({"error": "unauthorized"}), 401
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json() or {}
    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""

    if not current_password:
        return jsonify({"error": "current password is required"}), 400
    if not new_password:
        return jsonify({"error": "new password is required"}), 400

    ok, err = _validate_password_strength(new_password)
    if not ok:
        return jsonify({"error": err}), 400

    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT password_hash FROM Users WHERE id = %s",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "unauthorized"}), 401
        if not check_password(current_password, row.get("password_hash") or ""):
            return jsonify({"error": "current password is incorrect"}), 400

        hashed = hash_password(new_password)
        cur.execute("UPDATE Users SET password_hash = %s WHERE id = %s", (hashed, user_id))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()


@bp.route("/security-questions", methods=["GET"])
def get_security_questions():
    """GET /api/auth/security-questions?username=X
    Returns a user's security question texts (not answers). Used for forgot-password flow."""
    username = (request.args.get("username") or "").strip()
    if not username:
        return jsonify({"error": "username is required"}), 400
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id FROM Users WHERE username = %s", (username,))
        user = cur.fetchone()
        if not user:
            # Return empty to avoid username enumeration
            return jsonify({"questions": []})
        cur.execute(
            "SELECT id, question_text FROM UserSecurityAnswers WHERE user_id = %s LIMIT 5",
            (user["id"],),
        )
        qs = cur.fetchall()
        return jsonify({"questions": [{"id": q["id"], "text": q["question_text"]} for q in qs]})
    finally:
        conn.close()


@bp.route("/verify-security", methods=["POST"])
def verify_security():
    """POST /api/auth/verify-security {username, question_id, answer}
    Verifies security answer. On success returns a 15-min reset token."""
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    question_id = data.get("question_id")
    answer = (data.get("answer") or "").strip()
    if not username or not question_id or not answer:
        return jsonify({"error": "username, question_id, and answer are required"}), 400

    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, password_hash FROM Users WHERE username = %s AND (is_disabled = FALSE OR is_disabled IS NULL)",
            (username,),
        )
        user = cur.fetchone()
        if not user:
            return jsonify({"error": "invalid credentials"}), 401
        cur.execute(
            "SELECT answer_hash FROM UserSecurityAnswers WHERE id = %s AND user_id = %s",
            (question_id, user["id"]),
        )
        row = cur.fetchone()
        if not row or not check_password(answer, row["answer_hash"]):
            return jsonify({"error": "invalid credentials"}), 401

        # Reset token valid for 15 minutes, invalidated when password changes
        exp = datetime.now(tz=timezone.utc) + timedelta(minutes=15)
        # Use last 12 chars of current hash as part of secret so token auto-invalidates on password change
        extra = (user.get("password_hash") or "")[-12:]
        reset_token = jwt.encode(
            {"sub": str(user["id"]), "type": "pwd_reset", "exp": exp},
            SECRET_KEY + extra,
            algorithm="HS256",
        )
        token_str = reset_token if isinstance(reset_token, str) else reset_token.decode("utf-8")
        return jsonify({"reset_token": token_str})
    finally:
        conn.close()


@bp.route("/reset-password", methods=["POST"])
def reset_password():
    """POST /api/auth/reset-password {reset_token, new_password}
    Validates the reset token and updates the user's password."""
    data = request.get_json() or {}
    reset_token = (data.get("reset_token") or "").strip()
    new_password = data.get("new_password") or ""
    if not reset_token or not new_password:
        return jsonify({"error": "reset_token and new_password are required"}), 400

    ok, err = _validate_password_strength(new_password)
    if not ok:
        return jsonify({"error": err}), 400

    # Decode without verifying signature first to get the user id
    try:
        unverified = jwt.decode(reset_token, options={"verify_signature": False})
    except jwt.InvalidTokenError:
        return jsonify({"error": "invalid or expired reset token"}), 401

    if unverified.get("type") != "pwd_reset":
        return jsonify({"error": "invalid or expired reset token"}), 401

    user_id_str = unverified.get("sub")
    if not user_id_str:
        return jsonify({"error": "invalid or expired reset token"}), 401

    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, password_hash FROM Users WHERE id = %s", (int(user_id_str),))
        user = cur.fetchone()
        if not user:
            return jsonify({"error": "invalid or expired reset token"}), 401

        extra = (user.get("password_hash") or "")[-12:]
        try:
            jwt.decode(reset_token, SECRET_KEY + extra, algorithms=["HS256"])
        except jwt.InvalidTokenError:
            return jsonify({"error": "invalid or expired reset token"}), 401

        hashed = hash_password(new_password)
        cur.execute("UPDATE Users SET password_hash = %s WHERE id = %s", (hashed, user["id"]))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()


@bp.route("/demo-login", methods=["POST"])
@limiter.limit("30 per minute")
def demo_login():
    """Log into the shared demo account. Creates it with sample data if it doesn't exist."""
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id FROM Users WHERE username = 'demo'",
        )
        row = cur.fetchone()
        if row:
            user_id = row["id"]
            # Re-seed if data was cleared
            cur.execute("SELECT COUNT(*) AS cnt FROM Terms WHERE user_id = %s", (user_id,))
            if (cur.fetchone() or {}).get("cnt", 0) == 0:
                _seed_demo_data(cur, conn, user_id)
        else:
            cur.execute(
                "INSERT INTO Users (username, password_hash, security_setup_done) VALUES ('demo', NULL, TRUE)"
            )
            user_id = cur.lastrowid
            conn.commit()
            _seed_demo_data(cur, conn, user_id)

        token = token_for_user(user_id, "demo")
        token_str = token if isinstance(token, str) else token.decode("utf-8")
        return jsonify({
            "token": token_str,
            "username": "demo",
            "security_setup_done": True,
            "is_admin": False,
        })
    finally:
        conn.close()


def _seed_demo_data(cur, conn, user_id: int) -> None:
    """Populate a demo user with a realistic sample term, courses, and assignments."""
    # Term: Spring 2025
    cur.execute(
        "INSERT INTO Terms (user_id, name, start_date, end_date, is_active) VALUES (%s, %s, %s, %s, TRUE)",
        (user_id, "Spring 2025", "2025-01-06", "2025-05-16"),
    )
    term_id = cur.lastrowid

    courses = [
        ("CS 422 – Software Engineering",  "#3B82F6", 8),
        ("MATH 341 – Applied Probability", "#10B981", 6),
        ("ENGL 202 – Academic Writing",    "#F59E0B", 4),
    ]
    course_ids = []
    for name, color, hrs in courses:
        cur.execute(
            "INSERT INTO Courses (term_id, course_name, color, study_hours_per_week) VALUES (%s, %s, %s, %s)",
            (term_id, name, color, hrs),
        )
        course_ids.append(cur.lastrowid)

    cs_id, math_id, engl_id = course_ids

    # Meeting times
    meetings = [
        (cs_id,   "MO", "10:00", "11:50", "lecture"),
        (cs_id,   "WE", "10:00", "11:50", "lecture"),
        (math_id, "TU", "13:00", "14:15", "lecture"),
        (math_id, "TH", "13:00", "14:15", "lecture"),
        (engl_id, "FR", "11:00", "12:15", "lecture"),
    ]
    for cid, dow, st, et, mtype in meetings:
        cur.execute(
            "INSERT INTO Meetings (course_id, day_of_week, start_time_str, end_time_str, meeting_type) "
            "VALUES (%s, %s, %s, %s, %s)",
            (cid, dow, st, et, mtype),
        )

    # Assignments
    assignments = [
        # CS 422
        (cs_id, "Homework 1",      "2025-02-14", 3,  "assignment"),
        (cs_id, "Homework 2",      "2025-03-07", 4,  "assignment"),
        (cs_id, "Midterm Exam",    "2025-03-21", 6,  "midterm"),
        (cs_id, "Project Proposal","2025-03-28", 5,  "project"),
        (cs_id, "Homework 3",      "2025-04-11", 4,  "assignment"),
        (cs_id, "Final Project",   "2025-05-09", 20, "project"),
        # MATH 341
        (math_id, "Problem Set 1", "2025-02-07", 3, "assignment"),
        (math_id, "Problem Set 2", "2025-02-21", 3, "assignment"),
        (math_id, "Midterm",       "2025-03-14", 6, "midterm"),
        (math_id, "Problem Set 3", "2025-04-04", 4, "assignment"),
        (math_id, "Final Exam",    "2025-05-16", 6, "final"),
        # ENGL 202
        (engl_id, "Essay 1 Draft", "2025-02-28", 5, "assignment"),
        (engl_id, "Peer Review",   "2025-03-07", 1, "assignment"),
        (engl_id, "Essay 1 Final", "2025-03-21", 3, "assignment"),
        (engl_id, "Essay 2 Draft", "2025-04-11", 5, "assignment"),
        (engl_id, "Essay 2 Final", "2025-04-25", 3, "assignment"),
    ]
    for cid, name, due, hrs, atype in assignments:
        cur.execute(
            "INSERT INTO Assignments (course_id, assignment_name, due_date, hours, type) "
            "VALUES (%s, %s, %s, %s, %s)",
            (cid, name, due, hrs, atype),
        )

    conn.commit()


@bp.route("/me", methods=["GET"])
def me():
    """Returns current user info (username, security_setup_done) from JWT. Requires
    valid token."""
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
            "SELECT username, security_setup_done, is_admin FROM Users WHERE id = %s",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "unauthorized"}), 401
        username = row.get("username") or payload.get("username", "")
        db_admin = bool(row.get("is_admin")) if row.get("is_admin") is not None else False
        env_admins = set(
            u.strip().lower()
            for u in (os.getenv("ADMIN_USERNAMES") or "").split(",")
            if u.strip()
        )
        is_admin_user = db_admin or (username.strip().lower() in env_admins)
        return jsonify({
            "username": username,
            "security_setup_done": bool(row.get("security_setup_done")),
            "is_admin": is_admin_user,
        })
    finally:
        conn.close()
