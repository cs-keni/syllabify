"""Integration tests for POST /api/syllabus/parse and /api/courses."""
import io
from unittest.mock import MagicMock, patch

import pytest

from app.main import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def _jwt_payload():
    return {"sub": "1", "username": "syllabify-client"}


auth_headers = {"Authorization": "Bearer fake-token"}


# --- Syllabus parse (no DB write) ---


@patch("app.api.syllabus.decode_token")
def test_parse_requires_auth(decode_token, client):
    decode_token.return_value = None
    res = client.post("/api/syllabus/parse", json={"text": "CS 422"}, headers=auth_headers)
    assert res.status_code == 401


@patch("app.api.syllabus.decode_token")
def test_parse_json_text(decode_token, client):
    decode_token.return_value = _jwt_payload()
    res = client.post(
        "/api/syllabus/parse",
        json={"text": "CS 422\nAssignment 1 | 2/15/2025 | 4"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.get_json()
    assert "course_name" in data
    assert "assignments" in data
    assert isinstance(data["assignments"], list)
    assert "confidence" in data
    assert "score" in data["confidence"]
    assert "label" in data["confidence"]


@patch("app.api.syllabus.decode_token")
def test_parse_no_file_or_text(decode_token, client):
    decode_token.return_value = _jwt_payload()
    res = client.post("/api/syllabus/parse", json={}, headers=auth_headers)
    assert res.status_code == 400


@patch("app.api.syllabus.decode_token")
def test_parse_file_upload(decode_token, client):
    decode_token.return_value = _jwt_payload()
    res = client.post(
        "/api/syllabus/parse",
        data={"file": (io.BytesIO(b"CS 422\nAssignment 1 | 2/15 | 4"), "syllabus.txt")},
        headers=auth_headers,
    )
    assert res.status_code == 200
    out = res.get_json()
    assert "course_name" in out
    assert "assignments" in out


# --- Courses API (term-based: create, list, delete) ---


@patch("app.api.courses.get_db")
@patch("app.api.courses.decode_token")
def test_create_course(decode_token, get_db, client):
    decode_token.return_value = _jwt_payload()
    conn = MagicMock()
    cur = MagicMock()
    cur.lastrowid = 1
    cur.fetchone.return_value = {"id": 1}  # term exists
    conn.cursor.return_value = cur
    get_db.return_value = conn

    res = client.post(
        "/api/terms/1/courses",
        json={"course_name": "CS 422"},
        headers=auth_headers,
    )
    assert res.status_code == 201
    data = res.get_json()
    assert data.get("id") == 1
    assert data.get("course_name") == "CS 422"


@patch("app.api.courses.decode_token")
def test_create_course_requires_auth(decode_token, client):
    decode_token.return_value = None
    res = client.post(
        "/api/terms/1/courses",
        json={"course_name": "CS 422"},
        headers=auth_headers,
    )
    assert res.status_code == 401


@patch("app.api.courses.get_db")
@patch("app.api.courses.decode_token")
def test_list_courses(decode_token, get_db, client):
    decode_token.return_value = _jwt_payload()
    conn = MagicMock()
    cur = MagicMock()
    cur.fetchone.return_value = {"id": 1}  # term exists
    cur.fetchall.return_value = [{"id": 1, "course_name": "CS 422", "assignment_count": 3}]
    conn.cursor.return_value = cur
    get_db.return_value = conn

    res = client.get("/api/terms/1/courses", headers=auth_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert "courses" in data


@patch("app.api.courses.get_db")
@patch("app.api.courses.decode_token")
def test_delete_course(decode_token, get_db, client):
    decode_token.return_value = _jwt_payload()
    conn = MagicMock()
    cur = MagicMock()
    cur.fetchone.return_value = (1,)  # course exists and is owned
    conn.cursor.return_value = cur
    conn.close = MagicMock()
    get_db.return_value = conn

    res = client.delete("/api/courses/1", headers=auth_headers)
    assert res.status_code == 200
