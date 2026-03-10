from datetime import date, datetime
from unittest.mock import MagicMock, patch

from app.services.calendar_export_service import (
    build_ical_feed_for_user,
    get_export_horizon,
    get_or_create_feed_token,
)


def _mock_conn():
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    return conn, cur


def test_get_or_create_feed_token_reuses_existing_token():
    conn, cur = _mock_conn()
    cur.fetchone.return_value = {
        "ical_feed_token": "existing-token",
        "ical_feed_enabled": 0,
    }

    token, enabled = get_or_create_feed_token(conn, 1)
    assert token == "existing-token"
    assert enabled is False
    conn.commit.assert_not_called()


def test_get_or_create_feed_token_generates_unique_token_when_missing():
    conn, cur = _mock_conn()
    cur.fetchone.side_effect = [
        {"ical_feed_token": None, "ical_feed_enabled": 1},
        {"id": 7},  # first generated token collision
        None,  # second token unique
    ]

    with patch(
        "app.services.calendar_export_service._new_feed_token",
        side_effect=["duplicate-token", "fresh-token"],
    ):
        token, enabled = get_or_create_feed_token(conn, 1)

    assert token == "fresh-token"
    assert enabled is True
    conn.commit.assert_called_once()


def test_get_export_horizon_uses_active_term_end_date():
    conn, cur = _mock_conn()
    cur.fetchone.return_value = {"end_date": date(2026, 3, 31)}
    start, end = get_export_horizon(conn, 1, now_utc=datetime(2026, 3, 7, 12, 0, 0))

    assert start == datetime(2026, 2, 21, 0, 0, 0)
    assert end == datetime(2026, 3, 31, 23, 59, 59)


def test_get_export_horizon_falls_back_when_no_active_term():
    conn, cur = _mock_conn()
    cur.fetchone.return_value = None
    start, end = get_export_horizon(conn, 1, now_utc=datetime(2026, 3, 7, 12, 0, 0))

    assert start == datetime(2026, 2, 21, 0, 0, 0)
    assert end == datetime(2026, 7, 5, 23, 59, 59)


def test_build_ical_feed_for_user_uses_exported_rows():
    conn = MagicMock()
    with (
        patch(
            "app.services.calendar_export_service.get_export_horizon",
            return_value=(datetime(2026, 3, 1), datetime(2026, 3, 31)),
        ),
        patch(
            "app.services.calendar_export_service.fetch_eligible_study_times",
            return_value=[
                {
                    "id": 1,
                    "start_time": datetime(2026, 3, 10, 2, 0),
                    "end_time": datetime(2026, 3, 10, 3, 0),
                    "course_name": "CS 422",
                    "assignment_name": None,
                    "is_locked": False,
                    "notes": None,
                }
            ],
        ),
        patch(
            "app.services.calendar_export_service.serialize_study_times_to_ics",
            return_value=b"BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n",
        ) as serializer,
    ):
        out = build_ical_feed_for_user(conn, 1)
    assert out.startswith(b"BEGIN:VCALENDAR")
    serializer.assert_called_once()
