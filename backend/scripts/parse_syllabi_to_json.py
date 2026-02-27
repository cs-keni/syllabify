"""
Parse extracted syllabus text into structured JSON following syllabus-schema-template.
Reads from extracted/*.txt, writes parsed.json to syllabus/{course}/
"""
import json
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND = SCRIPT_DIR.parent
SYLLABUS_ROOT = BACKEND / "tests" / "fixtures" / "syllabus-data" / "syllabus"
EXTRACTED = BACKEND / "tests" / "fixtures" / "syllabus-data" / "extracted"


def parse_course_code(text: str, folder: str) -> str:
    """Extract course code (e.g. CS 210) from text or folder."""
    for m in re.finditer(r"\b([A-Z]{2,4}\s*\d{3}[A-Z]?)\b", text[:3000], re.I):
        code = m.group(1).strip()
        if code.lower() not in ("room", "week", "oct", "nov", "dec", "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep"):
            return code
    parts = folder.replace("_", " ").split()
    if len(parts) >= 2 and parts[0].isalpha() and parts[1].isdigit():
        return f"{parts[0]} {parts[1]}"
    return folder


def parse_course_title(text: str, folder: str) -> str:
    """Extract course title from text."""
    lines = text.split("\n")
    for i, line in enumerate(lines[:30]):
        line = line.strip()
        if re.match(r"^[A-Z]{2,4}\s*\d{3}", line, re.I) and len(line) < 80:
            rest = " ".join(lines[i + 1 : i + 3]).strip()
            if rest and len(rest) < 120:
                return rest.split("\n")[0][:100]
        if any(
            w in line.lower()
            for w in ["operating systems", "computer science", "algorithms", "concepts", "natural environment"]
        ):
            return line[:100]
    return ""


def parse_instructors(text: str) -> list:
    """Extract instructor name and email."""
    instructors = []
    for m in re.finditer(
        r"(?:Instructor|Course instructor|Professor)[:\s]+([A-Za-z][A-Za-z\.\s\-]+?)(?:\s+Office|\s+Email|$|\n)",
        text[:3000],
        re.I,
    ):
        name = m.group(1).strip()
        if len(name) > 3 and len(name) < 60:
            instructors.append({"id": f"inst-{len(instructors)}", "name": name, "email": None})
    for m in re.finditer(r"([a-z0-9_.+-]+@[a-z0-9.-]+\.edu)", text[:5000], re.I):
        email = m.group(1)
        if instructors and instructors[-1].get("email") is None:
            instructors[-1]["email"] = email
        elif email and not any(i.get("email") == email for i in instructors):
            instructors.append({"id": f"inst-{len(instructors)}", "name": None, "email": email})
    return instructors[:5] if instructors else []


def parse_meeting_times(text: str) -> list:
    """Extract structured meeting times."""
    day_map = {
        "m": "MO", "tu": "TU", "tues": "TU", "we": "WE", "wed": "WE",
        "th": "TH", "thu": "TH", "thurs": "TH", "f": "FR", "fr": "FR", "fri": "FR",
        "sa": "SA", "su": "SU", "mo": "MO", "tue": "TU", "wednesday": "WE",
        "thursday": "TH", "friday": "FR", "monday": "MO", "tuesday": "TU",
    }
    meetings = []
    for m in re.finditer(
        r"(?:Lecture|Class|Lab|Discussion)[s]?\s*(?: and |, |; )?([A-Za-z,]+)\s*[\d:]+\s*[-–to]+\s*[\d:]+\s*(?:AM|PM)?(?:\s*,\s*([A-Za-z0-9\s\-]+))?",
        text[:4000],
        re.I,
    ):
        days_str = m.group(1)
        location = m.group(2).strip() if m.group(2) else None
        for d in re.split(r"[\s,/\&\;]+", days_str):
            d = d.strip()[:2].lower() if d else ""
            day = day_map.get(d) or day_map.get(d + "s")
            if day:
                meetings.append({
                    "id": f"mt-{len(meetings)}",
                    "day_of_week": day,
                    "start_time": "10:00",
                    "end_time": "11:20",
                    "timezone": "America/Los_Angeles",
                    "location": location,
                    "type": "lecture",
                })
    if not meetings and re.search(r"(?:Tu|Tue|Thu|Wed|Mon|Fri)[,s]?\s+\d+[:-]", text[:2000], re.I):
        for d in re.findall(r"\b(Monday|Tuesday|Wednesday|Thursday|Friday|Tue|Thu|Wed|Mon|Fri)\b", text[:2000], re.I):
            key = d[:2].lower()
            day = day_map.get(key) or day_map.get(d.lower()[:3])
            if day and not any(me["day_of_week"] == day for me in meetings):
                meetings.append({
                    "id": f"mt-{len(meetings)}",
                    "day_of_week": day,
                    "start_time": None,
                    "end_time": None,
                    "timezone": "America/Los_Angeles",
                    "location": None,
                    "type": "lecture",
                })
    return meetings[:6]


