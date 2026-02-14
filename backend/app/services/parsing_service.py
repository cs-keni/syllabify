"""
Syllabus parsing: extract assignments, due dates, hours from plain text.
Uses rule-based heuristics (regex, tables, prose patterns).
"""
import re

from app.utils.date_utils import parse_due_date
from app.utils.document_utils import extract_text_from_file


def parse_file(file, mode: str = "rule") -> dict:
    """Extract text from file via document_utils, then parse with parse_text."""
    text = extract_text_from_file(file)
    return parse_text(text, mode=mode)


def parse_text(text: str, mode: str = "rule") -> dict:
    """
    Parse syllabus text into course_name and assignments.
    Returns { course_name, assignments, raw_text?, confidence? }
    assignments: [{ name, due_date (YYYY-MM-DD or null), hours }]
    """
    if not text or not text.strip():
        return {
            "course_name": "Course",
            "assignments": [],
            "raw_text": text or "",
            "confidence": "low",
        }

    if mode in ("hybrid", "ai"):
        # Optional: call AI parser if available
        try:
            from app.services.ai_parser import parse_with_ai
            return parse_with_ai(text)
        except ImportError:
            pass

    return _parse_rulebased(text)


def _parse_rulebased(text: str) -> dict:
    """Rule-based extraction: course name, assignments with name, due_date, hours."""
    course_name = _extract_course_name(text)
    assignments = []

    # Try table-like extraction (rows with | or tabs)
    lines = text.split("\n")
    for line in lines:
        # Pattern: "Assignment 1 | 2/15 | 4" or "Week 3: Midterm - Feb 15"
        parts = re.split(r"\s*[\|\t]\s*", line.strip())
        if len(parts) >= 2:
            name = parts[0].strip()
            due = parse_due_date(parts[1]) if len(parts) > 1 else None
            hours = _infer_hours(name, parts[2] if len(parts) > 2 else None)
            if name and len(name) > 2:
                assignments.append({
                    "name": name,
                    "due_date": due.isoformat() if due else None,
                    "hours": hours,
                })

    # Prose patterns: "Assignment 1 due Feb 15", "Midterm - March 3"
    if not assignments:
        assignments = _extract_from_prose(text)

    # If still few results, return low confidence with raw text
    confidence = "high" if len(assignments) >= 2 else "low"
    return {
        "course_name": course_name,
        "assignments": assignments,
        "raw_text": text if confidence == "low" else None,
        "confidence": confidence,
    }


def _extract_course_name(text: str) -> str:
    """Extract course name from title (first line or course code pattern)."""
    lines = text.strip().split("\n")
    for line in lines[:5]:
        line = line.strip()
        if not line:
            continue
        # Match "CS 422", "MATH 343", "GEOG 141"
        m = re.match(r"^([A-Z]{2,4}\s*\d{3}[A-Z]?(?:\s+[^\n]{0,80})?)", line, re.I)
        if m:
            return m.group(1).strip()[:80]
        if len(line) < 100 and not line.startswith(" "):
            return line[:80]
    return "Course"


def _infer_hours(name: str, explicit: str | None) -> int:
    """Infer estimated hours from assignment type or explicit value."""
    if explicit:
        try:
            return min(max(int(float(explicit)), 1), 10)
        except (ValueError, TypeError):
            pass
    name_lower = (name or "").lower()
    if any(w in name_lower for w in ("exam", "midterm", "final")):
        return 2
    if any(w in name_lower for w in ("quiz")):
        return 1
    if any(w in name_lower for w in ("project", "assignment", "homework", "hw")):
        return 4
    return 3


def _extract_from_prose(text: str) -> list:
    """Extract assignments from prose using regex patterns."""
    assignments = []
    seen = set()  # avoid duplicates: (name, due)

    # Simple: "X due DATE" (e.g. "Assignment 1 due Feb 15")
    for m in re.finditer(
        r"([^\n]{3,80}?)\s+due\s+(\d{1,2}[/\-]\d{1,2}(?:[/\-]\d{2,4})?|\w+\s+\d{1,2}(?:,?\s*\d{4})?)",
        text,
        re.I,
    ):
        name = m.group(1).strip()
        date_str = m.group(2).strip()
        due = parse_due_date(date_str)
        if name and len(name) > 2 and len(name) < 80:
            key = (name[:50], due.isoformat() if due else "")
            if key not in seen:
                seen.add(key)
                assignments.append({
                    "name": name,
                    "due_date": due.isoformat() if due else None,
                    "hours": _infer_hours(name, None),
                })

    # Pattern: "Feb 15 - Assignment 1" or "2/15: Midterm"
    for m in re.finditer(
        r"(\d{1,2}[/\-]\d{1,2}(?:[/\-]\d{2,4})?|\w+\s+\d{1,2}(?:,?\s*\d{4})?)\s*[:\-]\s*([^\n\.]{5,80})",
        text,
        re.I,
    ):
        date_str, name = m.group(1).strip(), m.group(2).strip()
        due = parse_due_date(date_str)
        if name and len(name) > 2 and len(name) < 80:
            key = (name[:50], due.isoformat() if due else "")
            if key not in seen:
                seen.add(key)
                assignments.append({
                    "name": name,
                    "due_date": due.isoformat() if due else None,
                    "hours": _infer_hours(name, None),
                })

    return assignments
