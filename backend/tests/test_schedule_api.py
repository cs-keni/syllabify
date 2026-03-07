from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.main import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture
def auth_token():
    return "fake-token"


@pytest.fixture
def other_auth_token():
    return "other-fake-token"


@pytest.fixture
def sample_study_time():
    return SimpleNamespace(id=101)


@pytest.fixture
def sample_calendar_event():
    return {
        "start_time": "2026-01-05T10:00:00",
        "end_time": "2026-01-05T10:30:00",
    }


def _mock_conn_with_cursor():
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    return conn, cur


@patch("app.api.schedule._get_db")
@patch("app.api.schedule._get_user")
def test_patch_study_time_lock(get_user, get_db, client, auth_token, sample_study_time):
    get_user.return_value = (1, None)
    conn, cur = _mock_conn_with_cursor()
    get_db.return_value = conn
    cur.fetchone.side_effect = [
        {
            "id": sample_study_time.id,
            "start_time": datetime(2026, 1, 5, 9, 0),
            "end_time": datetime(2026, 1, 5, 9, 15),
            "term_id": 7,
        },
        None,
        None,
    ]

    resp = client.patch(
        f"/api/schedule/study-times/{sample_study_time.id}",
        json={"is_locked": True},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True


@patch("app.api.schedule._get_db")
@patch("app.api.schedule._get_user")
def test_patch_study_time_invalid_times(get_user, get_db, client, auth_token, sample_study_time):
    get_user.return_value = (1, None)
    conn, cur = _mock_conn_with_cursor()
    get_db.return_value = conn
    cur.fetchone.return_value = {
        "id": sample_study_time.id,
        "start_time": datetime(2026, 1, 5, 9, 0),
        "end_time": datetime(2026, 1, 5, 9, 15),
        "term_id": 7,
    }

    resp = client.patch(
        f"/api/schedule/study-times/{sample_study_time.id}",
        json={"start_time": "2026-01-05T10:15:00", "end_time": "2026-01-05T10:00:00"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 422


@patch("app.api.schedule._get_db")
@patch("app.api.schedule._get_user")
def test_patch_study_time_overlaps_calendar_event(
    get_user, get_db, client, auth_token, sample_study_time, sample_calendar_event
):
    get_user.return_value = (1, None)
    conn, cur = _mock_conn_with_cursor()
    get_db.return_value = conn
    cur.fetchone.side_effect = [
        {
            "id": sample_study_time.id,
            "start_time": datetime(2026, 1, 5, 9, 0),
            "end_time": datetime(2026, 1, 5, 9, 15),
            "term_id": 7,
        },
        {"id": 55, "title": "Team Meeting"},
    ]

    resp = client.patch(
        f"/api/schedule/study-times/{sample_study_time.id}",
        json={
            "start_time": sample_calendar_event["start_time"],
            "end_time": sample_calendar_event["end_time"],
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 409


@patch("app.api.schedule._get_db")
@patch("app.api.schedule._get_user")
def test_patch_study_time_wrong_user(
    get_user, get_db, client, other_auth_token, sample_study_time
):
    get_user.return_value = (999, None)
    conn, cur = _mock_conn_with_cursor()
    get_db.return_value = conn
    cur.fetchone.return_value = None

    resp = client.patch(
        f"/api/schedule/study-times/{sample_study_time.id}",
        json={"is_locked": True},
        headers={"Authorization": f"Bearer {other_auth_token}"},
    )
    assert resp.status_code == 404
