from unittest.mock import MagicMock, patch

import pytest

from app.main import app
from app.services.ics_serializer import serialize_study_times_to_ics


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def _mock_conn():
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    return conn, cur


@patch("app.api.calendar.get_db")
def test_export_ics_invalid_token_returns_404(get_db, client):
    conn, cur = _mock_conn()
    cur.fetchone.return_value = None
    get_db.return_value = conn

    resp = client.get("/api/calendar/export/invalid-token.ics")
    assert resp.status_code == 404


@patch("app.api.calendar.get_db")
def test_export_ics_disabled_token_inaccessible(get_db, client):
    conn, cur = _mock_conn()
    cur.fetchone.return_value = None
    get_db.return_value = conn

    resp = client.get("/api/calendar/export/disabled-token.ics")
    assert resp.status_code == 404


@patch("app.api.calendar.build_ical_feed_for_user")
@patch("app.api.calendar.get_db")
def test_export_ics_success_returns_calendar_content(get_db, build_ical_feed_for_user, client):
    conn, cur = _mock_conn()
    cur.fetchone.return_value = {"id": 3}
    get_db.return_value = conn
    build_ical_feed_for_user.return_value = b"BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n"

    resp = client.get("/api/calendar/export/good-token.ics")
    assert resp.status_code == 200
    assert "text/calendar" in resp.headers.get("Content-Type", "")
    assert b"BEGIN:VCALENDAR" in resp.data


@patch("app.api.calendar.build_ical_feed_for_user")
@patch("app.api.calendar.get_db")
def test_export_ics_empty_schedule_still_valid_calendar(get_db, build_ical_feed_for_user, client):
    conn, cur = _mock_conn()
    cur.fetchone.return_value = {"id": 3}
    get_db.return_value = conn
    build_ical_feed_for_user.return_value = serialize_study_times_to_ics([])

    resp = client.get("/api/calendar/export/good-token.ics")
    assert resp.status_code == 200
    assert b"BEGIN:VCALENDAR" in resp.data
    assert b"VEVENT" not in resp.data


@patch("app.api.calendar.get_or_create_feed_token")
@patch("app.api.calendar.get_db")
@patch("app.api.calendar._get_user_from_token")
def test_get_export_token_returns_feed_url(get_user_from_token, get_db, get_or_create_feed_token, client):
    get_user_from_token.return_value = (1, None)
    conn, _cur = _mock_conn()
    get_db.return_value = conn
    get_or_create_feed_token.return_value = ("abc123", True)

    resp = client.get(
        "/api/calendar/export/token",
        headers={"Authorization": "Bearer fake-token"},
    )

    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["enabled"] is True
    assert payload["feedUrl"].endswith("/api/calendar/export/abc123.ics")
