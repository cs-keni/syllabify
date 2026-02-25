"""
Syllabus parsing: extract course info and assessments from plain text.
Uses the full syllabus_parser (schema with assessments, exams, categories)
and maps to API shape (course_name, assignments) for backward compatibility.
Hybrid mode: structured extraction + LLM parsing, with heuristic fallback.
"""
import os
import re

from app.utils.date_utils import parse_due_date


def compute_parse_confidence(parser_result: dict | None, course_name: str, assignments: list) -> dict:
    """
    Compute 0-100 confidence score from parse completeness (post-hoc heuristic).
    Returns { score: int, label: str, breakdown?: dict } for UI display.
    """
    def _label(s: int) -> str:
        if s >= 70:
            return "high"
        if s >= 40:
            return "medium"
        return "low"

    if not parser_result:
        # Fallback path: simpler scoring from course_name + assignments only
        score = 0
        if course_name and course_name not in ("Course", ""):
            score += 30
        n = len(assignments)
        if n >= 3:
            score += 45
        elif n >= 1:
            score += 30
        with_due = sum(1 for a in assignments if a.get("due_date"))
        if n and with_due:
            score += 25 * min(1.0, with_due / n)
        return {"score": min(100, score), "label": _label(min(100, score))}

    course = parser_result.get("course") or {}
    assessments = parser_result.get("assessments") or []
    meeting_times = course.get("meeting_times") or []
    instructors = course.get("instructors") or []
    late_policy = parser_result.get("late_pass_policy") or {}
    breakdown = {}

    # Course code (0-20): e.g. "CS 314" vs folder-like "105-Thompson"
    code = (course.get("course_code") or "").strip()
    if re.match(r"^[A-Z]{2,4}\s*\d{3}[A-Z]?$", code, re.I):
        breakdown["course_code"] = 20
    elif code and 3 <= len(code) <= 20 and "-" not in code and "_" not in code:
        breakdown["course_code"] = 10
    else:
        breakdown["course_code"] = 0

    # Course title (0-15): real title, not folder name
    title = (course.get("course_title") or "").strip()
    if title and 5 <= len(title) <= 120 and title != code:
        if not re.match(r"^[\w\-_.]+$", title) or " " in title:
            breakdown["course_title"] = 15
        else:
            breakdown["course_title"] = 5
    elif title:
        breakdown["course_title"] = 5
    else:
        breakdown["course_title"] = 0

    # Meeting times (0-25)
    mt_score = 0
    if meeting_times:
        with_time = sum(1 for m in meeting_times if m.get("start_time") or m.get("end_time"))
        with_loc = sum(1 for m in meeting_times if (m.get("location") or "").strip())
        mt_score = 10 + min(10, with_time * 4) + min(5, with_loc * 2)
    breakdown["meeting_times"] = min(25, mt_score)

    # Assessments (0-25): reward completeness but penalize duplicates
    a_score = 0
    if assessments:
        a_score = 10 + min(10, len(assessments) * 2)
        with_weight = sum(1 for a in assessments if a.get("weight_percent") is not None)
        if with_weight > 0:
            total = sum(a.get("weight_percent") or 0 for a in assessments)
            if 90 <= total <= 110:
                a_score += 5
        # Penalize duplicate types (e.g. 3x participation, 2x midterm when only 1 expected)
        type_counts = {}
        for a in assessments:
            t = a.get("type") or "assignment"
            type_counts[t] = type_counts.get(t, 0) + 1
        dup_penalty = 0
        if type_counts.get("participation", 0) > 1:
            dup_penalty += 3
        if type_counts.get("midterm", 0) > 1:
            dup_penalty += 2
        if type_counts.get("project", 0) > 3:
            dup_penalty += 2
        a_score = max(0, a_score - dup_penalty)
    breakdown["assessments"] = min(25, a_score)

    # Instructor (0-10)
    inst = (instructors[0].get("name") or "").strip() if instructors else ""
    breakdown["instructor"] = 10 if inst and inst.lower() != "staff" else (5 if inst else 0)

    # Late policy (0-5)
    breakdown["late_policy"] = 5 if late_policy.get("total_allowed") is not None else 0

    total = min(100, sum(breakdown.values()))
    return {"score": total, "label": _label(total), "breakdown": breakdown}
