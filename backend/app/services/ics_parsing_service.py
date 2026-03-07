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
