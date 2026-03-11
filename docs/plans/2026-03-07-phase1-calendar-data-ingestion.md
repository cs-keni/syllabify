# Phase 1: Calendar Data Ingestion — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the foundation for calendar data intake — support importing from ICS/iCal feed URLs and Google Calendar, parse/normalize/store/display events in an upgraded FullCalendar UI.

**Architecture:** New `CalendarSources` and `CalendarEvents` tables replace the existing `ExternalEvents`/`UserCalendarConnections` tables. A new ICS parsing service handles feed URL fetching and `.ics` parsing. The existing Google Calendar flow is refactored to use the new unified schema. Frontend replaces `SchedulePreview` with FullCalendar (React) and adds a unified import modal with Google + ICS tabs.

**Tech Stack:** Python `icalendar` + `requests` (backend ICS parsing), FullCalendar React (`@fullcalendar/react`, `@fullcalendar/daygrid`, `@fullcalendar/timegrid`, `@fullcalendar/interaction`), existing Flask/MySQL/React stack.

---

## Task 1: Database Migration

**Files:**
- Create: `docker/migrations/012_calendar_sources_events.sql`

**Step 1: Write migration SQL**

```sql
-- 012_calendar_sources_events.sql
-- Phase 1: Unified calendar sources and events tables

-- 1. CalendarSources — tracks all import sources (Google, ICS URL)
CREATE TABLE IF NOT EXISTS CalendarSources (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  source_type VARCHAR(20) NOT NULL DEFAULT 'google',       -- 'google' | 'ics_url'
  source_label VARCHAR(100) NOT NULL,
  feed_url TEXT,
  feed_url_hash CHAR(64),                                   -- SHA-256 for uniqueness
  feed_category VARCHAR(20) DEFAULT 'other',                -- 'canvas' | 'personal' | 'work' | 'academic' | 'other'
  google_calendar_id VARCHAR(255),
  color VARCHAR(7) DEFAULT '#3B82F6',
  is_writable TINYINT(1) DEFAULT 0,
  source_mode VARCHAR(20) DEFAULT 'import_only',            -- 'import_only' | 'two_way'
  is_active TINYINT(1) DEFAULT 1,
  last_synced_at DATETIME NULL,
  sync_error TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,
  UNIQUE KEY uk_user_feed_url (user_id, feed_url_hash),
  UNIQUE KEY uk_user_google_cal (user_id, source_type, google_calendar_id)
);

-- 2. CalendarEvents — unified storage for all imported events
CREATE TABLE IF NOT EXISTS CalendarEvents (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  source_id INT NOT NULL,
  external_uid VARCHAR(500) NOT NULL,
  recurrence_id VARCHAR(100),
  instance_key VARCHAR(255) NOT NULL DEFAULT 'base',        -- 'base' | 'master' | recurrence_id | provider instance id

  title VARCHAR(500) NOT NULL,
  description TEXT,
  location VARCHAR(500),

  start_time DATETIME,
  end_time DATETIME,
  original_timezone VARCHAR(100),

  start_date DATE,
  end_date DATE,

  event_kind VARCHAR(20) NOT NULL DEFAULT 'timed',          -- 'timed' | 'all_day' | 'deadline_marker'
  event_category VARCHAR(30) NOT NULL DEFAULT 'other',      -- 'class' | 'office_hours' | 'exam' | 'assignment_deadline' | 'meeting' | 'blocked_time' | 'personal' | 'work' | 'other'

  sync_status VARCHAR(20) NOT NULL DEFAULT 'active',        -- 'active' | 'cancelled' | 'deleted_at_source' | 'stale'

  recurrence_rule TEXT,
  is_recurring_instance TINYINT(1) DEFAULT 0,

  original_data JSON,

  is_locally_modified TINYINT(1) DEFAULT 0,
  local_title VARCHAR(500),
  local_start_time DATETIME,
  local_end_time DATETIME,
  local_notes TEXT,
  local_modified_at DATETIME,

  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,
  FOREIGN KEY (source_id) REFERENCES CalendarSources(id) ON DELETE CASCADE,
  UNIQUE KEY uk_source_event_instance (source_id, external_uid, instance_key),
  INDEX idx_user_kind (user_id, event_kind),
  INDEX idx_user_dates (user_id, start_time, end_time),
  INDEX idx_sync_status (sync_status)
);

-- 3. Extend StudyTimes for locked/pinned support (Phase 2 prep)
ALTER TABLE StudyTimes
  ADD COLUMN is_locked TINYINT(1) DEFAULT 0,
  ADD COLUMN assignment_id INT NULL,
  ADD COLUMN course_id INT NULL;

-- Note: Not adding FK constraints on assignment_id/course_id here because
-- MySQL requires the referenced column to have an index, and we want
-- ON DELETE SET NULL behavior which we'll handle in application code.
```

**Step 2: Verify migration file is valid**

Run: `cd /Users/leonwong/Desktop/syllabify/syllabify && cat docker/migrations/012_calendar_sources_events.sql | head -5`
Expected: First 5 lines of the migration file.

**Step 3: Commit**

```bash
git add docker/migrations/012_calendar_sources_events.sql
git commit -m "feat: add migration 012 for CalendarSources and CalendarEvents tables"
```

---

## Task 2: SQLAlchemy Models

**Files:**
- Create: `backend/app/models/calendar_source.py`
- Create: `backend/app/models/calendar_event.py`
- Modify: `backend/app/models/study_time.py`

**Step 1: Create CalendarSource model**

```python
# backend/app/models/calendar_source.py
from datetime import datetime
from sqlalchemy import Integer, String, Text, Boolean, DateTime, ForeignKey, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class CalendarSource(Base):
    __tablename__ = "CalendarSources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("Users.id"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, default="google")
    source_label: Mapped[str] = mapped_column(String(100), nullable=False)
    feed_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    feed_url_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    feed_category: Mapped[str] = mapped_column(String(20), nullable=False, default="other")
    google_calendar_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#3B82F6")
    is_writable: Mapped[bool] = mapped_column(Boolean, default=False)
    source_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="import_only")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    events = relationship("CalendarEvent", back_populates="source", cascade="all, delete-orphan")
```

