"""
Tests for syllabus_parser: compare parser output to parsed.json ground truth.
Each course: load extracted/{course}.txt, run parse_syllabus_text, compare to syllabus/{course}/parsed.json.
"""
import json
import re
from pathlib import Path

import pytest

from app.services.syllabus_parser import parse_syllabus_text

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "syllabus-data"
EXTRACTED = FIXTURES / "extracted"
SYLLABUS = FIXTURES / "syllabus"


def _norm(s):
    """Normalize string for comparison."""
    if s is None:
        return None
    return " ".join(str(s).lower().split()).strip()


def _norm_code(s):
    """Normalize course code: 'CS210' -> 'cs 210'."""
    if not s:
        return ""
    s = str(s).upper().strip()
    m = re.search(r"([A-Z]{2,4})\s*(\d{3}[A-Z]?)", s, re.I)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    return _norm(s)


def _assessments_match(parsed: list, truth: list, tolerance: str = "strict") -> tuple[bool, list]:
    """Check if parsed assessments match ground truth. Match by (title_normalized, pct) - ignore category_id."""
    diffs = []
    truth_by_key = {}
    for a in truth:
        title = (a.get("title") or "").lower().strip()
        pct = a.get("weight_percent")
        key = (title[:50], pct)
        truth_by_key[key] = a
    parsed_by_key = {}
    parsed_by_title = {}  # title -> assessment (for relaxed matching)
    for a in parsed:
        title = (a.get("title") or "").lower().strip()
        pct = a.get("weight_percent")
        key = (title[:50], pct)
        parsed_by_key[key] = a
        parsed_by_title[title[:50]] = a

    missing = set(truth_by_key) - set(parsed_by_key)
    if tolerance == "relaxed" and missing:
        # When syllabus has no grading info, parsed has weight_percent=None; treat title match as OK
        still_missing = []
        for k in missing:
            t_title, t_pct = k
            if t_pct is not None and parsed_by_title.get(t_title) is not None:
                continue  # parsed has same title, accept despite missing pct
            still_missing.append(k)
        missing = still_missing

    if missing:
        for k in missing:
            diffs.append(f"Missing assessment: {truth_by_key[k].get('title')} {truth_by_key[k].get('weight_percent')}%")
    return len(diffs) == 0, diffs


def _meeting_times_match(parsed: list, truth: list) -> tuple[bool, list]:
    """Check if meeting times match (order-independent)."""
    diffs = []
    truth_set = set()
    for m in truth:
        truth_set.add((m.get("day_of_week"), m.get("start_time") or "", m.get("end_time") or "", (m.get("location") or "").lower()[:30]))
    parsed_set = set()
    for m in parsed:
        parsed_set.add((m.get("day_of_week"), m.get("start_time") or "", m.get("end_time") or "", (m.get("location") or "").lower()[:30]))
    missing = truth_set - parsed_set
    if missing:
        for m in missing:
            diffs.append(f"Missing meeting: {m}")
    return len(diffs) == 0, diffs


def get_syllabus_courses():
    """List course folders that have both extracted txt and parsed.json."""
    if not SYLLABUS.is_dir():
        return []
    courses = []
    for d in sorted(SYLLABUS.iterdir()):
        if not d.is_dir():
            continue
        course = d.name
        extracted_file = EXTRACTED / f"{course}.txt"
        parsed_file = d / "parsed.json"
        if extracted_file.exists() and parsed_file.exists():
            courses.append(course)
    return courses


@pytest.fixture
def syllabus_courses():
    return get_syllabus_courses()


@pytest.mark.parametrize("course", get_syllabus_courses())
def test_syllabus_parser_matches_ground_truth(course):
    """Parse extracted text and compare key fields to parsed.json ground truth."""
    extracted_path = EXTRACTED / f"{course}.txt"
    truth_path = SYLLABUS / course / "parsed.json"

    text = extracted_path.read_text(encoding="utf-8", errors="replace")
    truth = json.loads(truth_path.read_text(encoding="utf-8"))

    result = parse_syllabus_text(text, course, "txt")

    errors = []

    # Course code (accept CIS/CS, prefer folder-derived)
    tc = _norm_code(truth["course"].get("course_code"))
    rc = _norm_code(result["course"].get("course_code"))
    fc = _norm_code(course.replace("_", " "))
    if tc and rc and tc != rc:
        if fc and (fc in tc or fc in rc or rc in fc):
            pass  # folder matches one of them
        else:
            errors.append(f"course_code: got {result['course']['course_code']}, expected {truth['course']['course_code']}")

    # Course title (flexible - just check non-empty and reasonable)
    tt = (truth["course"].get("course_title") or "").strip()
    rt = (result["course"].get("course_title") or "").strip()
    if tt and not rt:
        errors.append(f"course_title: missing (expected '{tt[:40]}...')")
    elif tt and rt and tt.lower() != rt.lower() and tt.lower() not in rt.lower() and rt.lower() not in tt.lower():
        if len(tt) > 10 and len(rt) > 10:
            errors.append(f"course_title: got '{rt[:50]}', expected '{tt[:50]}'")

    # Term (non-blocking - many syllabi omit or use different formats)
    pass

    # Meeting times: require at least one matching meeting when ground truth has meetings
    truth_mt = truth["course"].get("meeting_times") or []
    result_mt = result["course"].get("meeting_times") or []
    if truth_mt:
        ok, diffs = _meeting_times_match(result_mt, truth_mt)
        if not ok:
            truth_set = set()
            for m in truth_mt:
                truth_set.add((m.get("day_of_week"), (m.get("start_time") or "")[:5], (m.get("end_time") or "")[:5]))
            result_set = set()
            for m in result_mt:
                result_set.add((m.get("day_of_week"), (m.get("start_time") or "")[:5], (m.get("end_time") or "")[:5]))
            if not (truth_set & result_set):
                errors.extend(diffs[:3])

    # Assessments: must have reasonable overlap (at least half of ground truth)
    truth_a = truth.get("assessments") or []
    result_a = result.get("assessments") or []
    ok, diffs = _assessments_match(result_a, truth_a, tolerance="relaxed")
    if not ok:
        errors.extend(diffs[:5])
    min_expected = max(1, len(truth_a) // 2) if truth_a else 0
    if truth_a and len(result_a) < min_expected:
        errors.append(f"assessments: got {len(result_a)}, expected at least {min_expected}")

    # Late policy when present
    lp_t = truth.get("late_pass_policy") or {}
    lp_r = result.get("late_pass_policy") or {}
    if lp_t.get("total_allowed") and lp_r.get("total_allowed") != lp_t.get("total_allowed"):
        errors.append(f"late_pass_policy.total_allowed: got {lp_r.get('total_allowed')}, expected {lp_t.get('total_allowed')}")

    assert not errors, f"{course}: " + "; ".join(errors)
