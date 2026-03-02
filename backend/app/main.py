# Flask entry point.
# TODO: Create Flask app, load config (core.config), register blueprints for api.auth,
#       api.syllabus, api.schedule, api.export. Run with FLASK_APP=app.main.
#
# DISCLAIMER: Project structure may change. Functions may be added, removed, or
# modified. This describes the general idea as of the current state.

import os

import mysql.connector
from flask import Flask, jsonify, request
from flask_cors import CORS

from app.api.admin import bp as admin_bp
from app.api.assignments import bp as assignments_bp
from app.api.auth import bp as auth_bp
from app.api.courses import bp as courses_bp
from app.api.schedule import bp as schedule_bp
from app.api.syllabus import bp as syllabus_bp
from app.api.terms import bp as terms_bp
from app.api.users import bp as users_bp

app = Flask(__name__)
# CORS: set FRONTEND_URL on Render to your Vercel URL (e.g. https://syllabify-iota.vercel.app)
_frontend_origins = os.getenv("FRONTEND_URL", "http://localhost:3000").strip()
_frontend_origins = [o.strip() for o in _frontend_origins.split(",") if o.strip()]
CORS(
    app,
    origins=_frontend_origins,
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "OPTIONS", "PUT", "DELETE", "PATCH"],
)


def get_db_connection():
    """Creates and returns a MySQL connection using DB_* environment variables."""
    port = os.getenv("DB_PORT", "3306")
    try:
        port = int(port)
    except (TypeError, ValueError):
        port = 3306
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "mysql"),
        port=port,
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        connection_timeout=15,
    )


def _maintenance_check():
    """Before request: block non-admins when maintenance is on. Skip login, register, maintenance endpoint."""
    if app.testing:
        return None
    from app.api.admin import _is_admin
    from app.api.auth import decode_token
    from app.maintenance import get_maintenance_status

    if request.method == "OPTIONS":
        return None
    path = request.path or ""
    if path in ("/api/maintenance", "/api/settings") and request.method == "GET":
        return None
    if path in ("/api/auth/login", "/api/auth/register"):
        return None
    enabled, _ = get_maintenance_status()
    if not enabled:
        return None
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return jsonify({"error": "maintenance", "message": get_maintenance_status()[1]}), 503
    username = (payload.get("username") or "").strip()
    if _is_admin(username):
        return None
    return jsonify({"error": "maintenance", "message": get_maintenance_status()[1]}), 503


app.before_request(_maintenance_check)


@app.route("/api/maintenance", methods=["GET"])
def get_maintenance():
    """Public endpoint. Returns maintenance status. No auth required."""
    from app.maintenance import get_maintenance_status

    enabled, message = get_maintenance_status()
    return jsonify({"enabled": enabled, "message": message})


@app.route("/api/settings", methods=["GET"])
def get_settings():
    """Public endpoint. Returns registration and announcement. No auth required."""
    from app.admin_settings import get_announcement_banner, get_registration_enabled

    return jsonify({
        "registration_open": get_registration_enabled(),
        "announcement": get_announcement_banner(),
    })


app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(users_bp)
app.register_blueprint(terms_bp)
app.register_blueprint(courses_bp)
app.register_blueprint(assignments_bp)
app.register_blueprint(schedule_bp)
app.register_blueprint(syllabus_bp)


@app.route("/")
def index():
    """Simple health check / root endpoint. Returns a sample string."""
    return "sample index text"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