**Step 2: Create CalendarEvent model**

```python
# backend/app/models/calendar_event.py
from datetime import datetime, date
from sqlalchemy import Integer, String, Text, Boolean, DateTime, Date, ForeignKey, TIMESTAMP, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class CalendarEvent(Base):
    __tablename__ = "CalendarEvents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("Users.id"), nullable=False)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("CalendarSources.id"), nullable=False)
    external_uid: Mapped[str] = mapped_column(String(500), nullable=False)
    recurrence_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    instance_key: Mapped[str] = mapped_column(String(255), nullable=False, default="base")

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)

    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    original_timezone: Mapped[str | None] = mapped_column(String(100), nullable=True)

    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    event_kind: Mapped[str] = mapped_column(String(20), nullable=False, default="timed")
    event_category: Mapped[str] = mapped_column(String(30), nullable=False, default="other")

    sync_status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    recurrence_rule: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_recurring_instance: Mapped[bool] = mapped_column(Boolean, default=False)

    original_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    is_locally_modified: Mapped[bool] = mapped_column(Boolean, default=False)
    local_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    local_start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    local_end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    local_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    local_modified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    source = relationship("CalendarSource", back_populates="events")
```

**Step 3: Update StudyTime model — add is_locked, assignment_id, course_id**

Read `backend/app/models/study_time.py` first, then add 3 new fields after the existing `term_id` field:

```python
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    assignment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    course_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

**Step 4: Commit**

```bash
git add backend/app/models/calendar_source.py backend/app/models/calendar_event.py backend/app/models/study_time.py
git commit -m "feat: add CalendarSource and CalendarEvent models, extend StudyTime"
```

---

## Task 3: ICS Parsing Service (TDD)

**Files:**
- Create: `backend/app/services/ics_parsing_service.py`
- Create: `backend/tests/test_ics_parsing_service.py`
- Create: `backend/tests/fixtures/test_calendar.ics` (test fixture)
- Modify: `backend/requirements.txt` (add `icalendar>=5.0.0` and `requests>=2.31.0`)

**Step 1: Add dependencies to requirements.txt**

Add these lines to `backend/requirements.txt`:
```
icalendar>=5.0.0
requests>=2.31.0
```

**Step 2: Create test fixture — a sample ICS file**

```ics
# backend/tests/fixtures/test_calendar.ics
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
CALSCALE:GREGORIAN
BEGIN:VEVENT
UID:event-timed-001@test
DTSTART;TZID=America/Los_Angeles:20260315T090000
DTEND;TZID=America/Los_Angeles:20260315T101500
SUMMARY:CS 422 Lecture
LOCATION:Deschutes 100
DESCRIPTION:Software Methodologies lecture
END:VEVENT
BEGIN:VEVENT
UID:event-allday-001@test
DTSTART;VALUE=DATE:20260320
DTEND;VALUE=DATE:20260321
SUMMARY:Spring Break Starts
END:VEVENT
BEGIN:VEVENT
UID:event-deadline-001@test
DTSTART;VALUE=DATE:20260318
DTEND;VALUE=DATE:20260318
SUMMARY:Assignment 3 Due
DESCRIPTION:Submit on Canvas by 11:59 PM
END:VEVENT
BEGIN:VEVENT
UID:event-recurring-001@test
DTSTART;TZID=America/Los_Angeles:20260310T140000
DTEND;TZID=America/Los_Angeles:20260310T150000
SUMMARY:Office Hours
RRULE:FREQ=WEEKLY;BYDAY=TU;UNTIL=20260401T000000Z
LOCATION:Office 210
END:VEVENT
BEGIN:VEVENT
UID:event-cancelled-001@test
DTSTART;TZID=America/Los_Angeles:20260316T100000
DTEND;TZID=America/Los_Angeles:20260316T110000
SUMMARY:Cancelled Meeting
STATUS:CANCELLED
END:VEVENT
END:VCALENDAR
```

**Step 3: Write failing tests**

```python
# backend/tests/test_ics_parsing_service.py
import pytest
from pathlib import Path
from app.services.ics_parsing_service import parse_ics_content, classify_event, fetch_ics_feed


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
    from app.services.ics_parsing_service import auto_detect_category

    def test_lecture_keyword(self):
        assert self.auto_detect_category("CS 422 Lecture", "academic") == "class"

    def test_office_hours_keyword(self):
        assert self.auto_detect_category("Office Hours - Prof Smith", "academic") == "office_hours"

    def test_exam_keyword(self):
        assert self.auto_detect_category("Midterm Exam", "academic") == "exam"

    def test_assignment_due(self):
        assert self.auto_detect_category("Assignment 3 Due", "canvas") == "assignment_deadline"

    def test_fallback_other(self):
        assert self.auto_detect_category("Random Event", "personal") == "other"
```

**Step 4: Run tests to verify they fail**

Run: `cd /Users/leonwong/Desktop/syllabify/syllabify && docker compose exec backend python -m pytest tests/test_ics_parsing_service.py -v 2>&1 | head -30`

If Docker is not running, run locally:
```bash
cd backend && python -m pytest tests/test_ics_parsing_service.py -v 2>&1 | head -30
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.ics_parsing_service'`

**Step 5: Implement ics_parsing_service.py**

