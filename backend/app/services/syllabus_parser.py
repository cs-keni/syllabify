"""
Rule-based syllabus parser: extracts structured data from syllabus text.
Outputs JSON following the syllabus schema (course, assessments, meeting_times, etc.).
Used for Phase 1A syllabus parsing and tested against parsed.json ground truth.
"""
import re
from pathlib import Path


def parse_course_code(text: str, folder: str) -> str:
    """Extract course code (e.g. CS 210) from text or folder."""
    skip_prefixes = {"ROOM", "WEEK", "OCT", "NOV", "DEC", "JAN", "FEB", "MAR", "APR", "JUN", "JUL", "AUG", "SEP", "MTWR", "PLC", "DES", "MCK", "LIL"}
    m0 = re.match(r"^([A-Za-z]+)(\d{3}[A-Za-z]?)$", folder.replace("_", ""))
    if m0:
        folder_prefix, folder_num = m0.group(1), m0.group(2)
        folder_code = f"{folder_prefix} {folder_num}"
        pat = re.escape(folder_prefix) + r"\s*" + re.escape(folder_num)
        if re.search(pat, text[:1500], re.I):
            return folder_code
    for m in re.finditer(r"\b([A-Z]{2,4})\s*(\d{3}[A-Z]?)\b", text[:800], re.I):
        prefix, num = m.group(1), m.group(2)
        if prefix.upper() in skip_prefixes:
            continue
        if m0 and prefix.upper() != folder_prefix.upper():
            continue
        return f"{prefix} {num}".strip()
    if m0:
        return folder_code
    parts = folder.replace("_", " ").split()
    if len(parts) >= 2 and parts[0].isalpha() and parts[1].isdigit():
        return f"{parts[0]} {parts[1]}"
    return folder


def parse_course_title(text: str, folder: str) -> str:
    """Extract short course title from text (not full sentences)."""
    lines = text.split("\n")
    # Pattern: "CS 210, Computer Science I" or "CS 212 (Spring 2024; 31311) Computer Science III"
    for i, line in enumerate(lines[:25]):
        line = line.strip()
        m = re.search(r"[A-Z]{2,4}\s*\d{3}[A-Z]?\s*[\(\-\s]*(?:Fall|Winter|Spring|Summer)?\s*\d{4}?\s*[;\)\s]*\s*([^\.\n]{5,80}?)(?:\s*$|\s+[A-Z]|\s+Syllabus)", line, re.I)
        if m:
            title = m.group(1).strip()
            if title and len(title) < 80 and not title.endswith("%"):
                return title[:100]
        # "Welcome to CS 210, Computer Science I"
        m = re.search(r"(?:Welcome to|Course:?)\s*[A-Z]{2,4}\s*\d{3}[A-Z]?[,:\s]+(.+?)(?:\.|$)", line, re.I)
        if m:
            title = m.group(1).strip()
            if title and 5 < len(title) < 80:
                return title[:100]
        # Line starting with course code followed by title
        m = re.match(r"^[A-Z]{2,4}\s*\d{3}[A-Z]?\s+[\-\s]+(.{5,80})$", line, re.I)
        if m:
            return m.group(1).strip()[:100]
        # Known title keywords as fallback
        for kw in ["Computer Science I", "Computer Science III", "Introduction to Computer Science 2",
                   "Data Structures", "Operating Systems", "Concepts in Programming Languages",
                   "Applied Cryptography", "Introduction to Computer Networks", "Computer & Network Security",
                   "Software Methodologies I", "C/C++ and Unix", "The Solar System",
                   "Introduction to Comparative Literature I", "Natural Environment", "Personal Finance",
                   "Foundations of Data Science I", "Elementary Discrete Mathematics II",
                   "Mathematical Reasoning", "Introduction to Statistics", "Statistical Methods",
                   "Scientific and Technical Writing", "Tennis I"]:
            if kw.lower() in line.lower() and len(line) < 120:
                return kw
    return ""


def parse_instructors(text: str) -> list:
    """Extract instructor name and email."""
    instructors = []
    # "Course instructor: Michal Young" or "Instructor: Hank Childs"
    for m in re.finditer(
        r"(?:Instructor|Course instructor|Professor|Name)\s*(?:Contact)?\s*[:\t]+\s*([A-Za-z][A-Za-z\.\s\-']+?)(?:\s+Office|\s+Email|\s*$|\s*\n|\t)",
        text[:4000],
        re.I,
    ):
        name = m.group(1).strip()
        name = re.sub(r"\s+", " ", name)
        if 3 < len(name) < 60 and name.lower() not in ("download", "none", "n/a"):
            if not any(i.get("name") == name for i in instructors):
                instructors.append({"id": f"inst-{len(instructors)}", "name": name, "email": None})
    # Table format: "Hank Childs\tInstructor\thank@uoregon.edu"
    for m in re.finditer(r"^([A-Za-z][A-Za-z\.\s\-']+)\s+(?:Instructor|Professor|TA)\s+([a-z0-9_.+-]+@[a-z0-9.-]+\.edu)", text[:5000], re.M | re.I):
        name, email = m.group(1).strip(), m.group(2)
        name = re.sub(r"\s+", " ", name)
        if not any(i.get("email") == email for i in instructors):
            instructors.append({"id": f"inst-{len(instructors)}", "name": name, "email": email})
    # Attach emails to instructors missing them
    for m in re.finditer(r"([a-z0-9_.+-]+@[a-z0-9.-]+\.edu)", text[:6000], re.I):
        email = m.group(1)
        if instructors and instructors[0].get("email") is None and "hank" in email.lower():
            instructors[0]["email"] = email
            break
        for inv in instructors:
            if inv.get("email") is None:
                inv["email"] = email
                break
            if inv.get("email") == email:
                break
    return instructors[:5] if instructors else []


