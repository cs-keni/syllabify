"""Integration tests for POST /api/syllabus/parse."""
import io
from unittest.mock import MagicMock, patch

import pytest

from app.main import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture
def mock_db():
    """Mock MySQL connection and cursor for parse endpoint."""
    conn = MagicMock()
    cur = MagicMock()
    cur.lastrowid = 1
    cur.execute = MagicMock()
    conn.cursor.return_value = cur
    conn.commit = MagicMock()
    conn.rollback = MagicMock()
    conn.close = MagicMock()
    return conn


def _jwt_payload():
    return {"sub": "1", "username": "syllabify-client"}


@patch("app.api.syllabus.get_db")
@patch("app.api.syllabus.decode_token")
def test_parse_requires_auth(decode_token, get_db, client):
    decode_token.return_value = None
    res = client.post(
        "/api/syllabus/parse",
        json={"text": "CS 422 Syllabus"},
        content_type="application/json",
    )
    assert res.status_code == 401
    get_db.assert_not_called()


@patch("app.api.syllabus.get_db")
@patch("app.api.syllabus.decode_token")
def test_parse_json_text(decode_token, get_db, client, mock_db):
    decode_token.return_value = _jwt_payload()
    get_db.return_value = mock_db

    res = client.post(
        "/api/syllabus/parse",
        json={"text": "CS 422\nAssignment 1 | 2/15/2025 | 4"},
        content_type="application/json",
        headers={"Authorization": "Bearer fake-token"},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert "course_name" in data
    assert "assignments" in data
    assert isinstance(data["assignments"], list)


@patch("app.api.syllabus.get_db")
@patch("app.api.syllabus.decode_token")
def test_parse_no_file_or_text(decode_token, get_db, client):
    decode_token.return_value = _jwt_payload()
    res = client.post(
        "/api/syllabus/parse",
        json={},
        content_type="application/json",
        headers={"Authorization": "Bearer fake-token"},
    )
    assert res.status_code == 400


@patch("app.api.syllabus.get_db")
@patch("app.api.syllabus.decode_token")
def test_parse_file_upload(decode_token, get_db, client, mock_db):
    decode_token.return_value = _jwt_payload()
    get_db.return_value = mock_db

    res = client.post(
        "/api/syllabus/parse",
        data={"file": (io.BytesIO(b"CS 422\nAssignment 1 | 2/15 | 4"), "syllabus.txt")},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert res.status_code == 200
    out = res.get_json()
    assert "course_name" in out
    assert "assignments" in out