```python
# backend/app/services/ics_parsing_service.py
"""Service for parsing ICS/iCal feeds and normalizing events."""

import hashlib
import re
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

import requests
from icalendar import Calendar

# ── Public API ──────────────────────────────────────────────

def fetch_ics_feed(url: str, timeout: int = 30) -> str:
    """Fetch ICS content from a URL. Returns raw text."""
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Syllabify/1.0"})
    resp.raise_for_status()
    return resp.text


def parse_ics_content(
    ics_text: str,
    expand_start: str | None = None,
    expand_end: str | None = None,
    source_category: str = "other",
) -> list[dict]:
    """Parse ICS text into a list of normalized event dicts.

    Args:
        ics_text: Raw ICS/iCal content.
        expand_start: ISO date string for recurring event expansion window start.
        expand_end: ISO date string for recurring event expansion window end.
        source_category: Feed category for event classification hints.

    Returns:
        List of dicts with keys matching CalendarEvents columns.
    """
    cal = Calendar.from_ical(ics_text)
    events = []

    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        status = str(component.get("STATUS", "")).upper()
        if status == "CANCELLED":
            continue

        uid = str(component.get("UID", ""))
        if not uid:
            continue

        dtstart = component.get("DTSTART")
        dtend = component.get("DTEND")
        if dtstart is None:
            continue

        rrule = component.get("RRULE")
        summary = str(component.get("SUMMARY", ""))
        description = str(component.get("DESCRIPTION", "")) or None
        location = str(component.get("LOCATION", "")) or None

        start_val = dtstart.dt
        end_val = dtend.dt if dtend else None
        is_date = isinstance(start_val, date) and not isinstance(start_val, datetime)

        # Handle missing end
        if end_val is None:
            end_val = start_val + timedelta(hours=1) if not is_date else start_val + timedelta(days=1)

        # Classify event_kind
        event_kind = classify_event(is_date, start_val, end_val, summary, source_category)
        event_category = auto_detect_category(summary, source_category)

        # Build base event dict
        base = _build_event_dict(
            uid=uid,
            title=summary,
            description=description,
            location=location,
            start_val=start_val,
            end_val=end_val,
            is_date=is_date,
            event_kind=event_kind,
            event_category=event_category,
            rrule=str(rrule.to_ical(), "utf-8") if rrule else None,
            component=component,
        )

        # Expand recurring events
        if rrule and expand_start and expand_end:
            expanded = _expand_recurring(
                component, uid, base, expand_start, expand_end, source_category
            )
            events.extend(expanded)
        else:
            events.append(base)

    return events


def classify_event(
    is_date: bool,
    start_val,
    end_val,
    title: str,
    source_category: str,
) -> str:
    """Determine event_kind: 'timed', 'all_day', or 'deadline_marker'."""
    title_lower = title.lower() if title else ""
    deadline_keywords = ["due", "deadline", "submit", "assignment due"]

    if is_date:
        # Convert to date objects for comparison if needed
        s = start_val if isinstance(start_val, date) else start_val.date()
        e = end_val if isinstance(end_val, date) else end_val.date()

        is_single_day = (s == e) or (e - s <= timedelta(days=1))
        has_deadline_keyword = any(kw in title_lower for kw in deadline_keywords)

        if source_category == "canvas" and (is_single_day or has_deadline_keyword):
            return "deadline_marker"
        if is_single_day and has_deadline_keyword:
            return "deadline_marker"
        return "all_day" if not is_single_day else "deadline_marker" if source_category == "canvas" else "all_day"

    return "timed"


def auto_detect_category(title: str, source_category: str) -> str:
    """Auto-detect event_category from title keywords and source."""
    title_lower = title.lower() if title else ""

    patterns = [
        (r"\b(lecture|class|seminar)\b", "class"),
        (r"\boffice\s*hours?\b", "office_hours"),
        (r"\b(exam|midterm|final|quiz|test)\b", "exam"),
        (r"\b(due|deadline|assignment|homework|submit)\b", "assignment_deadline"),
        (r"\b(lab|recitation|section)\b", "class"),
        (r"\b(meeting|standup|sync)\b", "meeting"),
    ]

    for pattern, category in patterns:
        if re.search(pattern, title_lower):
            return category

    return "other"


def hash_feed_url(url: str) -> str:
    """SHA-256 hash of feed URL for unique constraint."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


# ── Internal helpers ────────────────────────────────────────

def _build_event_dict(
    uid, title, description, location, start_val, end_val,
    is_date, event_kind, event_category, rrule, component,
    instance_key="base", is_recurring_instance=False, recurrence_id=None,
) -> dict:
    """Build a normalized event dict from parsed ICS data."""
    tz_name = None
    if not is_date and hasattr(start_val, "tzinfo") and start_val.tzinfo:
        tz_name = str(start_val.tzinfo)
        # icalendar sometimes returns tzinfo objects, normalize name
        if hasattr(start_val.tzinfo, "zone"):
            tz_name = start_val.tzinfo.zone
        elif hasattr(start_val.tzinfo, "key"):
            tz_name = start_val.tzinfo.key

    # Convert timed events to UTC for storage
    start_utc = None
    end_utc = None
    start_date_val = None
    end_date_val = None

    if is_date:
        start_date_val = start_val if isinstance(start_val, date) else start_val.date()
        end_date_val = end_val if isinstance(end_val, date) else end_val.date()
        # For deadline_marker: ensure start_date == end_date
        if event_kind == "deadline_marker":
            end_date_val = start_date_val
    else:
        if isinstance(start_val, datetime):
            start_utc = _to_utc(start_val)
            end_utc = _to_utc(end_val) if isinstance(end_val, datetime) else start_utc + timedelta(hours=1)
        else:
            # Shouldn't happen for non-date events, but handle gracefully
            start_utc = datetime.combine(start_val, datetime.min.time(), tzinfo=ZoneInfo("UTC"))
            end_utc = start_utc + timedelta(hours=1)

    # Serialize original data for debug
    original_data = {}
    try:
        original_data = {
            "uid": uid,
            "summary": title,
            "dtstart": str(start_val),
            "dtend": str(end_val),
            "rrule": rrule,
            "status": str(component.get("STATUS", "")),
        }
    except Exception:
        pass

    return {
        "external_uid": uid,
        "recurrence_id": recurrence_id,
        "instance_key": instance_key,
        "title": title or "(No Title)",
        "description": description,
        "location": location,
        "start_time": start_utc,
        "end_time": end_utc,
        "original_timezone": tz_name,
        "start_date": start_date_val,
        "end_date": end_date_val,
        "event_kind": event_kind,
        "event_category": event_category,
        "recurrence_rule": rrule,
        "is_recurring_instance": is_recurring_instance,
        "original_data": original_data,
        "sync_status": "active",
    }


def _to_utc(dt: datetime) -> datetime:
    """Convert a datetime to UTC. Naive datetimes are assumed UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)


def _expand_recurring(component, uid, base_event, expand_start, expand_end, source_category):
    """Expand recurring events within a date range."""
    from dateutil.rrule import rrulestr

    dtstart = component.get("DTSTART").dt
    rrule_prop = component.get("RRULE")
    if not rrule_prop:
        return [base_event]

    rrule_str = rrule_prop.to_ical().decode("utf-8")
    is_date = isinstance(dtstart, date) and not isinstance(dtstart, datetime)

    # Parse date range
    range_start = datetime.fromisoformat(expand_start)
    range_end = datetime.fromisoformat(expand_end)

    if is_date:
        range_start = range_start.date() if isinstance(range_start, datetime) else range_start
        range_end = range_end.date() if isinstance(range_end, datetime) else range_end
    else:
        if range_start.tzinfo is None:
            range_start = range_start.replace(tzinfo=ZoneInfo("UTC"))
        if range_end.tzinfo is None:
            range_end = range_end.replace(tzinfo=ZoneInfo("UTC"))
        if dtstart.tzinfo is None:
            dtstart = dtstart.replace(tzinfo=ZoneInfo("UTC"))

    try:
        rule = rrulestr(f"DTSTART:{dtstart.strftime('%Y%m%dT%H%M%S')}\nRRULE:{rrule_str}", ignoretz=is_date)
        occurrences = list(rule.between(
            range_start if not is_date else datetime.combine(range_start, datetime.min.time()),
            range_end if not is_date else datetime.combine(range_end, datetime.min.time()),
            inc=True,
        ))
    except Exception:
        return [base_event]

    if not occurrences:
        return [base_event]

    # Calculate event duration from base event
    dtend = component.get("DTEND")
    if dtend:
        duration = dtend.dt - component.get("DTSTART").dt
    else:
        duration = timedelta(hours=1)

    results = []
    for occ in occurrences:
        occ_start = occ.date() if is_date else occ
        occ_end = (occ + duration).date() if is_date else occ + duration
        instance_id = occ.strftime("%Y%m%dT%H%M%S")

        event_kind = classify_event(is_date, occ_start, occ_end, base_event["title"], source_category)
        event_dict = _build_event_dict(
            uid=uid,
            title=base_event["title"],
            description=base_event["description"],
            location=base_event["location"],
            start_val=occ_start,
            end_val=occ_end,
            is_date=is_date,
            event_kind=event_kind,
            event_category=base_event["event_category"],
            rrule=base_event["recurrence_rule"],
            component=component,
            instance_key=instance_id,
            is_recurring_instance=True,
            recurrence_id=instance_id,
        )
        results.append(event_dict)

    return results
```

**Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_ics_parsing_service.py -v`
Expected: All tests PASS.

**Step 7: Commit**

```bash
git add backend/requirements.txt backend/app/services/ics_parsing_service.py backend/tests/test_ics_parsing_service.py backend/tests/fixtures/test_calendar.ics
git commit -m "feat: add ICS parsing service with tests and test fixtures"
```

---

## Task 4: Refactor Backend Calendar API

**Files:**
- Modify: `backend/app/api/calendar.py` — refactor to use CalendarSources/CalendarEvents, add ICS endpoints
- Modify: `backend/app/main.py` — no changes needed (calendar_bp already registered)

**Step 1: Read the current calendar.py (482 lines)**

Read the full file first to understand exact code structure.

**Step 2: Refactor calendar.py**

The refactored file must:
1. Keep all existing Google Calendar endpoints working
2. Migrate Google import/sync to use CalendarSources + CalendarEvents tables
3. Add new ICS feed endpoints:
   - `POST /api/calendar/import-ics` — import from ICS feed URL
   - `POST /api/calendar/sync-source/<source_id>` — re-sync any source
   - `GET /api/calendar/sources` — list user's calendar sources
   - `DELETE /api/calendar/sources/<source_id>` — remove a source
4. Refactor `GET /api/calendar/events` to query CalendarEvents instead of ExternalEvents

Key endpoints to add:

```python
# POST /api/calendar/import-ics
# Body: { url: str, label: str, category: str }
# 1. Validate URL
# 2. fetch_ics_feed(url)
# 3. parse_ics_content(ics_text, source_category=category)
# 4. Create CalendarSource (source_type='ics_url')
# 5. Bulk insert CalendarEvents
# 6. Return { ok: true, source_id, imported_count }

# POST /api/calendar/sync-source/<source_id>
# 1. Load CalendarSource by id (verify user ownership)
# 2. If ics_url: re-fetch and re-parse
# 3. If google: re-fetch from Google API
# 4. Mark existing events as 'stale'
# 5. Upsert fresh events, set matched ones back to 'active'
# 6. Update last_synced_at
# 7. Return { ok: true, synced_count }

# GET /api/calendar/sources
# Returns: { sources: [{ id, source_type, source_label, feed_category, color, is_active, last_synced_at, event_count }] }

# DELETE /api/calendar/sources/<source_id>
# Cascade deletes CalendarEvents for that source