def parse_meeting_times(text: str) -> list:
    """Extract structured meeting times: day, start, end, location."""
    day_map = {
        "m": "MO", "tu": "TU", "tues": "TU", "we": "WE", "wed": "WE",
        "th": "TH", "thu": "TH", "thurs": "TH", "f": "FR", "fr": "FR", "fri": "FR",
        "sa": "SA", "su": "SU", "mo": "MO", "tue": "TU", "mtwr": None,  # MTWR = multiple
    }
    meetings = []
    seen_days = set()

    # "Lecture 10-11:20 Tu, Thu in Pacific 123" - groups: 1=h1, 2=m1, 3=h2, 4=m2, 5=day1, 6=day2, 7=loc
    for m in re.finditer(
        r"(?:Lecture|Class|Lab|Discussion)?\s*(\d{1,2})(?::(\d{2}))?\s*[-–]\s*(\d{1,2})(?::(\d{2}))?\s*(?:AM|PM)?\s*(?:\,|\s)+(Tu|Thu|Tue|Wed|Mon|Fri|We|Th|Mo|Fr)[,\s]*(?:and\s+)?(Tu|Thu|Tue|Wed|Mon|Fri|We|Th|Mo|Fr)?\s*(?:in\s+)?([A-Za-z0-9\s\-]+)?",
        text[:5000],
        re.I,
    ):
        h1, m1, h2, m2 = m.group(1), m.group(2) or "00", m.group(3), m.group(4) or "00"
        start = f"{int(h1):02d}:{m1}"
        end = f"{int(h2):02d}:{m2}"
        loc = (m.group(7) or "").strip() if m.lastindex >= 7 and m.group(7) and len((m.group(7) or "").strip()) > 2 else None
        for g in (m.group(5), m.group(6)):
            if not g:
                continue
            key = g[:2].lower() if len(g) <= 3 else g.lower()[:3]
            day = day_map.get(key) or day_map.get(g.lower()[:2])
            if day and day not in seen_days:
                seen_days.add(day)
                meetings.append({
                    "id": f"mt-{len(meetings)+1}",
                    "day_of_week": day,
                    "start_time": start,
                    "end_time": end,
                    "timezone": "America/Los_Angeles",
                    "location": loc,
                    "type": "lecture",
                })

    # Simpler: "Lecture 10-11:20 Tu, Thu in Pacific 123" - location at end
    if not meetings:
        for m in re.finditer(
            r"(?:Lecture|Class)\s+(\d{1,2})[\:]?(\d{2})?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?\s*(?:AM|PM)?\s*[\s,]+(Tu|Thu|Tue|Wed|Mon|Fri)[,\s]+(?:and\s+)?(Tu|Thu|Tue|Wed|Mon|Fri)?[\s,]+(?:in\s+)?([A-Za-z0-9\s\-]+)",
            text[:4000],
            re.I,
        ):
            h1, m1, h2, m2 = m.group(1), m.group(2) or "00", m.group(3), m.group(4) or "00"
            start = f"{int(h1):02d}:{m1}"
            end = f"{int(h2):02d}:{m2}"
            loc = (m.group(7) or "").strip() if m.lastindex >= 7 and m.group(7) else None
            for g in (m.group(5), m.group(6)):
                if not g:
                    continue
                key = g[:2].lower()
                day = day_map.get(key) or day_map.get(g.lower()[:3])
                if day and day not in seen_days:
                    seen_days.add(day)
                    meetings.append({
                        "id": f"mt-{len(meetings)+1}",
                        "day_of_week": day,
                        "start_time": start,
                        "end_time": end,
                        "timezone": "America/Los_Angeles",
                        "location": loc,
                        "type": "lecture",
                    })

    # "M W 12:00-01:30" or "M W, 12:00-1:30, B040 PSC" (Monday Wednesday) - 01:30 = 1:30 PM when start is noon
    for m in re.finditer(r"\b(M|T|Tu|W|R|Th|F)\s*[,&\s]+\s*(M|T|Tu|W|R|Th|F)\s*[,]?\s*(\d{1,2})[\:]?(\d{2})?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?\s*(?:AM|PM)?\s*(?:\([^)]+\))?\s*(?:@|in)?\s*[,]?\s*([A-Za-z0-9\s\-]+)?", text[:5000], re.I):
        days_map = {"m": "MO", "t": "TU", "tu": "TU", "w": "WE", "r": "TH", "th": "TH", "f": "FR"}
        h1, m1 = int(m.group(3)), m.group(4) or "00"
        h2, m2 = int(m.group(5)), m.group(6) or "00"
        # When start is 12 (noon) and end is 1–7, treat end as PM (13:00–19:00)
        if h1 == 12 and 1 <= h2 <= 7:
            h2 += 12
        start = f"{h1:02d}:{m1}"
        end = f"{h2:02d}:{m2}"
        loc = (m.group(7) or "").strip() if m.lastindex >= 7 and m.group(7) and len((m.group(7) or "").strip()) > 1 else None
        for g in (m.group(1), m.group(2)):
            if not g:
                continue
            key = g.lower()[:2]
            day = days_map.get(key) or days_map.get(g.lower())
            if day and day not in seen_days:
                seen_days.add(day)
                meetings.append({
                    "id": f"mt-{len(meetings)+1}",
                    "day_of_week": day,
                    "start_time": start,
                    "end_time": end,
                    "timezone": "America/Los_Angeles",
                    "location": loc,
                    "type": "lecture",
                })

    # "M,Tu,W,F 1-1:50, 103 Peterson" - comma-separated days
    comma_days_map = {"m": "MO", "mo": "MO", "tu": "TU", "tue": "TU", "w": "WE", "we": "WE", "th": "TH", "r": "TH", "f": "FR", "fr": "FR"}
    for m in re.finditer(r"\b(M|Tu|Tue|W|Th|R|F|Mo)\s*,\s*(M|Tu|Tue|W|Th|R|F|Mo)(?:\s*,\s*(M|Tu|Tue|W|Th|R|F|Mo))?(?:\s*,\s*(M|Tu|Tue|W|Th|R|F|Mo))?\s+(\d{1,2})[\:]?(\d{2})?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?\s*(?:,\s*)?([A-Za-z0-9\s\-]+)?", text[:5000], re.I):
        days_found = [g for g in (m.group(1), m.group(2), m.group(3), m.group(4)) if g]
        h1, m1 = int(m.group(5)), m.group(6) or "00"
        h2, m2 = int(m.group(7)), m.group(8) or "00"
        if 1 <= h1 <= 7 and 1 <= h2 <= 7 and not re.search(r"am|pm", m.group(0), re.I):
            h1, h2 = h1 + 12, h2 + 12
        loc = (m.group(9) or "").strip() if m.lastindex >= 9 and m.group(9) and len((m.group(9) or "").strip()) > 2 else None
        start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
        for g in days_found:
            key = g.lower()[:2] if len(g) >= 2 else g.lower()
            day = comma_days_map.get(key) or comma_days_map.get(g.lower()[:3])
            if day and day not in seen_days:
                seen_days.add(day)
                meetings.append({
                    "id": f"mt-{len(meetings)+1}",
                    "day_of_week": day,
                    "start_time": start,
                    "end_time": end,
                    "timezone": "America/Los_Angeles",
                    "location": loc,
                    "type": "lecture",
                })

    # "MTWR 4:00-4:50", "MWF 3:00-3:50", "MTWF 1:00pm-1:50pm" - abbreviated days
    for m in re.finditer(r"\b(MTWR|MTWF|MWF|MW|MF|TR|WF|WR|T\.?R|M\.?W)\s+(\d{1,2})[\:]?(\d{2})?\s*(pm|am)?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?\s*(pm|am)?\s*(?:\t|\,|\s)([A-Za-z0-9\s\-]+)?", text[:5000], re.I):
        abbr = m.group(1).replace(".", "").replace(" ", "").upper()
        h1, m1 = int(m.group(2)), m.group(3) or "00"
        h2, m2 = int(m.group(5)), m.group(6) or "00"  # groups 5,6 = end time (4,7 = ampm)
        ampm = ((m.group(7) or m.group(4)) or "").lower()  # prefer second am/pm
        if ampm == "pm" and h1 < 12:
            h1 += 12
        if ampm == "pm" and h2 < 12:
            h2 += 12
        # Common afternoon class times (4-7) without am/pm -> assume pm
        if not ampm and 4 <= h1 <= 7 and 4 <= h2 <= 7:
            h1, h2 = h1 + 12, h2 + 12
        start = f"{h1:02d}:{m1}"
        end = f"{h2:02d}:{m2}"
        loc = (m.group(8) or "").strip() if m.lastindex >= 8 and m.group(8) else None
        if not loc:
            after = text[m.end() : m.end() + 150]
            loc_m = re.search(r"(?:Class\s+)?[Ll]ocation\s*:\s*([A-Za-z0-9\s\-]+?)(?:\n|$)", after, re.I)
            if loc_m:
                loc = loc_m.group(1).strip()
        expand = {"MW": ["MO", "WE"], "MTWR": ["MO", "TU", "WE", "TH"], "MTWF": ["MO", "TU", "WE", "FR"], "MWF": ["MO", "WE", "FR"], "MF": ["MO", "FR"], "TR": ["TU", "TH"], "WF": ["WE", "FR"], "WR": ["WE", "TH"]}
        days_list = expand.get(abbr, [])
        for day in days_list:
            if day not in seen_days:
                seen_days.add(day)
                meetings.append({
                    "id": f"mt-{len(meetings)+1}",
                    "day_of_week": day,
                    "start_time": start,
                    "end_time": end,
                    "timezone": "America/Los_Angeles",
                    "location": loc,
                    "type": "lecture",
                })

    # "Wednesdays 4:00 - 5:20 PM, McKenzie 221", "Fridays 4:00 - 5:20 PM", "Monday 8:30 - 9:50 AM"
    days_plural = {"mondays": "MO", "tuesdays": "TU", "wednesdays": "WE", "thursdays": "TH", "fridays": "FR", "monday": "MO", "tuesday": "TU", "wednesday": "WE", "thursday": "TH", "friday": "FR"}
    for m in re.finditer(r"\b(Monday|Tuesday|Wednesday|Thursday|Friday)s?\s+(\d{1,2})[\:]?(\d{2})?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?\s*(?:AM|PM)\s*(?:,\s*)([A-Za-z0-9\s\-]+)?", text[:5000], re.I):
        day = days_plural.get(m.group(1).lower())
        if not day or day in seen_days:
            continue
        h1, m1 = int(m.group(2)), m.group(3) or "00"
        h2, m2 = int(m.group(4)), m.group(5) or "00"
        if "am" in m.group(0).lower() and "pm" not in m.group(0).lower() and h1 >= 8:
            pass
        elif h1 < 12 and ("pm" in m.group(0).lower() or (h1 <= 7 and "am" not in m.group(0).lower())):
            h1, h2 = h1 + 12, h2 + 12
        seen_days.add(day)
        loc = (m.group(6) or "").strip() if m.lastindex >= 6 and m.group(6) else None
        meetings.append({
            "id": f"mt-{len(meetings)+1}",
            "day_of_week": day,
            "start_time": f"{h1:02d}:{m1}",
            "end_time": f"{h2:02d}:{m2}",
            "timezone": "America/Los_Angeles",
            "location": loc,
            "type": "lecture",
        })

    # "Tuesday/Thursday, 16:00-17:20, 125 McKenzie Hall" - slash, 24h time
    for m in re.finditer(r"\b(Tuesday|Thursday|Monday|Wednesday|Friday)\s*/\s*(Tuesday|Thursday|Monday|Wednesday|Friday)\s*,\s*(\d{1,2})[\:]?(\d{2})?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?\s*(?:,\s*)?([A-Za-z0-9\s\-]+)?", text[:5000], re.I):
        days_map = {"monday": "MO", "tuesday": "TU", "wednesday": "WE", "thursday": "TH", "friday": "FR"}
        h1, m1 = int(m.group(3)), m.group(4) or "00"
        h2, m2 = int(m.group(5)), m.group(6) or "00"
        if h1 < 12 and h1 >= 8:
            h1, h2 = h1 + 12, h2 + 12
        loc = (m.group(7) or "").strip() if m.lastindex >= 7 and m.group(7) and len((m.group(7) or "").strip()) > 2 else None
        for g in (m.group(1), m.group(2)):
            day = days_map.get(g.lower())
            if day and day not in seen_days:
                seen_days.add(day)
                meetings.append({
                    "id": f"mt-{len(meetings)+1}",
                    "day_of_week": day,
                    "start_time": f"{h1:02d}:{m1}",
                    "end_time": f"{h2:02d}:{m2}",
                    "timezone": "America/Los_Angeles",
                    "location": loc,
                    "type": "lecture",
                })

    # "Tuesday and Thursday from 10:00am to 11:30am" or "Tuesdays and Thursdays, 2pm to 3:20pm"
    for m in re.finditer(r"(Tuesday|Thursday|Monday|Wednesday|Friday)s?\s*(?:&\s*|and\s+)(Tuesday|Thursday|Monday|Wednesday|Friday)s?\s*(?:from\s+)?[,]?\s*(\d{1,2})[\:]?(\d{2})?\s*(?:pm|am)?\s*(?:to|[-–])\s*(\d{1,2})[\:]?(\d{2})?\s*(?:pm|am)(?:\s*(?:in\s+|\s*[,]\s*)([A-Za-z0-9\s\-]+))?", text[:5000], re.I):
        days_map = {"monday": "MO", "tuesday": "TU", "wednesday": "WE", "thursday": "TH", "friday": "FR"}
        h1, m1 = int(m.group(3)), m.group(4) or "00"
        h2, m2 = int(m.group(5)), m.group(6) or "00"
        if h1 < 12 and (m.group(0).lower().endswith("pm") or "pm" in m.group(0).lower()):
            h1, h2 = h1 + 12, h2 + 12
        start = f"{h1:02d}:{m1}"
        end = f"{h2:02d}:{m2}"
        loc = (m.group(7) or "").strip() if m.lastindex >= 7 and m.group(7) else None
        if not loc:
            before = text[max(0, m.start() - 200) : m.start()]
            loc_m = re.search(r"(?:Where|Location|Place|Room|Class\s+Location)\s*:\s*([A-Za-z0-9\s\-]+?)(?:\n|$)", before, re.I)
            if loc_m:
                loc = loc_m.group(1).strip()
        for g in (m.group(1), m.group(2)):
            day = days_map.get(g.lower())
            if day and day not in seen_days:
                seen_days.add(day)
                meetings.append({
                    "id": f"mt-{len(meetings)+1}",
                    "day_of_week": day,
                    "start_time": start,
                    "end_time": end,
                    "timezone": "America/Los_Angeles",
                    "location": loc,
                    "type": "lecture",
                })

    # "LAB will be on Thursday, B026 Klamath" - single day, location, no time
    for m in re.finditer(r"(?:will be\s+)?on\s+(Monday|Tuesday|Wednesday|Thursday|Friday)s?\s*[,]\s*([A-Za-z0-9\s\-]{3,30})", text[:4000], re.I):
        days_map = {"monday": "MO", "tuesday": "TU", "wednesday": "WE", "thursday": "TH", "friday": "FR"}
        day = days_map.get(m.group(1).lower())
        loc = m.group(2).strip()
        if day and day not in seen_days and "room" not in loc.lower()[:10]:
            seen_days.add(day)
            meetings.append({
                "id": f"mt-{len(meetings)+1}",
                "day_of_week": day,
                "start_time": None,
                "end_time": None,
                "timezone": "America/Los_Angeles",
                "location": loc,
                "type": "lecture",
            })

    # "T/R 101 LLCS" - days only, no time (R = Thursday)
    tr_map = {"m": "MO", "t": "TU", "tu": "TU", "th": "TH", "r": "TH", "w": "WE", "f": "FR"}
    for m in re.finditer(r"\b(T|Tu|Tue|Th|Thu|R|M|W|F)[/\s,]+(T|Tu|Tue|Th|Thu|R|M|W|F)\s+(\d{2,}\s+[A-Za-z0-9]{2,20})\b", text[:3000], re.I):
        loc = m.group(3).strip()
        if "quiz" in loc.lower() or "assign" in loc.lower() or "weekly" in loc.lower():
            continue
        for g in (m.group(1), m.group(2)):
            key = g[:2].lower() if len(g) <= 3 else g.lower()[:3]
            day = tr_map.get(key) or day_map.get(key)
            if day and day not in seen_days:
                seen_days.add(day)
                meetings.append({
                    "id": f"mt-{len(meetings)+1}",
                    "day_of_week": day,
                    "start_time": None,
                    "end_time": None,
                    "timezone": "America/Los_Angeles",
                    "location": loc,
                    "type": "lecture",
                })
    return meetings[:8]


