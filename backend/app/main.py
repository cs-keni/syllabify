# Flask entry point.
# TODO: Create Flask app, load config (core.config), register blueprints for api.auth,
#       api.syllabus, api.schedule, api.export. Run with FLASK_APP=app.main.
#
# DISCLAIMER: Project structure may change. Functions may be added, removed, or
# modified. This describes the general idea as of the current state.

import os

import mysql.connector
from flask import Flask
from flask_cors import CORS

from app.api.auth import bp as auth_bp
from app.api.courses import bp as courses_bp
from app.api.syllabus import bp as syllabus_bp

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

app.register_blueprint(auth_bp)
app.register_blueprint(syllabus_bp)
app.register_blueprint(courses_bp)

@app.route("/")
def index():
    """Simple health check / root endpoint. Returns a sample string."""
    return "sample index text"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