# GET /api/calendar/events (refactored)
# Query CalendarEvents instead of ExternalEvents
# Support filters: source_id, event_kind, start_date, end_date
# Return events with effective title/time (prefer local_* if is_locally_modified)
```

**Step 3: Refactor Google import to use new tables**

In the existing `/api/calendar/import` endpoint:
1. Create/find CalendarSource with source_type='google' for each calendar_id
2. Insert events into CalendarEvents instead of ExternalEvents
3. Map Google event fields to our schema:
   - `event.get('id')` → `external_uid`
   - `instance_key` = 'base' (Google singleEvents=True already expands recurring)
   - Detect `event_kind` from Google event properties (dateTime vs date)
   - Auto-detect `event_category` from title

**Step 4: Run existing tests to ensure nothing breaks**

Run: `cd backend && python -m pytest tests/ -v 2>&1 | tail -20`
Expected: All existing tests still pass.

**Step 5: Commit**

```bash
git add backend/app/api/calendar.py
git commit -m "feat: refactor calendar API to use CalendarSources/CalendarEvents, add ICS import"
```

---

## Task 5: Frontend — Install FullCalendar

**Files:**
- Modify: `frontend/package.json`

**Step 1: Install FullCalendar packages**

```bash
cd /Users/leonwong/Desktop/syllabify/syllabify/frontend
npm install @fullcalendar/react @fullcalendar/core @fullcalendar/daygrid @fullcalendar/timegrid @fullcalendar/interaction @fullcalendar/list
```

**Step 2: Verify installation**

Run: `cd frontend && cat package.json | grep fullcalendar`
Expected: All 6 packages listed in dependencies.

**Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore: install FullCalendar React dependencies"
```

---

## Task 6: Frontend — AppCalendar Component (Replace SchedulePreview)

**Files:**
- Create: `frontend/src/components/AppCalendar.jsx`
- Create: `frontend/src/components/AppCalendar.css` (FullCalendar style overrides)

**Step 1: Create AppCalendar component**

This component wraps FullCalendar and handles:
- Displaying events from CalendarEvents API + StudyTimes
- Week/day/month view switching
- Color coding by source/course
- Deadline markers as distinct badges (not blocks)
- Event click for details

```jsx
// frontend/src/components/AppCalendar.jsx
import { useState, useRef, useCallback } from 'react';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import listPlugin from '@fullcalendar/list';
import './AppCalendar.css';

const EVENT_KIND_STYLES = {
  timed: { display: 'block' },
  all_day: { display: 'block', allDay: true },
  deadline_marker: { display: 'list-item', borderColor: '#EF4444' },
};

const DEFAULT_CATEGORY_COLORS = {
  class: '#3B82F6',
  office_hours: '#8B5CF6',
  exam: '#EF4444',
  assignment_deadline: '#F59E0B',
  meeting: '#6366F1',
  blocked_time: '#6B7280',
  personal: '#10B981',
  work: '#F97316',
  other: '#64748B',
};

export default function AppCalendar({
  calendarEvents = [],
  studyTimes = [],
  onEventClick,
  onDateSelect,
  onEventDrop,
  onEventResize,
}) {
  const calendarRef = useRef(null);
  const [currentView, setCurrentView] = useState('timeGridWeek');

  const transformEvents = useCallback(() => {
    const events = [];

    // Transform calendar events
    for (const evt of calendarEvents) {
      if (evt.sync_status !== 'active') continue;

      const title = evt.is_locally_modified && evt.local_title
        ? evt.local_title : evt.title;

      if (evt.event_kind === 'deadline_marker') {
        events.push({
          id: `cal-${evt.id}`,
          title: `📌 ${title}`,
          start: evt.start_date || evt.start_time,
          allDay: true,
          display: 'list-item',
          backgroundColor: DEFAULT_CATEGORY_COLORS[evt.event_category] || '#F59E0B',
          borderColor: '#EF4444',
          extendedProps: { type: 'calendar_event', data: evt },
          classNames: ['deadline-marker'],
        });
      } else if (evt.event_kind === 'all_day') {
        events.push({
          id: `cal-${evt.id}`,
          title,
          start: evt.start_date,
          end: evt.end_date,
          allDay: true,
          backgroundColor: evt.source_color || DEFAULT_CATEGORY_COLORS[evt.event_category] || '#64748B',
          extendedProps: { type: 'calendar_event', data: evt },
        });
      } else {
        const startTime = evt.is_locally_modified && evt.local_start_time
          ? evt.local_start_time : evt.start_time;
        const endTime = evt.is_locally_modified && evt.local_end_time
          ? evt.local_end_time : evt.end_time;
        events.push({
          id: `cal-${evt.id}`,
          title,
          start: startTime,
          end: endTime,
          backgroundColor: evt.source_color || DEFAULT_CATEGORY_COLORS[evt.event_category] || '#64748B',
          extendedProps: { type: 'calendar_event', data: evt },
        });
      }
    }

    // Transform study times
    for (const st of studyTimes) {
      events.push({
        id: `study-${st.id}`,
        title: st.course_name ? `📚 ${st.course_name}` : '📚 Study',
        start: st.start_time,
        end: st.end_time,
        backgroundColor: st.is_locked ? '#059669' : '#10B981',
        borderColor: st.is_locked ? '#047857' : '#059669',
        extendedProps: { type: 'study_time', data: st },
        classNames: st.is_locked ? ['locked-study'] : [],
        editable: !st.is_locked,
      });
    }

    return events;
  }, [calendarEvents, studyTimes]);

  const handleEventClick = (info) => {
    if (onEventClick) {
      onEventClick(info.event.extendedProps);
    }
  };

  const handleDateSelect = (info) => {
    if (onDateSelect) {
      onDateSelect({ start: info.start, end: info.end, allDay: info.allDay });
    }
  };

  const handleEventDrop = (info) => {
    if (onEventDrop) {
      onEventDrop({
        eventId: info.event.id,
        props: info.event.extendedProps,
        start: info.event.start,
        end: info.event.end,
      });
    }
  };

  const handleEventResize = (info) => {
    if (onEventResize) {
      onEventResize({
        eventId: info.event.id,
        props: info.event.extendedProps,
        start: info.event.start,
        end: info.event.end,
      });
    }
  };

  return (
    <div className="app-calendar-container">
      <FullCalendar
        ref={calendarRef}
        plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin, listPlugin]}
        initialView={currentView}
        headerToolbar={{
          left: 'prev,next today',
          center: 'title',
          right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek',
        }}
        events={transformEvents()}
        editable={true}
        selectable={true}
        selectMirror={true}
        dayMaxEvents={true}
        weekends={true}
        slotMinTime="06:00:00"
        slotMaxTime="24:00:00"
        slotDuration="00:15:00"
        slotLabelInterval="01:00:00"
        allDaySlot={true}
        nowIndicator={true}
        eventClick={handleEventClick}
        select={handleDateSelect}
        eventDrop={handleEventDrop}
        eventResize={handleEventResize}
        viewDidMount={(info) => setCurrentView(info.view.type)}
        height="auto"
        stickyHeaderDates={true}
        eventTimeFormat={{
          hour: 'numeric',
          minute: '2-digit',
          meridiem: 'short',
        }}
      />
    </div>
  );
}
```