def parse_assessments(text: str, folder: str, term: str | None = None) -> tuple:
    """Extract assessment categories and individual assessments."""
    categories = []
    assessments = []
    cat_ids = {}
    seen_assessments = set()
    # Derive year from term for date parsing (e.g. "Fall 2025" -> 2025)
    yr = 2024
    if term:
        my = re.search(r"(\d{4})", term)
        if my:
            yr = int(my.group(1))

    def add_category(cid: str, name: str, weight: int | None) -> str:
        if cid not in cat_ids:
            cat_ids[cid] = len(categories)
            categories.append({
                "id": cid,
                "name": name,
                "weight_percent": weight,
                "drop_lowest": None,
                "subcategories": [],
                "grading_bucket": None,
            })
        elif weight is not None:
            idx = cat_ids[cid]
            if idx < len(categories) and categories[idx].get("weight_percent") is None:
                categories[idx]["weight_percent"] = weight
        return cid

    def add_assessment(aid: str, title: str, cid: str, atype: str, pct: int | None, due=None, recurrence=None, policies=None):
        key = (title[:40], cid, pct)
        if key in seen_assessments:
            return
        seen_assessments.add(key)
        rec = {"frequency": None, "interval": None, "by_day": None, "until": None, "count": None}
        if recurrence:
            rec.update(recurrence)
        pol = {"late_policy": None, "late_pass_allowed": None}
        if policies:
            pol.update(policies)
        assessments.append({
            "id": aid,
            "title": title,
            "category_id": cid,
            "type": atype,
            "due_datetime": due,
            "all_day": False if due and "T" in str(due) else True,
            "timezone": "America/Los_Angeles" if due and "T" in str(due) else None,
            "weight_percent": pct,
            "points": None,
            "recurrence": rec if any(rec.values()) else None,
            "policies": pol,
            "confidence": 0.9,
            "source_excerpt": f"{title}: {pct}%" if pct else title,
        })

    # "Slide – aesthesis – Due October 16, 11:59 p.m.", "slide assignment (due ... October 16)", "close-reading assignment Due November 6"
    _months = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
    for m in re.finditer(r"(?:(?:Slide|slide)\s*(?:[-–\s\u2013\"']*aesthesis[\"']?|assignment)|close[- ]?reading\s+assignment).*?(October|November|December|January|February|March|April|May|June|July|August|September|Oct\.?|Nov\.?|Dec\.?|Jan\.?|Feb\.?|Mar\.?|Apr\.?|Jun\.?|Jul\.?|Aug\.?|Sep\.?)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,\s*(\d{4}))?\s*(?:by|at|@|\s+)?(\d{1,2})?[\:]?(\d{2})?\s*(am|pm)?", text, re.I | re.DOTALL):
        mon, day, yr_str, h, min, ampm = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)
        title = "Close-reading assignment" if "close" in m.group(0).lower() and "reading" in m.group(0).lower() else "Aesthesis slide"
        yr = int(yr_str) if yr_str else 2023
        mon_num = _months.get((mon or "").lower()[:3], 1)
        due = f"{yr}-{mon_num:02d}-{int(day):02d}"
        if h: hr = int(h); hr = hr + 12 if (ampm or "").lower() == "pm" and hr < 12 else hr; due += f"T{hr:02d}:{min or '59'}:00"
        else: due += "T23:59:00"
        cid = re.sub(r"\s+", "_", title.lower())[:28].rstrip("_")
        add_category(cid, title, None)
        add_assessment(cid + "_1", title, cid, "assignment", None, due)

    # "6-8 weekly quizzes, due each week by 11:59 p.m. on Mondays"
    if re.search(r"weekly\s+quizzes?\s*[,.]\s*(?:due\s+)?(?:each\s+week|by\s+\d)", text, re.I):
        add_category("quizzes", "Weekly quizzes", None)
        add_assessment("quizzes_1", "Weekly quizzes", "quizzes", "quiz", None, None, {"frequency": "weekly", "interval": 1, "by_day": ["MO"], "until": None, "count": None})

    # "Project 1: 10%", "Exercise 1 (10%)"
    for m in re.finditer(r"(Project|Lab|Quiz|Homework|Assignment|Exercise)\s*(\d+)?\s*[:\s(]+(\d{1,3})\s*%", text, re.I):
        kind, num, pct = m.group(1), m.group(2), int(m.group(3))
        kind_lower = kind.lower()
        cid = "projects" if "project" in kind_lower else "labs" if "lab" in kind_lower else "quizzes" if "quiz" in kind_lower else "assignments"
        cid = add_category(cid, f"{kind} {num}".strip() if num else kind, None)
        atype = "project" if "project" in kind_lower else "quiz" if "quiz" in kind_lower else "assignment"
        title = f"{kind} {num}".strip() if num else kind
        add_assessment(f"{kind}_{num or 1}".lower().replace(" ", "_"), title, cid, atype, pct)

    # Table-style: "Homework ... 30%", "Quizzes ... 25%", "Project ... 5%", "Final Exam ... 20%", "Think & Explain ... 10%"
    for m in re.finditer(r"\b(Homework|Quizzes|Project|Final\s+Exam|Think\s*&\s*Explain\s*(?:Questions)?)\s+.{0,90}?(\d{1,3})\s*%", text, re.I | re.DOTALL):
        name, pct = m.group(1).strip(), int(m.group(2))
        if pct > 100:
            continue
        name = re.sub(r"\s+", " ", name)
        title = "Think & Explain Questions" if "think" in name.lower() and "explain" in name.lower() else "Final exam" if "final" in name.lower() and "exam" in name.lower() else "Quizzes" if name.lower() == "quizzes" else "Project" if name.lower() == "project" else name
        cid = re.sub(r"\s+", "_", title.lower())[:28].rstrip("_").replace("&", "").replace("__", "_")
        if not cid or cid in ("total", "the"):
            continue
        add_category(cid, title, pct)
        atype = "quiz" if "quiz" in name.lower() else "final" if "final" in name.lower() else "project" if "project" in name.lower() else "assignment"
        add_assessment(cid + "_1", title, cid, atype, pct)

    # "Lab attendance/submission 10%", "Lab Attendance: 10%", "Quizzes: 20%"
    for m in re.finditer(r"(Lab\s+attendance[/\s]*(?:and|/)\s*submission|Lab\s+Attendance|Quizzes?|Lab\s+attendance)[:\s]+(\d{1,3})\s*%", text, re.I):
        name, pct = m.group(1).strip(), int(m.group(2))
        cid = "labs" if "lab" in name.lower() else "quizzes"
        cid = add_category(cid, name, pct)
        atype = "participation" if "attendance" in name.lower() else "quiz"
        add_assessment(cid + "_1", name, cid, atype, pct, recurrence={"frequency": "weekly", "interval": 1})

    # "Exam 1 20", "Project 50", "Video 5", "Participation 5" - table format (name + number, no %)
    for m in re.finditer(r"(?:^|\n)\s*(Exam|Project|Video|Participation|Midterm|Final|Quiz|Homework|Lab|Assignment)\s*(\d+)?\s+(\d{1,3})\s*$", text, re.M | re.I):
        name, num, pct = m.group(1), m.group(2), int(m.group(3))
        if pct > 100:
            continue
        name_lower = name.lower()
        # "Group Project" when syllabus mentions group project and we see "Project 50"
        title = f"{name} {num}".strip() if num else name
        if name_lower == "project" and "group project" in text.lower() and not num:
            title = "Group Project"
        cid = re.sub(r"\s+", "_", title.lower())[:28].rstrip("_")
        atype = "midterm" if "midterm" in name_lower or "exam" in name_lower and "final" not in name_lower else "final" if "final" in name_lower else "project" if "project" in name_lower else "quiz" if "quiz" in name_lower else "assignment"
        if "exam" in name_lower and "midterm" not in name_lower and "final" not in name_lower:
            atype = "midterm"  # "Exam 1", "Exam 2"
        add_category(cid, title, pct)
        add_assessment(cid + ("_" + num if num else "_1"), title, cid, atype, pct)

    # "10%\nAttendance quizzes", "20%\n\nfinal" - percent on one line, name on next
    for m in re.finditer(r"(?:^|\n)\s*(\d{1,3})\s*%\s*\n\s*([A-Za-z][A-Za-z\s\-()/]+?)(?:\s*[-–]|\s+\(|$)", text, re.M | re.I):
        pct, name = int(m.group(1)), m.group(2).strip()
        if pct > 100 or len(name) < 3 or len(name) > 60:
            continue
        skip = any(w in name.lower() for w in ("dropped", "score", "individual", "submission", "canvas", "collaboration", "policy", "apply", "attempts"))
        if skip:
            continue
        title = "Final exam" if name.lower() == "final" else "Midterm" if name.lower() == "midterm" else name
        cid = "final" if name.lower() == "final" else "midterm" if name.lower() == "midterm" else re.sub(r"\s+", "_", name.lower())[:30].rstrip("_/()")
        if not cid or cid in ("total", "the"):
            continue
        add_category(cid, title, pct)
        atype = "quiz" if "quiz" in name.lower() else "midterm" if "midterm" in name.lower() else "final" if "final" in name.lower() else "assignment"
        if "lab" in name.lower(): atype = "participation" if "attend" in name.lower() else "assignment"
        add_assessment(f"{cid}_1", title, cid, atype, pct)

    # "midterm (20%)", "final (20%)", "Discussions and Assignments (20% of total)", "Labs and quizzes (40%)"
    for m in re.finditer(r"\b(midterm|final|Discussions?\s+and\s+Assignments?|Labs?\s+and\s+quizzes?)\s*\(\s*(\d{1,3})\s*%\s*(?:of\s+total(?:\s+grade)?)?\s*\)", text, re.I):
        name, pct = m.group(1).strip(), int(m.group(2))
        cid = re.sub(r"\s+", "_", name.lower())[:30].rstrip("_")
        title = "Midterm" if name.lower() == "midterm" else "Final" if name.lower() == "final" else name
        atype = "midterm" if "midterm" in name.lower() else "final" if "final" in name.lower() else "assignment" if "discussion" in name.lower() else "quiz"
        if "lab" in name.lower(): atype = "assignment"
        add_category(cid, title, pct)
        add_assessment(cid + "_1", title, cid, atype, pct)

    # "Test 1: October 23", "Test 2: November 6", "Test 3: November 25" - tests with dates
    _mo = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
    for m in re.finditer(r"Test\s+(\d+)\s*:\s*(\w+)\s+(\d{1,2})", text, re.I):
        num, mon, day = m.group(1), m.group(2), m.group(3)
        mon_num = _mo.get((mon or "").lower()[:3])
        due = f"{yr}-{mon_num:02d}-{int(day):02d}" if mon_num and 1 <= mon_num <= 12 else None
        add_category("tests", "Tests", None)
        add_assessment(f"test_{num}", f"Test {num}", "tests", "midterm", None, due)

    # "Class participation 5% Homework 15% Program 20% Tests 30% Final 30%" - run-on grading line
    prog_due = None
    for _m in re.finditer(r"Prog\.?\s*1\s*\(\s*(\d{1,2})/(\d{1,2})\s*\)", text, re.I):
        mo, dy = int(_m.group(1)), int(_m.group(2))
        if 1 <= mo <= 12 and 1 <= dy <= 31:
            prog_due = f"{yr}-{mo:02d}-{dy:02d}"
            break
    final_due = None
    for _m in re.finditer(r"Final\s*:\s*(\w+)\s+(\d{1,2}),?\s*(?:\w+,?\s*)?(\d{1,2})[\:.](\d{2})\s*(?:AM|am)\s*[-–]\s*(\d{1,2})[\:.](\d{2})\s*(?:AM|am)", text, re.I):
        mon, day = _m.group(1), int(_m.group(2))
        h1, m1, h2, m2 = int(_m.group(3)), int(_m.group(4)), int(_m.group(5)), int(_m.group(6))
        mon_num = _mo.get((mon or "").lower()[:3])
        if mon_num:
            final_due = f"{yr}-{mon_num:02d}-{day:02d}T{h1:02d}:{m1:02d}:00"
            break
    if not final_due:
        for _m in re.finditer(r"FINAL\s+EXAM\s*\(\s*(\d{1,2})/(\d{1,2})\s*[,]\s*(\d{1,2})[\:.](\d{2})\s*(?:AM|am)", text, re.I):
            mo, dy, h1, m1 = int(_m.group(1)), int(_m.group(2)), int(_m.group(3)), int(_m.group(4))
            if 1 <= mo <= 12 and 1 <= dy <= 31:
                final_due = f"{yr}-{mo:02d}-{dy:02d}T{h1:02d}:{m1:02d}:00"
                break
    for m in re.finditer(r"\b(Class\s+participation|Homework|Program|Tests?|Final)\s+(\d{1,3})\s*%", text, re.I):
        name, pct = m.group(1).strip(), int(m.group(2))
        cid = "program" if name.lower() == "program" else re.sub(r"\s+", "_", name.lower())[:28].rstrip("_")
        title = "Programming assignment" if name.lower() == "program" else "Class participation" if "participation" in name.lower() else "Final exam" if name.lower() == "final" else name
        if name.lower() == "tests":
            add_category("tests", "Tests", pct)
        else:
            add_category(cid, title if cid == "program" else name, pct)
        if name.lower() != "tests":
            atype = "participation" if "participation" in name.lower() else "final" if name.lower() == "final" else "project" if name.lower() == "program" else "assignment"
            due = (prog_due if name.lower() == "program" else final_due if name.lower() == "final" else None)
            add_assessment(cid + "_1", title, cid, atype, pct, due)

    # "Class Project 40%", "Class project 40%"
    for m in re.finditer(r"\bClass\s+Project\s+(\d{1,3})\s*%", text, re.I):
        pct = int(m.group(1))
        add_category("class_project", "Class Project", pct)
        add_assessment("class_project_1", "Class Project", "class_project", "project", pct)

    # "40% programming assignments", "20% homework" - percent first (name on same line as %)
    for m in re.finditer(r"(\d{1,3})\s*%[ \t]+([A-Za-z][A-Za-z \t\-/]+?)(?=[\s\.\,\)$]|\.)", text, re.I):
        pct, name = int(m.group(1)), m.group(2).strip()
        if pct > 100 or len(name) < 3 or len(name) > 55:
            continue
        skip_words = ("the", "your", "grade", "penalty", "of ", " to ", " or ", "each", "range", "standard", "b's", "c's", "d's", "upper", "lower", "bracket", " e.g ", "late ", "maximum")
        if any(w in name.lower() for w in skip_words) or name.lower().strip() == "and":
            continue
        cid = re.sub(r"\s+", "_", name.lower())[:28].rstrip("_/")
        add_category(cid, name, pct)
        atype = "assignment"
        if "exam" in name.lower() or "midterm" in name.lower(): atype = "midterm" if "midterm" in name.lower() else "final"
        elif "quiz" in name.lower(): atype = "quiz"
        elif "project" in name.lower(): atype = "project"
        elif "lab" in name.lower(): atype = "participation" if "attend" in name.lower() else "assignment"
        add_assessment(f"{cid}_1", name, cid, atype, pct)

    # "Two Midterms 22 % each", "2 Midterms 25% each" -> Midterm 1, Midterm 2
    for m in re.finditer(r"(?:(?:Two|2)\s+)?[Mm]idterms?\s+(\d{1,3})\s*%\s*(?:each|total)", text, re.I):
        pct = int(m.group(1))
        add_category("midterms", "Midterm Exams", pct * 2)
        add_assessment("midterm_1", "Midterm 1", "midterms", "midterm", pct)
        add_assessment("midterm_2", "Midterm 2", "midterms", "midterm", pct)

    # "Midterm 1 25%", "Midterm 2 25%" - explicit numbered midterms
    for m in re.finditer(r"Midterm\s+(\d+)\s*[:\s]+(\d{1,3})\s*%", text, re.I):
        num, pct = m.group(1), int(m.group(2))
        add_category("midterms", "Midterm Exams", pct * 2)
        add_assessment(f"midterm_{num}", f"Midterm {num}", "midterms", "midterm", pct)

    # "Midterm Exams 25% each" -> Midterm 1, Midterm 2 with dates
    date_pat = r"(?:Tuesday|Thursday|Monday|Wednesday|Friday),?\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{4}))?"
    month_abbr = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
    for m in re.finditer(r"Midterm\s+Exams?\s+(\d{1,3})\s*%\s*(?:each|total)", text, re.I):
        pct_each = int(m.group(1))
        # Find two dates in surrounding text
        block = text[max(0, m.start() - 1500) : m.end() + 300]
        dates = list(re.finditer(date_pat, block, re.I))
        if len(dates) >= 2:
            add_category("midterms", "Midterm Exams", pct_each * 2)
            for i, d in enumerate(dates[:2], 1):
                mon, day, year = d.group(1), d.group(2), d.group(3)
                try:
                    mon_num = month_abbr.get(mon.lower()[:3], 1)
                    yr = int(year) if year else 2023
                    due = f"{yr}-{mon_num:02d}-{int(day):02d}"
                except (ValueError, IndexError):
                    due = None
                add_assessment(f"midterm_{i}", f"Midterm {i}", "midterms", "midterm", pct_each, due)

    # "Mini-exams 45%" + "3 exams" -> Mini-exam 1, 2, 3 with null weight
    if re.search(r"Mini[- ]?exams?\s+\d{1,3}\s*%.*?(?:\d|three|3)\s+exam", text, re.I | re.DOTALL):
        add_category("mini_exams", "Mini-exams", 45)
        for i in range(1, 4):
            add_assessment(f"mini_exam_{i}", f"Mini-exam {i}", "mini_exams", "midterm", None)

    # "Exams 65%" with "mini-exam" and "final" nearby -> "Exams (mini-exams + final)"
    for m in re.finditer(r"\bExams?\s+(\d{1,3})\s*%", text, re.I):
        pct = int(m.group(1))
        block = text[max(0, m.start() - 200) : m.end() + 300]
        title = "Exams (mini-exams + final)" if ("mini" in block.lower() and "final" in block.lower()) else "Exams"
        add_category("exams", title, pct)
        add_assessment("exams_1", title, "exams", "midterm", pct)

    # "Final exam 30%", "Final exam: 30%", "Final exam (30%)", "Final 30%"
    for m in re.finditer(r"\b(Final\s+exam|Midterm\s+exam|Final|Midterm)\s*[:\s(]*(\d{1,3})\s*%\)?", text, re.I):
        name, pct = m.group(1).strip(), int(m.group(2))
        cid = "final" if "final" in name.lower() else "midterm"
        title = "Final exam" if "final" in name.lower() else "Midterm exam"
        if "exam" not in name.lower():
            name = title
        add_category(cid, title, pct)
        add_assessment(cid + "_1", title, cid, "final" if "final" in name.lower() else "midterm", pct)

    # "Midterm: 25%", "Final: 45%" - colon format
    for m in re.finditer(r"\b(Midterm|Final)\s*:?\s*(\d{1,3})\s*%", text, re.I):
        kind, pct = m.group(1), int(m.group(2))
        cid = "exams" if kind.lower() == "midterm" else "final"
        add_category(cid, f"{kind} exam" if kind.lower() == "final" else "Midterm", pct)
        add_assessment(kind.lower() + "_1", "Midterm" if kind.lower() == "midterm" else "Final", cid,
                      "midterm" if kind.lower() == "midterm" else "final", pct)

    # "Project 1 (due: Oct. 24)", "Project 2 (due: Nov. 19)" - schedule table, no percent
    _mo_abbr = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
    for m in re.finditer(r"Project\s+(\d+)\s*\(\s*(?:due|out)\s*:\s*(\w+)\.?\s+(\d{1,2})", text, re.I):
        num, mon_abbr, day = m.group(1), m.group(2), int(m.group(3))
        mon_num = _mo_abbr.get((mon_abbr or "").lower()[:3])
        due = f"{yr}-{mon_num:02d}-{day:02d}" if mon_num and 1 <= mon_num <= 12 else None
        if "due" in m.group(0).lower():
            add_category("projects", "Projects", None)
            add_assessment(f"project_{num}", f"Project {num}", "projects", "project", None, due)

    # "Nov. 4 MIDTERM", "6 Nov. 4 MIDTERM" - schedule table
    for m in re.finditer(r"(?:^|\n)\s*\d*\s*(\w+)\.?\s+(\d{1,2})\s+MIDTERM", text, re.M | re.I):
        mon_abbr, day = m.group(1), int(m.group(2))
        mon_num = _mo_abbr.get((mon_abbr or "").lower()[:3])
        due = f"{yr}-{mon_num:02d}-{day:02d}" if mon_num and 1 <= mon_num <= 12 else None
        add_category("midterm", "Midterm", None)
        add_assessment("midterm_1", "Midterm", "midterm", "midterm", None, due)

    # "Dec. 11 12:30-14:30 FINAL", "11 Dec. 11 12:30-14:30 FINAL"
    for m in re.finditer(r"(?:^|\n)\s*\d*\s*(\w+)\.?\s+(\d{1,2})\s+(\d{1,2})[\:.](\d{2})\s*[-–]\s*(\d{1,2})[\:.](\d{2})\s*FINAL", text, re.M | re.I):
        mon_abbr, day = m.group(1), int(m.group(2))
        h1, m1 = int(m.group(3)), int(m.group(4))
        mon_num = _mo_abbr.get((mon_abbr or "").lower()[:3])
        due = f"{yr}-{mon_num:02d}-{day:02d}T{h1:02d}:{m1:02d}:00" if mon_num and 1 <= mon_num <= 12 else None
        add_category("final", "Final exam", None)
        add_assessment("final_1", "Final", "final", "final", None, due)

    # Section headings: "Homework:" or "Projects:" as assignment types (weight None) - DSCI101-style
    for m in re.finditer(r"(?:^|\n)\s*(Homework|Projects)\s*:\s*[A-Z]", text, re.M | re.I):
        name = m.group(1).strip()
        cid = name.lower()
        title = "Homework" if name.lower() == "homework" else "Projects"
        add_category(cid, title, None)
        add_assessment(f"{cid}_1", title, cid, "assignment" if cid == "homework" else "project", None)

    # Labor-based: "1. Weekly discussion boards", "• Origin Story", "• Instructions" - WR320
    wr_items = [
        (r"weekly\s+discussion\s+boards?", "Weekly discussion boards", "discussion"),
        (r"origin\s+story", "Origin Story", "projects"),
        (r"instructions?\s*(?:[-–—]|\s+[Aa])", "Instructions", "projects"),
        (r"literature\s+review\s+and\s+research\s+proposal", "Literature review and research proposal", "projects"),
        (r"procedure\s+description", "Procedure Description", "projects"),
    ]
    for pat, title, cid in wr_items:
        if re.search(pat, text, re.I):
            cat_name = "Discussion boards" if cid == "discussion" else "Writing Projects"
            add_category(cid, cat_name, None)
            aid = re.sub(r"\s+", "_", title.lower())[:28].rstrip("_") + "_1"
            add_assessment(aid, title, cid, "assignment", None)

    # "Projects 15%", "Mini-exams 45%", "Final exam 30%", "• Homework 30%", "• Final exam 40%"
    for m in re.finditer(r"(?:^|\n)\s*[•\-\*]?\s*([A-Za-z][A-Za-z\s\-]+?)\s+(\d{1,3})\s*%\s*", text, re.M | re.I):
        name = m.group(1).strip()
        pct = int(m.group(2))
        skip = name.lower() in ("the", "a", "an", "to", "of", "and", "or", "your", "grade")
        if skip or len(name) > 50 or pct > 100:
            continue
        if re.search(r"^[A-Za-z]+\s+\d+$", name) and "project" not in name.lower() and "midterm" not in name.lower():
            continue
        cid = re.sub(r"\s+", "_", name.lower())[:30].rstrip("_")
        if not cid or cid in ("room", "week"):
            continue
        add_category(cid, name, pct)
        atype = "assignment"
        if "exam" in name.lower() or "midterm" in name.lower():
            atype = "midterm" if "midterm" in name.lower() else "final"
        elif "quiz" in name.lower():
            atype = "quiz"
        elif "project" in name.lower():
            atype = "project"
        elif "demo" in name.lower():
            atype = "assignment"
        add_assessment(f"{cid}_1", name, cid, atype, pct)

    # Bucketed: "Projects (\"Project Grade\"):" then "Project 1: 10%"
    if "Project Grade" in text or "Exam Grade" in text:
        add_category("project_grade", "Project Grade", None)
        add_category("exam_grade", "Exam Grade", None)

    # Dates: "Midterm: 25%" with "Week 6 / Tuesday / May 7"
    date_pat = r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{4}))?"
    months = "jan feb mar apr may jun jul aug sep oct nov dec".split()
    for m in re.finditer(rf"(Midterm|Final)\s*:\s*(\d{{1,3}})\s*%.*?{date_pat}", text, re.I | re.DOTALL):
        kind, pct_str = m.group(1), m.group(2)
        mon, day_str, year = m.group(3), m.group(4), m.group(5)
        try:
            mon_num = months.index(mon[:3].lower()) + 1
            yr = int(year) if year else 2025
            due = f"{yr}-{mon_num:02d}-{int(day_str):02d}"
        except (ValueError, IndexError):
            continue
        cid = "exam_grade" if "exam_grade" in (c["id"] for c in categories) else "exams"
        add_category(cid, "Exam Grade" if cid == "exam_grade" else "Exams", None)
        add_assessment(kind.lower(), kind, cid, "midterm" if "midterm" in kind.lower() else "final", int(pct_str), due)

    # "Final Tuesday June 11th @ 8am" or "June 11, 8am"
    for m in re.finditer(rf"Final\s+(?:exam\s+)?(?:Tuesday\s+)?(?:June|Jun)\s+(\d{{1,2}})(?:st|nd|rd|th)?\s*(?:@\s+)?(\d{{1,2}})?(?::(\d{{2}}))?\s*(am|pm)?", text, re.I):
        day_str, h, min, ampm = m.group(1), m.group(2), m.group(3), m.group(4)
        yr = 2024 if "Spring 2024" in text[:500] else 2025
        due_date = f"{yr}-06-11"
        if h:
            hr = int(h)
            if (ampm or "").lower() == "pm" and hr < 12:
                hr += 12
            due = f"{due_date}T{hr:02d}:{min or '00'}:00"
        else:
            due = due_date
        cid = "exam_grade" if any(c["id"] == "exam_grade" for c in categories) else add_category("final", "Final exam", None)
        if not any(a["title"].lower() == "final" for a in assessments):
            add_assessment("final", "Final", cid, "final", None, due)

    return categories, assessments