from app.utils.document_utils import extract_text_from_file, extract_structured_from_file


def _intermediate_from_text(text: str) -> dict:
    """Build intermediate format from raw text (for pasted text, no file)."""
    from app.utils.document_utils import _detect_sections, _extract_candidate_dates, _extract_candidate_percentages
    return {
        "raw_text": text,
        "sections": _detect_sections(text),
        "tables": [],
        "candidate_dates": _extract_candidate_dates(text),
        "candidate_percentages": _extract_candidate_percentages(text),
        "metadata": {"source_type": "txt"},
    }


def _parse_hybrid_file(file) -> dict:
    """Hybrid parse: structured extraction + LLM, fallback to heuristic."""
    intermediate = extract_structured_from_file(file)
    filename = getattr(file, "filename", None) or ""
    source_type = "pdf" if str(filename).lower().endswith(".pdf") else "docx" if str(filename).lower().endswith(".docx") else "txt"
    result = _parse_hybrid(intermediate, source_type)
    if result is not None:
        return result
    text = intermediate.get("raw_text") or extract_text_from_file(file)
    return _parse_with_syllabus_parser(text, source_type)


def _parse_hybrid(intermediate: dict, source_type: str) -> dict | None:
    """Call LLM parser, map to API shape. Returns None on failure."""
    try:
        from app.services.llm_parser import parse_with_llm
    except ImportError:
        return None
    llm_result = parse_with_llm(intermediate)
    if not llm_result:
        return None
    raw_text = intermediate.get("raw_text", "")
    return _map_llm_result_to_api(llm_result, source_type, raw_text)


def _map_llm_result_to_api(llm_result: dict, source_type: str, raw_text: str = "") -> dict:
    """Map LLM output to parsing_service API shape (course_name, assignments, assessments, meeting_times, instructors, confidence)."""
    course = llm_result.get("course") or {}
    assessments = llm_result.get("assessments") or []
    course_name = (course.get("course_code") or course.get("course_title") or "Course").strip()

    seen = {}
    for a in assessments:
        title = (a.get("title") or "").strip()
        if _is_junk_title(title):
            continue
        atype = a.get("type") or "assignment"
        due_datetime = a.get("due_datetime")
        due_date = due_datetime[:10] if due_datetime and len(due_datetime) >= 10 else None
        weight = a.get("weight_percent")
        key = (title.lower()[:50], atype)
        if key not in seen or (due_date and not seen[key].get("due_date")):
            seen[key] = {
                "name": title,
                "due_date": due_date,
                "hours": _hours_from_assessment_type(atype),
                "type": atype,
                "weight": weight,
            }
    assignments = [
        {"name": v["name"], "due_date": v["due_date"], "hours": v["hours"], "type": v["type"]}
        for v in seen.values()
    ]
    assessments_for_api = [
        {"title": v["name"], "due_datetime": v["due_date"], "type": v["type"]}
        for v in seen.values()
    ]
    meeting_times = course.get("meeting_times") or []
    instructors = course.get("instructors") or []
    conf = compute_parse_confidence(llm_result, course_name, assignments)
    return {
        "course_name": course_name,
        "assignments": assignments,
        "assessments": assessments_for_api,
        "meeting_times": meeting_times,
        "instructors": instructors,
        "raw_text": None if conf["label"] == "high" else raw_text,
        "confidence": conf,
    }


