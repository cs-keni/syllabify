"""
Parse due dates from syllabus text. Handles common formats: MM/DD, Jan 15, February 15, 2025, etc.
"""
import re
from datetime import date, datetime

from dateutil import parser as dateutil_parser

# Common phrases that mean "no date"
TBA_PATTERNS = (
    r"\bTBA\b",
    r"\bTBD\b",
    r"\bTo\s+be\s+announced\b",
    r"\bTo\s+be\s+determined\b",
)


def parse_due_date(s: str) -> date | None:
    """
    Parse a date string into a date object.
    Handles: "2/15", "2/15/2025", "Feb 15", "February 15, 2025", "2025-02-15".
    Returns None for "TBA", "TBD", empty, or unparseable.
    """
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    if not s:
        return None

    # Check for TBA-like
    for pat in TBA_PATTERNS:
        if re.search(pat, s, re.I):
            return None

    # Try dateutil first (handles many formats)
    try:
        parsed = dateutil_parser.parse(s, fuzzy=True, default=datetime(2025, 1, 1))
        if parsed:
            return parsed.date()
    except (ValueError, TypeError):
        pass

    # Fallback: MM/DD or MM-DD
    m = re.match(r"(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?", s)
    if m:
        month, day, year = int(m.group(1)), int(m.group(2)), m.group(3)
        if year:
            year = int(year)
            if year < 100:
                year += 2000 if year < 50 else 1900
        else:
            year = 2025  # Default
        try:
            return date(year, month, day)
        except ValueError:
            return None

    return None
