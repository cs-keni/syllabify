"""
Utility functions for working with terms.
Provides mapping between term names and term IDs for syllabus JSON ingestion.
"""

from typing import Optional

from app.main import get_db_connection


def get_term_id_by_name(user_id: int, term_name: str) -> Optional[int]:
    """
    Find term ID by term name for a specific user.

    Args:
        user_id: The user's ID
        term_name: Term name (e.g., "Winter 2025")

    Returns:
        term_id if found, None otherwise

    Example:
        >>> get_term_id_by_name(1, "Winter 2025")
        3
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id FROM Terms WHERE user_id = %s AND term_name = %s LIMIT 1",
            (user_id, term_name),
        )
        result = cur.fetchone()
        return result["id"] if result else None
    finally:
        conn.close()


def get_or_create_term(
    user_id: int, term_name: str, start_date=None, end_date=None
) -> int:
    """
    Get existing term ID or create new term if it doesn't exist.

    Args:
        user_id: The user's ID
        term_name: Term name (e.g., "Winter 2025")
        start_date: Optional start date (defaults to today if creating)
        end_date: Optional end date (defaults to 3 months from start)

    Returns:
        term_id (either existing or newly created)

    Example:
        >>> get_or_create_term(1, "Winter 2025", "2025-01-06", "2025-03-21")
        3
    """
    from datetime import date, timedelta

    # Try to find existing term
    term_id = get_term_id_by_name(user_id, term_name)
    if term_id:
        return term_id

    # Create new term if not found
    if not start_date:
        start_date = date.today()
    if not end_date:
        end_date = date.today() + timedelta(days=90)  # Default 3 months

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Terms "
            "(user_id, term_name, start_date, end_date, is_active) "
            "VALUES (%s, %s, %s, %s, FALSE)",
            (user_id, term_name, start_date, end_date),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def map_syllabus_json_to_db(user_id: int, syllabus_json: dict) -> dict:
    """
    Transform Kenni's syllabus JSON to include term_id for DB insertion.

    Args:
        user_id: The user's ID
        syllabus_json: Kenni's parsed syllabus JSON

    Returns:
        Modified JSON with term_id added to course object

    Example:
        >>> json_in = {"course": {"term": "Winter 2025", ...}}
        >>> json_out = map_syllabus_json_to_db(1, json_in)
        >>> json_out["course"]["term_id"]
        3
    """
    if "course" in syllabus_json and "term" in syllabus_json["course"]:
        term_name = syllabus_json["course"]["term"]

        # Get or create term (you can adjust this based on requirements)
        term_id = get_term_id_by_name(user_id, term_name)

        if not term_id:
            # If term doesn't exist, you have options:
            # Option 1: Auto-create (uncomment below)
            # term_id = get_or_create_term(user_id, term_name)

            # Option 2: Raise error (current behavior)
            raise ValueError(
                f"Term '{term_name}' not found. "
                f"Please create the term first in the Term Management UI."
            )

        # Add term_id to the course object
        syllabus_json["course"]["term_id"] = term_id

    return syllabus_json
