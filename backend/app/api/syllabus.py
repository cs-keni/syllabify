"""
Syllabus API: POST /parse for file upload or pasted text.
Returns course_name, assignments, confidence, raw_text.
Parse does NOT persist; use POST /api/courses after review.
"""
from flask import Blueprint, jsonify, request

from app.api.auth import decode_token
from app.services.parsing_service import parse_file, parse_text

bp = Blueprint("syllabus", __name__, url_prefix="/api/syllabus")


@bp.route("/parse", methods=["POST"])
def parse():
    """
    Accept multipart/form-data (file) or application/json ({"text": "..."}).
    Returns { course_name, assignments, confidence?, raw_text? }.
    Does NOT persist to DB; call POST /api/courses after user reviews/confirms.
    """
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return jsonify({"error": "unauthorized"}), 401
    try:
        int(payload.get("sub"))
    except (TypeError, ValueError):
        return jsonify({"error": "unauthorized"}), 401

    text = None
    file = None
    mode = request.args.get("mode", "rule")

    # JSON body: {"text": "..."}
    if request.is_json:
        data = request.get_json() or {}
        text = data.get("text")

    # Multipart: file upload
    if "file" in (request.files or {}):
        file = request.files.get("file")
        if file and file.filename:
            file = file

    if not text and not file:
        return jsonify({"error": "provide file or text"}), 400

    if file and text:
        return jsonify({"error": "provide either file or text, not both"}), 400

    try:
        if file:
            result = parse_file(file, mode=mode)
        else:
            result = parse_text(text or "", mode=mode)
    except Exception as e:
        return jsonify({"error": f"parse failed: {e}"}), 500

    course_name = result.get("course_name") or "Course"
    assignments = result.get("assignments") or []

    # Build response (no DB write; save happens on Confirm)
    resp = {
        "course_name": course_name,
        "assignments": assignments,
    }
    if result.get("confidence"):
        resp["confidence"] = result["confidence"]
    if result.get("raw_text") is not None:
        resp["raw_text"] = result["raw_text"]

    return jsonify(resp), 200
