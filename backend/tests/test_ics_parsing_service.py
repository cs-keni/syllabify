import pytest
from pathlib import Path
from app.services.ics_parsing_service import parse_ics_content, classify_event, fetch_ics_feed, auto_detect_category


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "test_calendar.ics"


@pytest.fixture
def sample_ics():
    return FIXTURE_PATH.read_text()


class TestParseIcsContent:
    def test_returns_list(self, sample_ics):
        events = parse_ics_content(sample_ics)
        assert isinstance(events, list)

    def test_skips_cancelled_events(self, sample_ics):
        events = parse_ics_content(sample_ics)
        titles = [e["title"] for e in events]
        assert "Cancelled Meeting" not in titles

    def test_parses_timed_event(self, sample_ics):
        events = parse_ics_content(sample_ics)
        timed = [e for e in events if e["external_uid"] == "event-timed-001@test"]
        assert len(timed) == 1
        e = timed[0]
        assert e["title"] == "CS 422 Lecture"
        assert e["event_kind"] == "timed"
        assert e["start_time"] is not None
        assert e["end_time"] is not None
        assert e["start_date"] is None
        assert e["original_timezone"] == "America/Los_Angeles"
        assert e["location"] == "Deschutes 100"

    def test_parses_all_day_event(self, sample_ics):
        events = parse_ics_content(sample_ics)
        allday = [e for e in events if e["external_uid"] == "event-allday-001@test"]
        assert len(allday) == 1
        e = allday[0]
        assert e["event_kind"] == "all_day"
        assert e["start_date"] is not None
        assert e["end_date"] is not None
        assert e["start_time"] is None

    def test_parses_deadline_event(self, sample_ics):
        events = parse_ics_content(sample_ics)
        deadline = [e for e in events if e["external_uid"] == "event-deadline-001@test"]
        assert len(deadline) == 1
        e = deadline[0]
        assert e["event_kind"] == "deadline_marker"
        assert e["start_date"] == e["end_date"]

    def test_expands_recurring_events(self, sample_ics):
        events = parse_ics_content(
            sample_ics,
            expand_start="2026-03-10",
            expand_end="2026-04-01",
        )
        recurring = [e for e in events if e["external_uid"] == "event-recurring-001@test"]
        assert len(recurring) >= 3  # ~3-4 Tuesdays between Mar 10 and Apr 1
        for e in recurring:
            assert e["is_recurring_instance"] is True
            assert e["instance_key"] != "base"
            assert e["recurrence_rule"] is not None

    def test_preserves_original_data(self, sample_ics):
        events = parse_ics_content(sample_ics)
        for e in events:
            if not e.get("is_recurring_instance"):
                assert e["original_data"] is not None


class TestClassifyEvent:
    def test_zero_duration_date_is_deadline(self):
        result = classify_event(
            is_date=True,
            start_val="2026-03-18",
            end_val="2026-03-18",
            title="Assignment 3 Due",
            source_category="canvas",
        )
        assert result == "deadline_marker"

    def test_multi_day_date_is_all_day(self):
        result = classify_event(
            is_date=True,
            start_val="2026-03-20",
            end_val="2026-03-22",
            title="Spring Break",
            source_category="personal",
        )
        assert result == "all_day"

    def test_timed_event(self):
        result = classify_event(
            is_date=False,
            start_val="2026-03-15T09:00:00",
            end_val="2026-03-15T10:15:00",
            title="CS 422 Lecture",
            source_category="academic",
        )
        assert result == "timed"

    def test_canvas_due_keyword_is_deadline(self):
        result = classify_event(
            is_date=True,
            start_val="2026-03-18",
            end_val="2026-03-19",
            title="Due: Project 2",
            source_category="canvas",
        )
        assert result == "deadline_marker"


class TestAutoDetectCategory:
    """Test event_category auto-detection from title and source."""

    def test_lecture_keyword(self):
        assert auto_detect_category("CS 422 Lecture", "academic") == "class"

    def test_office_hours_keyword(self):
        assert auto_detect_category("Office Hours - Prof Smith", "academic") == "office_hours"

    def test_exam_keyword(self):
        assert auto_detect_category("Midterm Exam", "academic") == "exam"

    def test_assignment_due(self):
        assert auto_detect_category("Assignment 3 Due", "canvas") == "assignment_deadline"

    def test_fallback_other(self):
        assert auto_detect_category("Random Event", "personal") == "other"