**Step 2: Create AppCalendar.css for custom styling**

```css
/* frontend/src/components/AppCalendar.css */

.app-calendar-container {
  @apply bg-white dark:bg-gray-800 rounded-lg shadow p-4;
}

/* FullCalendar theme overrides */
.app-calendar-container .fc {
  --fc-border-color: #e5e7eb;
  --fc-today-bg-color: rgba(59, 130, 246, 0.05);
  --fc-event-border-color: transparent;
  --fc-now-indicator-color: #EF4444;
  font-family: inherit;
}

/* Dark mode */
.dark .app-calendar-container .fc {
  --fc-border-color: #374151;
  --fc-today-bg-color: rgba(59, 130, 246, 0.1);
  --fc-page-bg-color: #1f2937;
  --fc-neutral-bg-color: #374151;
  color: #f3f4f6;
}

/* Header toolbar styling */
.app-calendar-container .fc .fc-toolbar-title {
  @apply text-lg font-semibold;
}

.app-calendar-container .fc .fc-button {
  @apply text-sm font-medium rounded px-3 py-1.5;
}

.app-calendar-container .fc .fc-button-primary {
  @apply bg-blue-600 border-blue-600;
}

.app-calendar-container .fc .fc-button-primary:hover {
  @apply bg-blue-700;
}

.app-calendar-container .fc .fc-button-primary:not(:disabled).fc-button-active {
  @apply bg-blue-800;
}

/* Event styling */
.app-calendar-container .fc-event {
  @apply rounded px-1.5 py-0.5 text-xs font-medium cursor-pointer;
  border-width: 0;
  border-left-width: 3px;
}

/* Deadline marker styling */
.app-calendar-container .deadline-marker {
  @apply font-bold;
  border-left-width: 3px;
  border-left-color: #EF4444 !important;
  background-color: #FEF2F2 !important;
  color: #991B1B !important;
}

.dark .app-calendar-container .deadline-marker {
  background-color: rgba(239, 68, 68, 0.15) !important;
  color: #FCA5A5 !important;
}

/* Locked study block styling */
.app-calendar-container .locked-study {
  background-image: repeating-linear-gradient(
    45deg,
    transparent,
    transparent 3px,
    rgba(255, 255, 255, 0.1) 3px,
    rgba(255, 255, 255, 0.1) 6px
  );
}

/* Slot styling */
.app-calendar-container .fc-timegrid-slot {
  height: 1.5rem;
}

.app-calendar-container .fc-timegrid-slot-label {
  @apply text-xs text-gray-500;
}
```

**Step 3: Commit**

```bash
git add frontend/src/components/AppCalendar.jsx frontend/src/components/AppCalendar.css
git commit -m "feat: add AppCalendar component with FullCalendar integration"
```

---

## Task 7: Frontend — Unified Import Modal

**Files:**
- Create: `frontend/src/components/UnifiedImportModal.jsx` (replaces CalendarImportModal)

**Step 1: Create UnifiedImportModal with tabs**

The modal has two tabs:
1. Google Calendar — same flow as current CalendarImportModal
2. ICS Feed URL — new form: URL input, label, category dropdown