def parse_assessments(text: str, folder: str) -> tuple:
    """Extract assessment categories and individual assessments."""
    categories = []
    assessments = []
    cat_ids = {}

    # Grade weight patterns: "Projects 15%", "Midterm 30%", "Final exam 40%"
    for m in re.finditer(
        r"(?:^|\n)\s*([A-Za-z][A-Za-z\s\-]+?)\s+(\d{1,3})\s*%\s*",
        text,
        re.M | re.I,
    ):
        name = m.group(1).strip()
        pct = int(m.group(2))
        skip = name.lower() in ("the", "a", "an", "to", "of", "and", "or")
        if not skip and len(name) > 3 and len(name) < 50 and pct <= 100:
            cid = re.sub(r"\s+", "_", name.lower())[:30]
            if cid not in cat_ids:
                cat_ids[cid] = len(categories)
                categories.append({
                    "id": cid,
                    "name": name,
                    "weight_percent": pct,
                    "drop_lowest": None,
                    "subcategories": [],
                    "grading_bucket": None,
                })
            a_type = "assignment"
            if "exam" in name.lower() or "midterm" in name.lower():
                a_type = "midterm" if "midterm" in name.lower() else "final"
            elif "quiz" in name.lower():
                a_type = "quiz"
            elif "project" in name.lower():
                a_type = "project"
            elif "homework" in name.lower() or "hw" in name.lower():
                a_type = "assignment"
            assessments.append({
                "id": f"{cid}_1",
                "title": name,
                "category_id": cid,
                "type": a_type,
                "due_datetime": None,
                "all_day": True,
                "timezone": None,
                "weight_percent": pct,
                "points": None,
                "recurrence": {"frequency": None, "interval": None, "by_day": None, "until": None, "count": None},
                "policies": {"late_policy": None, "late_pass_allowed": None},
                "confidence": 0.85,
                "source_excerpt": m.group(0).strip()[:200],
            })

    # Date patterns: "April 23rd", "May 16", "Jun 11"
    date_pat = r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{4}))?"
    months = "jan feb mar apr may jun jul aug sep oct nov dec".split()

    for m in re.finditer(
        rf"(Midterm|Final|Exam|Project|Homework|Assignment|Quiz|Lab)\s*(\d+)?\s+(\d{{1,3}})\s*%\s*.*?({date_pat})",
        text,
        re.I | re.DOTALL,
    ):
        try:
            kind, num, pct_str, mon, day_str, year = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)
            if not day_str.isdigit():
                continue
            mon_num = months.index(mon[:3].lower()) + 1
            yr = int(year) if year else 2025
            due = f"{yr}-{mon_num:02d}-{int(day_str):02d}"
        except (ValueError, IndexError, AttributeError):
            continue
        a_id = f"{kind}_{num or 1}".lower()
        cid = "exams" if "exam" in kind.lower() or "midterm" in kind.lower() or "final" in kind.lower() else "assignments"
        if cid not in cat_ids:
            cat_ids[cid] = len(categories)
            categories.append({"id": cid, "name": cid.title(), "weight_percent": None, "drop_lowest": None, "subcategories": [], "grading_bucket": None})
        a_id = f"{kind}_{num or 1}".lower().replace(" ", "_")
        if not any(a["id"] == a_id for a in assessments):
            assessments.append({
                "id": a_id,
                "title": f"{kind} {num or ''}".strip(),
                "category_id": cid,
                "type": "midterm" if "midterm" in kind.lower() else "final" if "final" in kind.lower() else "assignment",
                "due_datetime": due,
                "all_day": True,
                "timezone": "America/Los_Angeles",
                "weight_percent": int(pct_str) if pct_str else None,
                "points": None,
                "recurrence": None,
                "policies": {},
                "confidence": 0.9,
                "source_excerpt": m.group(0).strip()[:150],
            })

    # Fallback: simple due date patterns
    for m in re.finditer(rf"({date_pat})", text):
        pass  # could add schedule items
    return categories, assessments


