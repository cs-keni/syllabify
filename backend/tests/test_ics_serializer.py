from datetime import datetime, timezone

from icalendar import Calendar

from app.services.ics_serializer import serialize_study_times_to_ics


def _events_from_ics(blob: bytes):
    cal = Calendar.from_ical(blob)
    events = [component for component in cal.walk() if component.name == "VEVENT"]
    return cal, events


def test_empty_schedule_returns_valid_calendar():
    blob = serialize_study_times_to_ics([])
    cal, events = _events_from_ics(blob)
    assert str(cal.get("PRODID")) == "-//Syllabify//Study Plan Export//EN"
    assert str(cal.get("VERSION")) == "2.0"
    assert len(events) == 0


def test_uid_is_stable_across_repeated_exports():
    study_times = [
        {
            "id": 42,
            "start_time": datetime(2026, 3, 10, 2, 0, tzinfo=timezone.utc),
            "end_time": datetime(2026, 3, 10, 3, 30, tzinfo=timezone.utc),
            "course_name": "CS 422",
            "assignment_name": "Project Report",
            "is_locked": True,
            "notes": "Focus on schema",
        }
    ]

    _, events_a = _events_from_ics(serialize_study_times_to_ics(study_times))
    _, events_b = _events_from_ics(serialize_study_times_to_ics(study_times))
    assert len(events_a) == 1
    assert len(events_b) == 1
    assert str(events_a[0].get("UID")) == str(events_b[0].get("UID")) == "studytime-42@syllabify"


def test_modified_time_keeps_uid_and_updates_dtstart():
    before = [
        {
            "id": 99,
            "start_time": datetime(2026, 3, 10, 2, 0),
            "end_time": datetime(2026, 3, 10, 3, 0),
            "course_name": "Math 253",
            "assignment_name": None,
            "is_locked": False,
            "notes": None,
        }
    ]
    after = [
        {
            "id": 99,
            "start_time": datetime(2026, 3, 10, 4, 0),
            "end_time": datetime(2026, 3, 10, 5, 0),
            "course_name": "Math 253",
            "assignment_name": None,
            "is_locked": False,
            "notes": None,
        }
    ]

    _, events_before = _events_from_ics(serialize_study_times_to_ics(before))
    _, events_after = _events_from_ics(serialize_study_times_to_ics(after))

    assert str(events_before[0].get("UID")) == str(events_after[0].get("UID")) == "studytime-99@syllabify"
    assert events_before[0].decoded("DTSTART") != events_after[0].decoded("DTSTART")