```jsx
// frontend/src/components/UnifiedImportModal.jsx
import { useState, useEffect } from 'react';

const CATEGORIES = [
  { value: 'canvas', label: 'Canvas Calendar' },
  { value: 'academic', label: 'Academic / University' },
  { value: 'personal', label: 'Personal' },
  { value: 'work', label: 'Work' },
  { value: 'other', label: 'Other' },
];

export default function UnifiedImportModal({
  onClose,
  onImportGoogle,
  onImportIcs,
  token,
  getCalendarList,
  calendarConnected,
  activeTerm,
}) {
  const [activeTab, setActiveTab] = useState(calendarConnected ? 'google' : 'ics');

  // ── Google Calendar tab state ──
  const [calendars, setCalendars] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [loadingCals, setLoadingCals] = useState(false);

  // ── ICS tab state ──
  const [icsUrl, setIcsUrl] = useState('');
  const [icsLabel, setIcsLabel] = useState('');
  const [icsCategory, setIcsCategory] = useState('other');

  const [importing, setImporting] = useState(false);
  const [error, setError] = useState('');

  // Load Google calendars when tab switches to google
  useEffect(() => {
    if (activeTab === 'google' && calendarConnected && calendars.length === 0) {
      setLoadingCals(true);
      getCalendarList(token)
        .then((data) => {
          setCalendars(data.calendars || []);
          const primary = data.calendars?.find((c) => c.primary);
          if (primary) setSelected(new Set([primary.id]));
        })
        .catch(() => setError('Failed to load calendars'))
        .finally(() => setLoadingCals(false));
    }
  }, [activeTab, calendarConnected, token]);

  // Set date defaults from active term
  useEffect(() => {
    if (activeTerm?.start_date && activeTerm?.end_date) {
      setStartDate(activeTerm.start_date);
      setEndDate(activeTerm.end_date);
    } else {
      const now = new Date();
      setStartDate(now.toISOString().slice(0, 10));
      const future = new Date(now);
      future.setMonth(future.getMonth() + 3);
      setEndDate(future.toISOString().slice(0, 10));
    }
  }, [activeTerm]);

  const toggleCalendar = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const handleGoogleImport = async () => {
    if (selected.size === 0) return setError('Select at least one calendar');
    if (!startDate || !endDate) return setError('Select a date range');
    setImporting(true);
    setError('');
    try {
      await onImportGoogle({
        calendar_ids: Array.from(selected),
        start_date: startDate,
        end_date: endDate,
      });
      onClose();
    } catch (e) {
      setError(e.message || 'Import failed');
    } finally {
      setImporting(false);
    }
  };

  const handleIcsImport = async () => {
    if (!icsUrl.trim()) return setError('Enter a feed URL');
    if (!icsLabel.trim()) return setError('Enter a label for this calendar');
    setImporting(true);
    setError('');
    try {
      await onImportIcs({
        url: icsUrl.trim(),
        label: icsLabel.trim(),
        category: icsCategory,
      });
      onClose();
    } catch (e) {
      setError(e.message || 'Import failed');
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-40 bg-black/40 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="px-6 pt-5 pb-3">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Import Calendar
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Import events from Google Calendar or an ICS/iCal feed URL.
          </p>
        </div>

        {/* Tabs */}
        <div className="px-6 flex border-b border-gray-200 dark:border-gray-700">
          <button
            onClick={() => { setActiveTab('google'); setError(''); }}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
              activeTab === 'google'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Google Calendar
          </button>
          <button
            onClick={() => { setActiveTab('ics'); setError(''); }}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
              activeTab === 'ics'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            ICS / iCal Feed
          </button>
        </div>

        {/* Tab Content */}
        <div className="px-6 py-4">
          {activeTab === 'google' && (
            <div className="space-y-4">
              {!calendarConnected ? (
                <p className="text-sm text-gray-500">
                  Connect your Google account first from the Schedule page.
                </p>
              ) : loadingCals ? (
                <p className="text-sm text-gray-500">Loading calendars...</p>
              ) : (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Select calendars
                    </label>
                    <div className="max-h-40 overflow-y-auto border rounded-lg p-2 space-y-1 dark:border-gray-600">
                      {calendars.map((cal) => (
                        <label key={cal.id} className="flex items-center gap-2 p-1.5 rounded hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={selected.has(cal.id)}
                            onChange={() => toggleCalendar(cal.id)}
                            className="rounded text-blue-600"
                          />
                          <span className="text-sm text-gray-800 dark:text-gray-200 truncate">
                            {cal.summary} {cal.primary && '(Primary)'}
                          </span>
                        </label>
                      ))}
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Start</label>
                      <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)}
                        className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">End</label>
                      <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)}
                        className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm" />
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {activeTab === 'ics' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Feed URL
                </label>
                <input
                  type="url"
                  value={icsUrl}
                  onChange={(e) => setIcsUrl(e.target.value)}
                  placeholder="https://example.com/calendar.ics"
                  className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
                />
                <p className="mt-1 text-xs text-gray-400">
                  Paste an ICS/iCal feed URL (e.g. Canvas Calendar Feed).
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Label
                </label>
                <input
                  type="text"
                  value={icsLabel}
                  onChange={(e) => setIcsLabel(e.target.value)}
                  placeholder="My Canvas Calendar"
                  className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Category
                </label>
                <select
                  value={icsCategory}
                  onChange={(e) => setIcsCategory(e.target.value)}
                  className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
                >
                  {CATEGORIES.map((c) => (
                    <option key={c.value} value={c.value}>{c.label}</option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <p className="mt-3 text-sm text-red-600 dark:text-red-400">{error}</p>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
          >
            Cancel
          </button>
          <button
            onClick={activeTab === 'google' ? handleGoogleImport : handleIcsImport}
            disabled={importing || (activeTab === 'google' && !calendarConnected)}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {importing ? 'Importing...' : 'Import'}
          </button>
        </div>
      </div>
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/UnifiedImportModal.jsx
git commit -m "feat: add UnifiedImportModal with Google Calendar and ICS tabs"
```

---

## Task 8: Frontend — API Client Updates

**Files:**
- Modify: `frontend/src/api/client.js`

**Step 1: Read client.js to find exact insertion point**

Read the file, locate the calendar methods section (around lines 710-796).

**Step 2: Add new API methods after existing calendar methods**

Insert these new methods before the default export:

```javascript
// ── Calendar Sources ──

export async function getCalendarSources(token) {
  const res = await apiFetch(`${BASE}/api/calendar/sources`, {
    headers: headers(true, token),
  });
  return res.json();
}

export async function importIcsFeed(token, { url, label, category }) {
  const res = await apiFetch(`${BASE}/api/calendar/import-ics`, {
    method: 'POST',
    headers: headers(true, token),
    body: JSON.stringify({ url, label, category }),
  });
  return res.json();
}

export async function syncSource(token, sourceId) {
  const res = await apiFetch(`${BASE}/api/calendar/sync-source/${sourceId}`, {
    method: 'POST',
    headers: headers(true, token),
  });
  return res.json();
}

export async function deleteCalendarSource(token, sourceId) {
  const res = await apiFetch(`${BASE}/api/calendar/sources/${sourceId}`, {
    method: 'DELETE',
    headers: headers(true, token),
  });
  return res.json();
}

export async function getStudyTimes(token, termId) {
  const res = await apiFetch(`${BASE}/api/schedule/terms/${termId}/study-times`, {
    headers: headers(true, token),
  });
  return res.json();
}
```