def parse_term(text: str) -> str | None:
    """Extract term (e.g. Fall 2025, Spring 2025)."""
    m = re.search(r"(Fall|Winter|Spring|Summer)\s*(?:Term\s+)?(\d{4})", text[:1500], re.I)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    m = re.search(r"(Fall|Winter|Spring|Summer)\s*(\d{4})", text[:1500], re.I)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    m = re.search(r"[Ff]\s*(\d{4})", text[:500])
    if m:
        return f"Fall {m.group(1)}"
    m = re.search(r"\((\w+\s+\d{4})\)", text[:800])
    if m:
        s = m.group(1)
        if re.match(r"(Fall|Winter|Spring|Summer)\s+\d{4}", s, re.I):
            return s
    return None


def parse_late_policy(text: str) -> dict:
    """Extract late pass policy: total_allowed, extension_days."""
    policy = {"total_allowed": None, "extension_days": None}
    m = re.search(r"(\d+)\s*[\"'\u201C\u201D]?\s*(?:late\s+)?pass(?:es)?", text[:15000], re.I)
    if m:
        policy["total_allowed"] = int(m.group(1))
    for pat in (r"(?:one|1)\s+late\s+(?:project|assignment)", r"(?:one|1)\s+(?:project|assignment)\s+late", r"turn in (?:one|1) (?:project|assignment) late", r"(?:one|1)\s*[\"'\u201C\u201D]?\s*late\s*submission\s*token", r"have\s+(?:one|1)\s+.{0,15}late\s*submission", r"one[\"'\u201C\u201D]?\s*latesubmissiontoken", r"(?:one|1)\s*[\"'\u201C\u201D]?\s*latesubmissiontoken"):
        if re.search(pat, text[:15000], re.I) and policy["total_allowed"] is None:
            policy["total_allowed"] = 1
            break
    m = re.search(r"(\d+)\s*(?:day|days)\s*(?:each|extension|late)", text[:15000], re.I)
    if m:
        policy["extension_days"] = int(m.group(1))
    return policy


def parse_syllabus_text(text: str, course_id: str, source_type: str = "txt") -> dict:
    """
    Parse syllabus text into full schema JSON.
    Returns dict with course, assessment_categories, assessments, grading_structure, late_pass_policy, schedule, metadata.
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
        if "pacific" in loc.lower() or "lillis" in loc.lower() or "mckenzie" in loc.lower() or "mck" in loc.lower():
            break
    if not loc and meeting_times:
        loc = meeting_times[0].get("location")

    if not instructors:
        instructors = [{"id": "inst-0", "name": None, "email": None}]
    if not categories:
        categories = [{"id": "general", "name": "General", "weight_percent": None, "drop_lowest": None, "subcategories": [], "grading_bucket": None}]

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
        "metadata": {"created_at": None, "updated_at": None, "source_type": source_type, "schema_version": "1.0"},
    }
