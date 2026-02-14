# Terms API: CRUD operations for managing academic terms/semesters.
# Endpoints for listing, creating, updating, deleting, and activating terms.

from datetime import datetime

from flask import Blueprint, jsonify, request

from ..api.auth import decode_token, get_db

bp = Blueprint("terms", __name__, url_prefix="/api/terms")


@bp.route("", methods=["GET"])
def list_terms():
    """List all terms for the authenticated user, ordered by start_date DESC."""
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return jsonify({"error": "unauthorized"}), 401

    user_id = int(payload.get("sub"))
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, term_name, start_date, end_date, is_active, created_at "
            "FROM Terms WHERE user_id = %s ORDER BY start_date DESC",
            (user_id,),
        )
        terms = cur.fetchall()

        # Convert date objects to ISO format strings for JSON
        for term in terms:
            if term.get("start_date"):
                term["start_date"] = term["start_date"].isoformat()
            if term.get("end_date"):
                term["end_date"] = term["end_date"].isoformat()
            if term.get("created_at"):
                term["created_at"] = term["created_at"].isoformat()

        return jsonify({"terms": terms})
    finally:
        conn.close()


@bp.route("", methods=["POST"])
def create_term():
    """Create a new term for the authenticated user."""
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return jsonify({"error": "unauthorized"}), 401

    user_id = int(payload.get("sub"))
    data = request.get_json() or {}

    # Validate required fields
    term_name = (data.get("term_name") or "").strip()
    start_date = data.get("start_date")
    end_date = data.get("end_date")

    if not term_name:
        return jsonify({"error": "term_name is required"}), 400
    if not start_date:
        return jsonify({"error": "start_date is required"}), 400
    if not end_date:
        return jsonify({"error": "end_date is required"}), 400

    # Validate date format and logic
    try:
        start_dt = datetime.fromisoformat(start_date).date()
        end_dt = datetime.fromisoformat(end_date).date()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    if end_dt <= start_dt:
        return jsonify({"error": "end_date must be after start_date"}), 400

    conn = get_db()
    try:
        cur = conn.cursor()

        # Insert new term
        cur.execute(
            "INSERT INTO Terms (user_id, term_name, start_date, end_date, is_active) "
            "VALUES (%s, %s, %s, %s, FALSE)",
            (user_id, term_name, start_dt, end_dt),
        )
        term_id = cur.lastrowid
        conn.commit()

        return (
            jsonify(
                {
                    "id": term_id,
                    "term_name": term_name,
                    "start_date": start_dt.isoformat(),
                    "end_date": end_dt.isoformat(),
                    "is_active": False,
                }
            ),
            201,
        )
    finally:
        conn.close()


@bp.route("/<int:term_id>", methods=["GET"])
def get_term(term_id):
    """Get a single term by ID. Must belong to authenticated user."""
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return jsonify({"error": "unauthorized"}), 401

    user_id = int(payload.get("sub"))
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, term_name, start_date, end_date, is_active, created_at "
            "FROM Terms WHERE id = %s AND user_id = %s",
            (term_id, user_id),
        )
        term = cur.fetchone()

        if not term:
            return jsonify({"error": "Term not found"}), 404

        # Convert dates to ISO format
        if term.get("start_date"):
            term["start_date"] = term["start_date"].isoformat()
        if term.get("end_date"):
            term["end_date"] = term["end_date"].isoformat()
        if term.get("created_at"):
            term["created_at"] = term["created_at"].isoformat()

        return jsonify(term)
    finally:
        conn.close()


@bp.route("/<int:term_id>", methods=["PUT"])
def update_term(term_id):
    """Update an existing term. Must belong to authenticated user."""
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return jsonify({"error": "unauthorized"}), 401

    user_id = int(payload.get("sub"))
    data = request.get_json() or {}

    # Check ownership
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM Terms WHERE id = %s AND user_id = %s", (term_id, user_id)
        )
        if not cur.fetchone():
            return jsonify({"error": "Term not found"}), 404

        # Build update query dynamically
        updates = []
        params = []

        if "term_name" in data:
            term_name = (data["term_name"] or "").strip()
            if not term_name:
                return jsonify({"error": "term_name cannot be empty"}), 400
            updates.append("term_name = %s")
            params.append(term_name)

        if "start_date" in data:
            try:
                start_dt = datetime.fromisoformat(data["start_date"]).date()
                updates.append("start_date = %s")
                params.append(start_dt)
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid start_date format"}), 400

        if "end_date" in data:
            try:
                end_dt = datetime.fromisoformat(data["end_date"]).date()
                updates.append("end_date = %s")
                params.append(end_dt)
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid end_date format"}), 400

        if not updates:
            return jsonify({"error": "No fields to update"}), 400

        # Execute update
        params.append(term_id)
        cur.execute(
            f"UPDATE Terms SET {', '.join(updates)} WHERE id = %s", tuple(params)
        )
        conn.commit()

        # Fetch and return updated term
        cur.execute(
            "SELECT id, term_name, start_date, end_date, is_active FROM Terms WHERE id = %s",
            (term_id,),
        )
        term = cur.fetchone()
        return jsonify(
            {
                "id": term[0],
                "term_name": term[1],
                "start_date": term[2].isoformat(),
                "end_date": term[3].isoformat(),
                "is_active": bool(term[4]),
            }
        )
    finally:
        conn.close()


@bp.route("/<int:term_id>", methods=["DELETE"])
def delete_term(term_id):
    """Delete a term. Must belong to authenticated user. Cascades to courses."""
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return jsonify({"error": "unauthorized"}), 401

    user_id = int(payload.get("sub"))
    conn = get_db()
    try:
        cur = conn.cursor()

        # Check ownership
        cur.execute(
            "SELECT id FROM Terms WHERE id = %s AND user_id = %s", (term_id, user_id)
        )
        if not cur.fetchone():
            return jsonify({"error": "Term not found"}), 404

        # Delete (will cascade to courses via FK)
        cur.execute("DELETE FROM Terms WHERE id = %s", (term_id,))
        conn.commit()

        return jsonify({"message": "Term deleted successfully"}), 200
    finally:
        conn.close()


@bp.route("/<int:term_id>/activate", methods=["POST"])
def activate_term(term_id):
    """Set a term as active. Unsets is_active for all other user's terms."""
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return jsonify({"error": "unauthorized"}), 401

    user_id = int(payload.get("sub"))
    conn = get_db()
    try:
        cur = conn.cursor()

        # Check ownership
        cur.execute(
            "SELECT id FROM Terms WHERE id = %s AND user_id = %s", (term_id, user_id)
        )
        if not cur.fetchone():
            return jsonify({"error": "Term not found"}), 404

        # Unset all user's terms
        cur.execute(
            "UPDATE Terms SET is_active = FALSE WHERE user_id = %s", (user_id,)
        )

        # Set this term as active
        cur.execute("UPDATE Terms SET is_active = TRUE WHERE id = %s", (term_id,))
        conn.commit()

        return jsonify({"message": "Term activated successfully"}), 200
    finally:
        conn.close()
