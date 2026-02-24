"""
Rule-based syllabus parser: extracts structured data from syllabus text.
Outputs JSON following the syllabus schema (course, assessments, meeting_times, etc.).
Modular structure: course, meeting_times, assessments, late_policy.

When adding support for new syllabus formats:
  - Add new patterns in the appropriate module (assessments.py, meeting_times.py, etc.)
  - Add course title to course_title_keywords in course.py if needed
  - Add late-policy phrases to late_policy.py for new phrasings
  - Run tests: python -m pytest tests/test_syllabus_parser.py -v
"""
import re

from .assessments import parse_assessments
from .course import (
    parse_course_code,
    parse_course_title,
    parse_instructors,
    parse_term,
)
from .late_policy import parse_late_policy
from .meeting_times import parse_meeting_times


def parse_syllabus_text(text: str, course_id: str, source_type: str = "txt") -> dict:
    """
    Parse syllabus text into full schema JSON.
    Returns dict with course, assessment_categories, assessments, grading_structure,
    late_pass_policy, schedule, metadata.
    """
    course_code = parse_course_code(text, course_id)
    course_title = parse_course_title(text, course_id) or course_code
    term = parse_term(text)
    instructors = parse_instructors(text)
    meeting_times = parse_meeting_times(text)
    categories, assessments = parse_assessments(text, course_id, term)
    late_policy = parse_late_policy(text)

    loc = None
    for m in re.finditer(r"(?:in|at)\s+([A-Za-z0-9\s\-]{3,30})\s*\.", text[:3000], re.I):
        loc = m.group(1).strip()
        if any(k in loc.lower() for k in ("pacific", "lillis", "mckenzie", "mck")):
            break
    if not loc and meeting_times:
        loc = meeting_times[0].get("location")

    if not instructors:
        instructors = [{"id": "inst-0", "name": None, "email": None}]
    if not categories:
        categories = [{
            "id": "general", "name": "General", "weight_percent": None,
            "drop_lowest": None, "subcategories": [], "grading_bucket": None,
        }]

    gtype = "bucketed" if any(c["id"] in ("project_grade", "exam_grade") for c in categories) else "flat"
    buckets = []
    if gtype == "bucketed":
        for c in categories:
            if c["id"] in ("project_grade", "exam_grade"):
                buckets.append({"id": c["id"][:4], "name": c["name"], "weight_percent": None})

    return {
        "course": {
            "id": course_id.lower(),
            "course_code": course_code,
            "course_title": course_title or course_code,
            "term": term,
            "timezone": "America/Los_Angeles",
            "instructors": instructors,
            "meeting_times": meeting_times,
            "location": loc,
        },
        "assessment_categories": categories,
        "assessments": assessments,
        "grading_structure": {"type": gtype, "buckets": buckets},
        "late_pass_policy": late_policy,
        "schedule": [],
        "metadata": {
            "created_at": None, "updated_at": None,
            "source_type": source_type, "schema_version": "1.0",
        },
    }


# Re-export for external use
__all__ = [
    "parse_syllabus_text",
    "parse_course_code",
    "parse_course_title",
    "parse_term",
    "parse_instructors",
    "parse_meeting_times",
    "parse_assessments",
    "parse_late_policy",
]
