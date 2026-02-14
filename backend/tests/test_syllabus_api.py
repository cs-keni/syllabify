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


# --- Courses API (save, list, delete) ---


@patch("app.api.courses.get_db")
@patch("app.api.courses.decode_token")
def test_create_course(decode_token, get_db, client):
    decode_token.return_value = _jwt_payload()
    conn = MagicMock()
    cur = MagicMock()
    cur.lastrowid = 1
    conn.cursor.return_value = cur
    get_db.return_value = conn

    res = client.post(
        "/api/courses",
        json={
            "course_name": "CS 422",
            "assignments": [{"name": "A1", "due": "2025-02-15", "hours": 4}],
        },
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
        "/api/courses",
        json={"course_name": "CS 422", "assignments": []},
        headers=auth_headers,
    )
    assert res.status_code == 401


@patch("app.api.courses.get_db")
@patch("app.api.courses.decode_token")
def test_list_courses(decode_token, get_db, client):
    decode_token.return_value = _jwt_payload()
    conn = MagicMock()
    cur = MagicMock()
    cur.fetchall.return_value = [{"id": 1, "name": "CS 422", "assignment_count": 3}]
    conn.cursor.return_value.__enter__ = lambda self: cur
    conn.cursor.return_value.__exit__ = lambda *a: None
    conn.cursor.return_value = MagicMock(return_value=cur)
    conn.close = MagicMock()
    get_db.return_value = conn

    res = client.get("/api/courses", headers=auth_headers)
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
