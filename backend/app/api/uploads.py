"""Upload API: avatar and banner file uploads. Returns URL path for storage."""
import os
import re
import uuid
from pathlib import Path

from flask import Blueprint, jsonify, request, send_from_directory

from app.api.auth import decode_token

bp = Blueprint("uploads", __name__, url_prefix="/api/uploads")

# Allowed image extensions
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_SIZE = 5 * 1024 * 1024  # 5 MB


def _uploads_dir() -> Path:
    """Return uploads base directory. Creates if needed.
    Default /tmp/uploads for production (Render, etc.) where app dir may be read-only.
    Use UPLOADS_DIR env to override. Local docker-compose uses a volume at /app/backend/uploads.
    """
    base = Path(os.getenv("UPLOADS_DIR", "/tmp/uploads"))
    base.mkdir(parents=True, exist_ok=True)
    return base


def _require_user():
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return None
    try:
        return int(payload.get("sub"))
    except (TypeError, ValueError):
        return None


@bp.route("/avatars/<path:filename>", methods=["GET"])
def serve_avatar(filename):
    """Serve uploaded avatar. Public read. Cross-Origin-Resource-Policy for ORB."""
    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", filename):
        return jsonify({"error": "invalid filename"}), 400
    base = _uploads_dir() / "avatars"
    base.mkdir(parents=True, exist_ok=True)
    path = base / filename
    if not path.exists() or not path.is_file():
        return jsonify({"error": "not found"}), 404
    resp = send_from_directory(str(base), filename, max_age=86400)
    resp.headers["Cross-Origin-Resource-Policy"] = "cross-origin"
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


@bp.route("/banners/<path:filename>", methods=["GET"])
def serve_banner(filename):
    """Serve uploaded banner. Public read. CORS headers for ORB."""
    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", filename):
        return jsonify({"error": "invalid filename"}), 400
    base = _uploads_dir() / "banners"
    base.mkdir(parents=True, exist_ok=True)
    path = base / filename
    if not path.exists() or not path.is_file():
        return jsonify({"error": "not found"}), 404
    resp = send_from_directory(str(base), filename, max_age=86400)
    resp.headers["Cross-Origin-Resource-Policy"] = "cross-origin"
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


def _handle_upload(field: str, subdir: str) -> tuple[dict, int]:
    """Handle multipart file upload. Returns (response_dict, status_code)."""
    user_id = _require_user()
    if not user_id:
        return {"error": "unauthorized"}, 401

    if "file" not in (request.files or {}):
        return {"error": "no file provided"}, 400
    file = request.files["file"]
    if not file or not file.filename:
        return {"error": "no file selected"}, 400

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        return {"error": f"invalid file type. Allowed: {', '.join(ALLOWED_EXT)}"}, 400

    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_SIZE:
        return {"error": "file too large (max 5 MB)"}, 400

    base = _uploads_dir() / subdir
    base.mkdir(parents=True, exist_ok=True)
    safe_name = f"{user_id}_{uuid.uuid4().hex[:12]}{ext}"
    path = base / safe_name
    file.save(str(path))

    url_path = f"/api/uploads/{subdir}/{safe_name}"
    return {"url": url_path}, 200


@bp.route("/avatar", methods=["POST"])
def upload_avatar():
    """POST multipart file. Returns { url: '/api/uploads/avatars/...' }."""
    data, status = _handle_upload("file", "avatars")
    return jsonify(data), status


@bp.route("/banner", methods=["POST"])
def upload_banner():
    """POST multipart file. Returns { url: '/api/uploads/banners/...' }."""
    data, status = _handle_upload("file", "banners")
    return jsonify(data), status