Also add these to the default export object at the end of the file.

**Step 3: Commit**

```bash
git add frontend/src/api/client.js
git commit -m "feat: add API client methods for calendar sources, ICS import, study times"
```

---

## Task 9: Frontend — Rewire Schedule Page

**Files:**
- Modify: `frontend/src/pages/Schedule.jsx`

**Step 1: Read current Schedule.jsx**

Read the full file to understand current structure.

**Step 2: Rewrite Schedule.jsx**

Replace the SchedulePreview with AppCalendar, wire up UnifiedImportModal, fetch real events:

Key changes:
1. Import `AppCalendar` instead of `SchedulePreview`
2. Import `UnifiedImportModal` instead of `CalendarImportModal`
3. Fetch calendar events via `api.getCalendarEvents(token, { start_date, end_date })`
4. Fetch study times via `api.getStudyTimes(token, termId)`
5. Fetch calendar sources via `api.getCalendarSources(token)`
6. Pass real data to `AppCalendar`
7. Add "Import Calendar" button that opens `UnifiedImportModal`
8. Add "iCal Export" placeholder button (disabled, with tooltip "Coming soon")
9. Add sources list sidebar showing connected sources with sync/delete actions

The page layout should be:
```
┌─────────────────────────────────────────────┐
│ Schedule                                     │
│ [Generate Study Times] [Import Calendar]     │
│ [iCal Export (coming soon)]                  │
├──────────────────────────┬──────────────────┤
│                          │ Sources          │
│   AppCalendar            │ • Google Cal ↻   │
│   (FullCalendar)         │ • Canvas Feed ↻  │
│                          │ + Add Source      │
│                          │                  │
└──────────────────────────┴──────────────────┘
```

**Step 3: Commit**

```bash
git add frontend/src/pages/Schedule.jsx
git commit -m "feat: rewire Schedule page with AppCalendar, unified import, real data"
```

---

## Task 10: Backend — GET StudyTimes Endpoint

**Files:**
- Modify: `backend/app/api/schedule.py`

**Step 1: Read current schedule.py**

**Step 2: Add GET endpoint for study times**

```python
@schedule_bp.route("/terms/<int:term_id>/study-times", methods=["GET"])
def get_study_times(term_id):
    """Return all study times for a term."""
    user_id, err = _get_user(request)
    if err:
        return err

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """SELECT st.id, st.start_time, st.end_time, st.notes,
                  st.is_locked, st.assignment_id, st.course_id,
                  c.course_name
           FROM StudyTimes st
           LEFT JOIN Courses c ON st.course_id = c.id
           WHERE st.term_id = %s
           ORDER BY st.start_time""",
        (term_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    study_times = []
    for r in rows:
        study_times.append({
            "id": r["id"],
            "start_time": r["start_time"].isoformat() if r["start_time"] else None,
            "end_time": r["end_time"].isoformat() if r["end_time"] else None,
            "notes": r["notes"],
            "is_locked": bool(r["is_locked"]) if r.get("is_locked") is not None else False,
            "assignment_id": r["assignment_id"],
            "course_id": r["course_id"],
            "course_name": r.get("course_name"),
        })

    return jsonify({"study_times": study_times})
```

**Step 3: Commit**

```bash
git add backend/app/api/schedule.py
git commit -m "feat: add GET /api/schedule/terms/:id/study-times endpoint"
```

---

## Task 11: Integration Testing & Validation

**Step 1: Start Docker environment**

```bash
cd /Users/leonwong/Desktop/syllabify/syllabify
docker compose down && docker compose up -d --build
```

**Step 2: Verify migration applied**

```bash
docker compose exec mysql mysql -u syllabify_user -p'syllabify_pass' syllabify_db -e "SHOW TABLES LIKE 'Calendar%';"
```

Expected: CalendarSources, CalendarEvents tables listed.

**Step 3: Verify StudyTimes columns added**

```bash
docker compose exec mysql mysql -u syllabify_user -p'syllabify_pass' syllabify_db -e "DESCRIBE StudyTimes;"
```

Expected: is_locked, assignment_id, course_id columns present.

**Step 4: Run backend tests**

```bash
docker compose exec backend python -m pytest tests/ -v
```

Expected: All tests pass, including new ICS parsing tests.

**Step 5: Start frontend and verify**

```bash
cd frontend && npm run dev
```

- Navigate to `/app/schedule`
- Verify FullCalendar renders
- Verify "Import Calendar" button opens UnifiedImportModal
- Verify both tabs work (Google and ICS)
- Verify "iCal Export" button shows as disabled/coming soon

**Step 6: Test ICS import flow**

- Use a public ICS feed URL for testing
- Verify events appear on the calendar
- Verify deadline markers show with distinct styling
- Verify source appears in the sources sidebar

**Step 7: Test Google Calendar import flow (if credentials available)**

- Connect Google account
- Import calendars
- Verify events show in FullCalendar

**Step 8: Final commit with any fixes**

```bash
git add -A
git commit -m "fix: integration fixes for Phase 1 calendar data ingestion"
```

---

## Compatibility Check with Phase 2 & Phase 3

| Future Feature | Phase 1 Preparation | Status |
|---|---|---|
| Scheduling conflict detection | CalendarEvents has event_kind + start_time/end_time for busy interval queries | Ready |
| Locked/pinned study blocks | StudyTimes.is_locked column added | Ready |
| Local overrides | CalendarEvents has local_* columns + local_modified_at | Ready |
| iCal export subscription | CalendarEvents has stable external_uid + instance_key for UID generation | Ready |
| Sync status management | sync_status enum with 'stale' for safe sync | Ready |
| Two-way Google write-back | CalendarSources.is_writable + source_mode distinguish read/write | Ready |
| Event category for scheduler | Two-layer event_kind + event_category | Ready |

**No known conflicts with Phase 2 or Phase 3.**