def _is_junk_title(t: str) -> bool:
    """Filter obvious junk assessment titles."""
    if not t or len(t) < 3:
        return True
    t_lower = t.lower()
    if t_lower in ("each", "class", "lab"):
        return True
    if re.match(r"^lab\s*\d+$", t_lower):
        return True
    if t_lower.startswith("continue with ") or "no class" in t_lower:
        return True
    if t_lower in ("midterm midterm midterm", "no class no class"):
        return True
    if t_lower.startswith("except for ") or "waived by the token" in t_lower:
        return True
    if "textbooks and readings" in t_lower and len(t) < 30:
        return True
    if t_lower.startswith("of ") and "participation" in t_lower:
        return True
    if "lecture section coverage" in t_lower and "homework" in t_lower:
        return True
    if t_lower == "learning outcomes" or t_lower == "missed exams":
        return True
    if "late projects" in t_lower and "submissions will incur" in t_lower:
        return True
    if "late submissions will incur" in t_lower:
        return True
    return False


def parse_file(file, mode: str = "rule") -> dict:
    """Extract text from file via document_utils, then parse with parse_text."""
    use_llm = os.getenv("USE_LLM_PARSER", "").lower() == "true"
    if use_llm and mode in ("hybrid", "rule", "ai"):
        return _parse_hybrid_file(file)
    text = extract_text_from_file(file)
    filename = getattr(file, "filename", None) or ""
    source_type = "pdf" if str(filename).lower().endswith(".pdf") else "txt"
    return parse_text(text, mode=mode, source_type=source_type)


def parse_text(text: str, mode: str = "rule", source_type: str = "txt") -> dict:
    """
    Parse syllabus text into course_name, assignments, and full assessments.
    Returns { course_name, assignments, assessments?, raw_text?, confidence? }
    assignments: [{ name, due_date (YYYY-MM-DD or null), hours, type? }] for UI/save.
    assessments: full schema list (title, type, due_datetime, weight_percent, ...) for UI.
    """
    if not text or not text.strip():
        return {
            "course_name": "Course",
            "assignments": [],
            "assessments": [],
            "raw_text": text or "",
            "confidence": {"score": 0, "label": "low"},
        }

    use_llm = os.getenv("USE_LLM_PARSER", "").lower() == "true"
    if use_llm and mode in ("hybrid", "rule", "ai"):
        intermediate = _intermediate_from_text(text)
        result = _parse_hybrid(intermediate, source_type)
        if result is not None:
            return result

    if mode in ("hybrid", "ai"):
        try:
            from app.services.ai_parser import parse_with_ai
            return parse_with_ai(text)
        except ImportError:
            pass

    return _parse_with_syllabus_parser(text, source_type)


def _hours_from_assessment_type(atype: str) -> int:
    """Infer default hours from assessment type (midterm/final/quiz/project/assignment)."""
    if not atype:
        return 3
    t = (atype or "").lower()
    if t in ("midterm", "final"):
        return 2
    if t == "quiz":
        return 1
    if t == "project":
        return 4
    return 3