def parse_term(text: str) -> str:
    """Extract term (e.g. Fall 2025, Spring 2025)."""
    m = re.search(r"(Fall|Winter|Spring|Summer)\s*(\d{4})", text[:1500], re.I)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    m = re.search(r"(\d{4})\s*(?:Fall|Winter|Spring|Summer)", text[:1500], re.I)
    if m:
        return f"{m.group(2)} {m.group(1)}" if m.group(2) else m.group(1)
    return None


def parse_late_policy(text: str) -> dict:
    """Extract late pass policy."""
    policy = {"total_allowed": None, "extension_days": None}
    m = re.search(r"(\d+)\s*(?:late|extension)", text[:5000], re.I)
    if m:
        policy["total_allowed"] = int(m.group(1))
    m = re.search(r"(\d+)\s*(?:day|days)\s*(?:extension|late)", text[:5000], re.I)
    if m:
        policy["extension_days"] = int(m.group(1))
    return policy


def build_syllabus_json(folder: str, text: str, source_file: str) -> dict:
    """Build full syllabus JSON from extracted text."""
    course_code = parse_course_code(text, folder)
    course_title = parse_course_title(text, folder) or folder
    term = parse_term(text)
    instructors = parse_instructors(text)
    meeting_times = parse_meeting_times(text)
    categories, assessments = parse_assessments(text, folder)
    late_policy = parse_late_policy(text)

    # Location
    loc_m = re.search(r"(?:Room|Location|Hall|Building)[:\s]+([A-Za-z0-9\s\-]+)", text[:2000], re.I)
    location = loc_m.group(1).strip() if loc_m else None

    return {
        "course": {
            "id": folder.lower(),
            "course_code": course_code,
            "course_title": course_title or course_code,
            "term": term,
            "timezone": "America/Los_Angeles",
            "instructors": instructors if instructors else [{"id": "inst-0", "name": None, "email": None}],
            "meeting_times": meeting_times if meeting_times else [],
            "location": location,
        },
        "assessment_categories": categories if categories else [{"id": "general", "name": "General", "weight_percent": None, "drop_lowest": None, "subcategories": [], "grading_bucket": None}],
        "assessments": assessments if assessments else [],
        "grading_structure": {"type": "flat" if len(categories) <= 1 else "bucketed", "buckets": []},
        "late_pass_policy": late_policy,
        "schedule": [],
        "metadata": {"created_at": None, "updated_at": None, "source_type": Path(source_file).suffix.lstrip("."), "schema_version": "1.0"},
    }


def main():
    for f in sorted(EXTRACTED.glob("*.txt")):
        if f.name.startswith("_"):
            continue
        course = f.stem
        folder = SYLLABUS_ROOT / course
        if not folder.is_dir():
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        # Find original file for source_type
        orig = next((x for x in folder.iterdir() if x.suffix.lower() in (".pdf", ".docx", ".txt") and x.name != "parsed.json"), None)
        source = orig.name if orig else "txt"
        try:
            data = build_syllabus_json(course, text, source)
            out = folder / "parsed.json"
            out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"OK {course} -> {len(data['assessments'])} assessments")
        except Exception as e:
            print(f"ERR {course}: {e}")


if __name__ == "__main__":
    main()