def _parse_with_syllabus_parser(text: str, source_type: str) -> dict:
    """
    Use full syllabus_parser (schema with assessments, exams, categories).
    Maps to course_name + assignments for API, and returns assessments for UI.
    """
    try:
        from app.services.syllabus_parser import parse_syllabus_text
    except ImportError:
        return _parse_rulebased_fallback(text)

    course_id = "upload"
    result = parse_syllabus_text(text, course_id, source_type)
    course = result.get("course") or {}
    course_name = (course.get("course_code") or course.get("course_title") or "Course").strip()
    assessments = result.get("assessments") or []

    # Dedupe: prefer (title_normalized, type) with due_datetime or highest weight_percent
    no_final_exam = bool(re.search(r"\bno\s+final\s+exam\b|\bno\s+final\b", text[:5000], re.I))
    seen = {}
    for a in assessments:
        title = (a.get("title") or "").strip()
        if _is_junk_title(title):
            continue
        if no_final_exam and title.lower() in ("final", "final exam"):
            continue
        atype = a.get("type") or "assignment"
        # Normalize participation titles for deduplication: "In Class Participation", "Class participation", "of class participation" -> same
        key_title = title.lower()[:50]
        if atype == "participation" and "participation" in key_title:
            if "class" in key_title or "in class" in key_title or key_title.startswith("of "):
                key_title = "class participation"
        # Normalize midterm: "Midterm" and "Midterm exam" -> same
        if atype == "midterm" and ("midterm" in key_title or "exam" in key_title):
            key_title = "midterm"
        # Normalize project: "Project" and "Class Project" (same thing when both ~40%)
        if atype == "project" and ("class project" in key_title or key_title == "project"):
            key_title = "class project"
        key = (key_title, atype)
        due_datetime = a.get("due_datetime")
        due_date = (due_datetime[:10] if due_datetime and len(due_datetime) >= 10 else None)
        weight = a.get("weight_percent")
        existing = seen.get(key)
        # Prefer: 1) due date (never replace row with due_date by one without), 2) higher weight, 3) longer title
        if existing is None:
            should_replace = True
        elif due_date and not existing.get("due_date"):
            should_replace = True  # we have date, existing doesn't
        elif not due_date and existing.get("due_date"):
            should_replace = False  # keep existing (it has date)
        else:
            should_replace = (
                weight is not None and (existing.get("weight") or 0) < (weight or 0)
            ) or (len(title) > len(existing.get("name") or ""))
        if should_replace:
            seen[key] = {
                "name": title,
                "due_date": due_date,
                "hours": _hours_from_assessment_type(atype),
                "type": atype,
                "weight": weight,
            }

    assignments = [
        {"name": v["name"], "due_date": v["due_date"], "hours": v["hours"], "type": v["type"]}
        for v in seen.values()
    ]
    # Assessments-shaped list (deduped) for frontend so it gets type/due
    assessments_for_api = [
        {"title": v["name"], "due_datetime": v["due_date"], "type": v["type"]}
        for v in seen.values()
    ]

    # If full parser found nothing, fall back to simple table/prose extraction
    if len(assignments) == 0:
        fallback = _parse_rulebased_fallback(text)
        fallback_items = fallback.get("assignments") or []
        assignments = []
        assessments_for_api = []
        for a in fallback_items:
            atype = a.get("type") or _infer_type_from_name(a.get("name", ""))
            item = {
                "name": a["name"],
                "due_date": a.get("due_date"),
                "hours": a.get("hours", 3),
                "type": atype,
            }
            assignments.append(item)
            assessments_for_api.append({"title": a["name"], "due_datetime": a.get("due_date"), "type": atype})
        if fallback.get("course_name") and not course_name:
            course_name = fallback["course_name"]
        conf = compute_parse_confidence(None, course_name, assignments)
        return {
            "course_name": course_name,
            "assignments": assignments,
            "assessments": assessments_for_api,
            "meeting_times": [],
            "raw_text": text if conf["label"] == "low" else None,
            "confidence": conf,
        }

    conf = compute_parse_confidence(result, course_name, assignments)
    meeting_times = course.get("meeting_times") or []
    instructors = course.get("instructors") or []
    return {
        "course_name": course_name,
        "assignments": assignments,
        "assessments": assessments_for_api,
        "meeting_times": meeting_times,
        "instructors": instructors,
        "raw_text": None if conf["label"] == "high" else text,
        "confidence": conf,
    }


def _parse_rulebased_fallback(text: str) -> dict:
    """Fallback if syllabus_parser unavailable: simple regex extraction."""
    course_name = _extract_course_name(text)
    assignments = []
    lines = text.split("\n")
    for line in lines:
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
    if not assignments:
        assignments = _extract_from_prose(text)
    conf = compute_parse_confidence(None, course_name, assignments)
    return {
        "course_name": course_name,
        "assignments": assignments,
        "assessments": [],
        "meeting_times": [],
        "raw_text": text if conf["label"] == "low" else None,
        "confidence": conf,
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


def _infer_type_from_name(name: str) -> str:
    """Infer assignment type from name (for fallback extraction)."""
    n = (name or "").lower()
    if "midterm" in n or ("exam" in n and "final" not in n):
        return "midterm"
    if "final" in n:
        return "final"
    if "quiz" in n:
        return "quiz"
    if "project" in n:
        return "project"
    if "participat" in n or "attend" in n:
        return "participation"
    return "assignment"


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
