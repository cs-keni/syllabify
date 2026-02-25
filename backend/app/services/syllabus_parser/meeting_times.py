"""
Meeting times extraction: day, start, end, location.
Distinguishes class/lecture meetings from instructor and TA office hours.
"""
import re

# Day-name words or fragments that often appear as location when regex captures too much
_DAY_WORDS = re.compile(
    r"^(?:mon|tues?|wed(?:nes)?|thu(?:rs)?|fri|sat|sun)?days?\s*\d*|"
    r"^[a-z]*days?\s*\d+|"
    r"^or\s*\d+$|"
    r"^rs?days?\s*(?:tbd)?$|"
    r"^\d+\s*$",
    re.I,
)


def _location_looks_invalid(loc: str) -> bool:
    """Return True if location is likely a parsing error (day fragment, 'or 3', etc.)."""
    if not loc or not (loc := loc.strip()):
        return True
    if len(loc) <= 2 and not loc.isdigit():
        return True
    # "or 3", "Wednesdays 10", "nesdays 10", "rsdays TBD"
    if _DAY_WORDS.search(loc):
        return True
    if re.match(r"^(?:mon|tues?|wed|thu|fri|sat|sun)", loc, re.I) and not re.search(r"\d{2,}", loc):
        return True
    # Invalid time-like "30:00" etc. mistaken as location
    if re.search(r"\d{2}\s*:\s*\d{2}", loc) and "hall" not in loc.lower() and "room" not in loc.lower():
        return True
    return False


def _abbreviate_location(loc: str) -> str:
    """Abbreviate common building names for consistent output (e.g. 180 PLC, LLCS 101)."""
    if not loc or len(loc) < 5:
        return loc
    loc_lower = loc.lower()
    # "180 Prince Lucien Campbell Hall (PLC)" or "Prince Lucien Campbell Hall (PLC)" -> "180 PLC" or "PLC"
    m = re.search(r"(\d+)\s+.*?prince lucien campbell hall\s*\(?PLC\)?", loc_lower, re.I)
    if m:
        return f"{m.group(1)} PLC"
    m = re.search(r"prince lucien campbell hall\s*\(?PLC\)?", loc_lower, re.I)
    if m:
        return "PLC"
    # "Living Learning Center South 101" -> "LLCS 101"; "101 Living Learning Center South" -> "101 LLC"
    m = re.search(r"(\d+)\s+living learning center south(?:\s+\(|\)|\s|$)", loc_lower, re.I)
    if m:
        return f"{m.group(1)} LLC"
    m = re.search(r"living learning center south\s+(\d+)", loc_lower, re.I)
    if m:
        return f"LLCS {m.group(1)}"
    # "129 McKenzie Hall (MCK)" or "129 McKenzie Hall" or "McKenzie 221"
    m = re.search(r"(\d+)\s+(?:.*?mckenzie\s*(?:hall)?|mckenzie\s*(?:hall)?)\s*\(?MCK\)?", loc_lower, re.I)
    if m:
        return f"{m.group(1)} MCK"
    m = re.search(r"(\d+)\s+mckenzie\s*(?:hall)?", loc_lower, re.I)
    if m:
        return f"{m.group(1)} MCK"
    m = re.search(r"(mckenzie|mck)\s+(\d+)", loc_lower, re.I)
    if m:
        return f"{m.group(2)} MCK"
    # "220 Deschutes", "220 DES" -> "220 DES"
    m = re.search(r"(\d+)\s+(?:deschutes|des)\b", loc_lower, re.I)
    if m:
        return f"{m.group(1)} DES"
    # "140 Tykeson", "140 TYKE" -> "140 TYKE"
    m = re.search(r"(\d+)\s+(?:tykeson|tyke)\b", loc_lower, re.I)
    if m:
        return f"{m.group(1)} TYKE"
    # "191 Allan Price Science", "191 ANS" -> "191 ANS"
    m = re.search(r"(\d+)\s+(?:allan\s+price\s+science|ans)\b", loc_lower, re.I)
    if m:
        return f"{m.group(1)} ANS"
    # "Fenton 316", "FEN 105" -> "316 fen", "105 fen" (match common test expectations)
    m = re.search(r"(?:fenton|fen)\s*(\d+)|(\d+)\s*(?:fenton|fen)\b", loc_lower, re.I)
    if m:
        num = m.group(1) or m.group(2)
        return f"{num} fen"
    # Penn State: "EAB, 102" -> "EAB 102", "E-330, Olmsted" -> "E-330 Olmsted", "Olmsted E330"
    m = re.search(r"eab\s*[,]?\s*(\d+)", loc_lower, re.I)
    if m:
        return f"EAB {m.group(1)}"
    m = re.search(r"e[-]?(\d+)\s*[,]?\s*olmsted|olmsted\s*[,]?\s*e[-]?(\d+)", loc_lower, re.I)
    if m:
        num = m.group(1) or m.group(2)
        return f"E-{num} Olmsted"
    m = re.search(r"olmsted\s+([a-z]?\d+)|([a-z]?\d+)\s+olmsted", loc_lower, re.I)
    if m:
        room = (m.group(1) or m.group(2) or "").strip()
        return f"Olmsted {room.upper()}" if room else loc
    return loc


def _normalize_location(loc: str | None) -> str | None:
    """Return None if location looks invalid (fragment/garbage), else abbreviate if known."""
    if not loc or not (loc := loc.strip()):
        return None
    # Strip trailing "Lectures", "Instructor", "Office" or newline+word (e.g. "ECJ 1.306\nInstructor" -> "ECJ 1.306")
    loc = re.sub(r"\s*\n\s*[A-Za-z]+\s*$", "", loc, re.I)
    loc = re.sub(r"\s*\n\s*Lectures\s*$", "", loc, re.I)
    loc = re.sub(r"\s+Lectures\s*$", "", loc, re.I)
    loc = loc.strip()
    if _location_looks_invalid(loc):
        return None
    return _abbreviate_location(loc) if len(loc) >= 3 else loc


def parse_meeting_times(text: str) -> list:
    """Extract structured meeting times: day, start, end, location.
    Distinguishes lecture/class meetings from instructor and TA office hours.
    """
    # Normalize hyphenated line breaks (e.g. "De-\nschutes" -> "Deschutes")
    text = re.sub(r"-\s*\n\s*", "", text)
    day_map = {
        "m": "MO", "tu": "TU", "tues": "TU", "we": "WE", "wed": "WE",
        "th": "TH", "thu": "TH", "thurs": "TH", "f": "FR", "fr": "FR", "fri": "FR",
        "sa": "SA", "su": "SU", "mo": "MO", "tue": "TU", "mtwr": None,  # MTWR = multiple
    }
    meetings = []
    seen_days = set()
    seen_oh_keys: set[tuple[str, str, str]] = set()  # (day, start, end) for office hours

    days_map = {"monday": "MO", "tuesday": "TU", "wednesday": "WE", "thursday": "TH", "friday": "FR"}

    # --- Office hours (instructor and TA): run first so we tag them before generic patterns ---
    # "Office hours: Thursdays 10-11 AM, Deschutes 362" / "Mondays 2:30-3:30 PM, Wednesdays 10:30-11:30 AM, Thursdays TBD, Deschutes 313"
    for block in re.finditer(
        r"(?:Office\s+hours?|OH)\s*:\s*([^\n]{20,200})",
        text,
        re.I,
    ):
        segment = block.group(1)
        prev = text[max(0, block.start() - 250) : block.start()]
        is_ta = bool(re.search(r"(?:^|\n)\s*TA\s*(?:\n|$)", prev, re.I))
        meeting_type = "ta_office_hours" if is_ta else "office_hours"
        # Default location from end of block (e.g. "..., Deschutes 313")
        default_loc = None
        loc_at_end = re.search(r",\s*([A-Za-z0-9][A-Za-z0-9\s\-\.]{2,30})\s*$", segment)
        if loc_at_end:
            default_loc = _normalize_location(loc_at_end.group(1).strip())
        parts = re.split(r",\s*(?=(?:Mon|Tues?|Wed|Thu|Fri|Sat|Sun)days?)", segment)
        for part in parts:
            part = part.strip()
            loc = default_loc
            loc_match = re.search(r",\s*([A-Za-z0-9][A-Za-z0-9\s\-\.]{2,30})\s*$", part)
            if loc_match:
                cand = loc_match.group(1).strip()
                if not _location_looks_invalid(cand):
                    loc = _normalize_location(cand)
                part = part[: loc_match.start()].strip()
            # "Thursdays 10-11 AM" or "Mondays 2:30-3:30 PM" or "Wednesdays 10:30-11:30 AM" or "Thursdays TBD"
            for m in re.finditer(
                r"(Monday|Tuesday|Wednesday|Thursday|Friday)s?\s+(\d{1,2})[\:]?(\d{2})?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?\s*(?:AM|PM)?",
                part,
                re.I,
            ):
                day = days_map.get(m.group(1).lower())
                if not day:
                    continue
                h1, m1 = int(m.group(2)), m.group(3) or "00"
                h2, m2 = int(m.group(4)), m.group(5) or "00"
                if "am" in m.group(0).lower() and "pm" not in m.group(0).lower() and 8 <= h1 <= 11:
                    pass
                elif h1 < 12 and ("pm" in m.group(0).lower() or (h1 <= 7 and "am" not in m.group(0).lower())):
                    h1, h2 = h1 + 12, h2 + 12
                start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
                key = (day, start, end)
                if key in seen_oh_keys:
                    continue
                seen_oh_keys.add(key)
                meetings.append({
                    "id": f"mt-{len(meetings)+1}",
                    "day_of_week": day,
                    "start_time": start,
                    "end_time": end,
                    "timezone": "America/Los_Angeles",
                    "location": loc,
                    "type": meeting_type,
                })
            for m in re.finditer(
                r"(Monday|Tuesday|Wednesday|Thursday|Friday)s?\s+TBD",
                part,
                re.I,
            ):
                day = days_map.get(m.group(1).lower())
                if not day:
                    continue
                key = (day, "TBD", "TBD")
                if key in seen_oh_keys:
                    continue
                seen_oh_keys.add(key)
                meetings.append({
                    "id": f"mt-{len(meetings)+1}",
                    "day_of_week": day,
                    "start_time": None,
                    "end_time": None,
                    "timezone": "America/Los_Angeles",
                    "location": loc,
                    "type": meeting_type,
                })

    # "Class is held MW 1-1:50 PAI 3.02" or "Class is held MW 1--1:50 PAI 3.02" (UT Austin; soft-hyphen normalizes to -)
    for m in re.finditer(
        r"Class\s+is\s+held\s+(MW|MWF|TR|MTWR)\s+(\d{1,2})[\:]?(\d{2})?\s*[-–]+\s*(\d{1,2})[\:]?(\d{2})?\s+([A-Za-z0-9\s\-\.]+?)(?=\s*\n|$)",
        text[:3000],
        re.I,
    ):
        abbr = m.group(1).upper()
        h1, m1 = int(m.group(2)), m.group(3) or "00"
        h2, m2 = int(m.group(4)), m.group(5) or "00"
        if 1 <= h1 <= 7 and 1 <= h2 <= 7:
            h1, h2 = h1 + 12, h2 + 12
        start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
        loc = _abbreviate_location(m.group(6).strip())
        expand = {"MW": ["MO", "WE"], "MWF": ["MO", "WE", "FR"], "TR": ["TU", "TH"], "MTWR": ["MO", "TU", "WE", "TH"]}
        for day in expand.get(abbr, []):
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

    # "Spring 2015: TTh 2:00 - 3:30 in GDC 2.216" or "Class: T-TH 12:30 p.m. to 2 p.m. BMC 3.208"
    # TTh (no separator), T-TH, TuTh, TR (Tuesday-Thursday)
    # Skip when in Office hours context (e.g. "Office hours: ...; TuTh 10:30-11:30a")
    for m in re.finditer(
        r"\b(?:Class\s*:\s*|[A-Za-z]+\s+\d{4}\s*:\s*)?(TTh|TTH|TR|T\W*TH|TH\W*T|Tu\W*Th|Th\W*Tu)\s*"
        r"(\d{1,2})[\:]?(\d{2})?\s*(?:p\.?m\.?|am\.?)?\s*(?:to|[-–])\s*"
        r"(\d{1,2})[\:]?(\d{2})?\s*(?:p\.?m\.?|am\.?)?\s*(?:in\s+)?\s*([A-Za-z0-9][A-Za-z0-9\-\. ]{1,45})",
        text[:5000],
        re.I,
    ):
        prev = text[max(0, m.start() - 80) : m.start()]
        if re.search(r"Office\s+hours\s*:.*[;:]?\s*$|;\s*$", prev, re.I):
            continue  # Skip TuTh in "Office hours: ...; TuTh" context
        if re.search(r"Time\s*:\s*", prev, re.I):
            continue  # Skip - let "Time: TTh ... Place:" pattern handle it
        h1, m1 = int(m.group(2)), m.group(3) or "00"
        h2, m2 = int(m.group(4)), m.group(5) or "00"
        if re.search(r"p\.?m\.?|pm\b", m.group(0), re.I):
            if h1 < 12:
                h1 += 12
            if h2 < 12:
                h2 += 12
        elif not re.search(r"a\.?m\.?|am\b", m.group(0), re.I) and 1 <= h1 <= 7 and 1 <= h2 <= 7:
            h1, h2 = h1 + 12, h2 + 12
        start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
        loc = (m.group(6) or "").strip()
        if re.match(r"^\d{1,2}\.?\s*(?:Place)?$", loc, re.I):
            continue  # Skip "30. Place" or "12" - wrong capture from "Time: TTh 11:00-12:30. Place:"
        if loc.lower() in ("pm", "am"):
            continue  # Skip "pm"/"am" wrongly captured as location (e.g. "TTh 3:30-5pm" -> loc="pm")
        if loc and len(loc) > 2 and re.search(r"\d", loc) and len(loc) < 50:
            loc = _abbreviate_location(loc)
        for day in ["TU", "TH"]:
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

    # "Lecture Hour: 9:30-11:00am TTH, Room: ETC 2.136" - time first, then TTH/MWF
    if not meetings:
        for m in re.finditer(
            r"(?:Lecture\s+Hour|Lecture|Class)\s*:\s*(\d{1,2})[\:]?(\d{2})?(?:am|pm|a|p)?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?(?:am|pm|a|p)?\s+(TTH|TTh|TR|MWF|MW)\s*,?\s*(?:Room:\s*)?([A-Za-z0-9\s\-\.]+)",
            text[:3000],
            re.I,
        ):
            h1, m1 = int(m.group(1)), m.group(2) or "00"
            h2, m2 = int(m.group(3)), m.group(4) or "00"
            if re.search(r"pm|p\b", m.group(0), re.I) and h1 < 12:
                h1, h2 = h1 + 12, h2 + 12
            elif not re.search(r"am|a\b", m.group(0), re.I) and 1 <= h1 <= 7 and 1 <= h2 <= 7:
                h1, h2 = h1 + 12, h2 + 12
            start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
            loc = _abbreviate_location(m.group(6).strip())
            abbr = m.group(5).upper().replace(" ", "")
            expand = {"TTH": ["TU", "TH"], "TR": ["TU", "TH"], "MWF": ["MO", "WE", "FR"], "MW": ["MO", "WE"]}
            for day in expand.get(abbr, []):
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

    # "Spring 2019 T, Th | 3:30 – 5:00pm | GSB 2.122" - T, Th with pipe separators
    if not meetings:
        for m in re.finditer(
            r"(?:T|Tu|Tue)\s*,\s*(?:Th|Thu)\s*\|\s*(\d{1,2})[\:]?(\d{2})?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?\s*(?:pm|am)?\s*\|\s*([A-Za-z0-9\s\-\.]+)",
            text[:3000],
            re.I,
        ):
            h1, m1 = int(m.group(1)), m.group(2) or "00"
            h2, m2 = int(m.group(3)), m.group(4) or "00"
            if re.search(r"pm", m.group(0), re.I) and h1 < 12:
                h1, h2 = h1 + 12, h2 + 12
            start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
            loc = _abbreviate_location(m.group(5).strip())
            for day in ["TU", "TH"]:
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

    # "Date/Time/Location: MW / 10:30-11:45 AM / ECJ 1.306" - pipe-separated (run even if office hours already added)
    if not any(m.get("type") == "lecture" for m in meetings):
        for m in re.finditer(
            r"Date/Time/Location\s*:\s*(MW|MWF|TR|TTH|TTh)\s*/\s*(\d{1,2})[\:]?(\d{2})?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?\s*(?:AM|PM|am|pm)?\s*/\s*([A-Za-z0-9][A-Za-z0-9\-\. ]*?)(?:\s*\n|$)",
            text[:3000],
            re.I,
        ):
            h1, m1 = int(m.group(2)), m.group(3) or "00"
            h2, m2 = int(m.group(4)), m.group(5) or "00"
            if re.search(r"pm|PM", m.group(0), re.I) and h1 < 12:
                h1, h2 = h1 + 12, h2 + 12
            elif not re.search(r"am|AM", m.group(0), re.I) and 1 <= h1 <= 7 and 1 <= h2 <= 7:
                h1, h2 = h1 + 12, h2 + 12
            start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
            loc = _normalize_location(m.group(6).strip())
            if not loc:
                continue
            abbr = m.group(1).upper().replace(" ", "")
            expand = {"TTH": ["TU", "TH"], "TR": ["TU", "TH"], "MWF": ["MO", "WE", "FR"], "MW": ["MO", "WE"]}
            for day in expand.get(abbr, []):
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

    # "Hours: Monday & Wednesday" + next line "5:00 PM to 6:30 PM" + "Location: ECJ 1.214"
    if not any(m.get("type") == "lecture" for m in meetings):
        for m in re.finditer(
            r"Hours\s*:\s*Monday\s*&\s*Wednesday\s*\n\s*(\d{1,2})[\:]?(\d{2})?\s*(?:AM|PM|am|pm)?\s+to\s+(\d{1,2})[\:]?(\d{2})?\s*(?:AM|PM|am|pm)?\s*\n\s*Location\s*:\s*([A-Za-z0-9\s\-\.]+)",
            text[:3000],
            re.I,
        ):
            h1, m1 = int(m.group(1)), m.group(2) or "00"
            h2, m2 = int(m.group(3)), m.group(4) or "00"
            if re.search(r"pm|PM", m.group(0), re.I) and h1 < 12:
                h1, h2 = h1 + 12, h2 + 12
            elif not re.search(r"am|AM", m.group(0), re.I) and 1 <= h1 <= 7 and 1 <= h2 <= 7:
                h1, h2 = h1 + 12, h2 + 12
            start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
            loc = _normalize_location(m.group(5).strip())
            if not loc:
                continue
            for day in ["MO", "WE"]:
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

    # "Information Time: MW 9:30-11:00am" + "Location: GDC 5.302" (within next ~150 chars)
    if not any(m.get("type") == "lecture" for m in meetings):
        for m in re.finditer(
            r"Information\s+Time\s*:\s*(MW|MWF|TR|TTH|TTh)\s+(\d{1,2})[\:]?(\d{2})?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?(?:am|pm|AM|PM)?[\s\S]{0,150}?Location\s*:\s*([A-Za-z0-9\s\-\.]+)",
            text[:3000],
            re.I,
        ):
            h1, m1 = int(m.group(2)), m.group(3) or "00"
            h2, m2 = int(m.group(4)), m.group(5) or "00"
            if re.search(r"pm|PM", m.group(0), re.I) and h1 < 12:
                h1, h2 = h1 + 12, h2 + 12
            elif not re.search(r"am|AM", m.group(0), re.I) and 1 <= h1 <= 7 and 1 <= h2 <= 7:
                h1, h2 = h1 + 12, h2 + 12
            start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
            loc = _normalize_location(m.group(6).strip())
            if not loc:
                continue
            abbr = m.group(1).upper().replace(" ", "")
            expand = {"TTH": ["TU", "TH"], "TR": ["TU", "TH"], "MWF": ["MO", "WE", "FR"], "MW": ["MO", "WE"]}
            for day in expand.get(abbr, []):
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

    # "Class time: MWF 9-10am; Location: CLA 0.130" - semicolon-separated
    if not any(m.get("type") == "lecture" for m in meetings):
        for m in re.finditer(
            r"Class\s+time\s*:\s*(MWF|MW|TR|TTH|TTh|WF|T\s+R)\s+(\d{1,2})[\:]?(\d{2})?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?(?:am|pm|AM|PM)?\s*(?:;\s*Location\s*:\s*([A-Za-z0-9][A-Za-z0-9\-\. ]*))?",
            text[:3000],
            re.I,
        ):
            days_raw = m.group(1).replace(" ", "").upper()
            if "T" in days_raw and "R" in days_raw:
                abbr = "TR"
            elif "W" in days_raw and "F" in days_raw and "M" not in days_raw:
                abbr = "WF"
            else:
                abbr = days_raw
            h1, m1 = int(m.group(2)), m.group(3) or "00"
            h2, m2 = int(m.group(4)), m.group(5) or "00"
            if re.search(r"pm|PM", m.group(0), re.I) and h1 < 12:
                h1, h2 = h1 + 12, h2 + 12
            elif not re.search(r"am|AM", m.group(0), re.I) and 1 <= h1 <= 7 and 1 <= h2 <= 7:
                h1, h2 = h1 + 12, h2 + 12
            start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
            loc = _normalize_location(m.group(6).strip()) if m.group(6) else None
            if not loc and m.end() < len(text):
                loc_m = re.search(r"Location\s*:\s*([A-Za-z0-9\s\-\.]+)", text[m.end():m.end()+150], re.I)
                if loc_m:
                    loc = _normalize_location(loc_m.group(1).strip())
            expand = {"TTH": ["TU", "TH"], "TR": ["TU", "TH"], "MWF": ["MO", "WE", "FR"], "MW": ["MO", "WE"], "WF": ["WE", "FR"]}
            for day in expand.get(abbr, []):
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

    # "M-Tu-W-Th-F 10:00–11:15am – PAI 4.42" - hyphenated days = MTWRF
    if not any(m.get("type") == "lecture" for m in meetings):
        for m in re.finditer(
            r"M[-–]Tu[-–]W[-–]Th[-–]F\s+(\d{1,2})[\:]?(\d{2})?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?(?:am|pm|AM|PM)?\s*[-–]\s*([A-Za-z0-9\s\-\.]+)",
            text[:3000],
            re.I,
        ):
            h1, m1 = int(m.group(1)), m.group(2) or "00"
            h2, m2 = int(m.group(3)), m.group(4) or "00"
            if re.search(r"pm|PM", m.group(0), re.I) and h1 < 12:
                h1, h2 = h1 + 12, h2 + 12
            elif not re.search(r"am|AM", m.group(0), re.I) and 1 <= h1 <= 7 and 1 <= h2 <= 7:
                h1, h2 = h1 + 12, h2 + 12
            start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
            loc = _normalize_location(m.group(5).strip())
            if not loc:
                continue
            for day in ["MO", "TU", "WE", "TH", "FR"]:
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

    # "Sections 51825, 51830: MW 12.30-2:00 pm UTC 4.132" (period as decimal in time)
    if not any(m.get("type") == "lecture" for m in meetings):
        for m in re.finditer(
            r"Sections?\s+(?:\d+\s*,\s*)*\d+\s*:\s*(MW|MWF|TR|TTH|TTh)\s+(\d{1,2})[\.\:](\d{2})\s*[-–]\s*(\d{1,2})[\.\:]?(\d{2})?\s*(?:pm|am|PM|AM)?\s+([A-Za-z0-9][A-Za-z0-9\-\. ]*)",
            text[:4000],
            re.I,
        ):
            h1, m1 = int(m.group(2)), m.group(3) or "00"
            h2, m2 = int(m.group(4)), m.group(5) or "00"
            if re.search(r"pm|PM", m.group(0), re.I):
                if h1 < 12:
                    h1 += 12
                if h2 < 12:
                    h2 += 12
            elif not re.search(r"am|AM", m.group(0), re.I) and 1 <= h1 <= 7 and 1 <= h2 <= 7:
                h1, h2 = h1 + 12, h2 + 12
            start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
            loc = _normalize_location(m.group(6).strip())
            if not loc:
                continue
            abbr = m.group(1).upper().replace(" ", "")
            expand = {"TTH": ["TU", "TH"], "TR": ["TU", "TH"], "MWF": ["MO", "WE", "FR"], "MW": ["MO", "WE"]}
            for day in expand.get(abbr, []):
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

    # "Section: 51630, MWF 11:00 AM - 12:00 PM, GDC 2.216"
    if not any(m.get("type") == "lecture" for m in meetings):
        for m in re.finditer(
            r"Section\s*:\s*\d+\s*,\s*(MWF|MW|TR|TTH|TTh)\s+(\d{1,2})[\:]?(\d{2})?\s*(AM|PM|am|pm)?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?\s*(AM|PM|am|pm)?\s*,\s*([A-Za-z0-9][A-Za-z0-9\-\. ]*)",
            text[:3000],
            re.I,
        ):
            h1, m1 = int(m.group(2)), m.group(3) or "00"
            h2, m2 = int(m.group(5)), m.group(6) or "00"
            ampm1, ampm2 = (m.group(4) or "").lower(), (m.group(7) or "").lower()
            if "pm" in ampm1 and h1 < 12:
                h1 += 12
            elif not ampm1 and 1 <= h1 <= 7:
                h1 += 12
            if "pm" in ampm2 and h2 < 12:
                h2 += 12
            elif not ampm2 and 1 <= h2 <= 7:
                h2 += 12
            start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
            loc = _normalize_location(m.group(8).strip())
            if not loc:
                continue
            abbr = m.group(1).upper().replace(" ", "")
            expand = {"TTH": ["TU", "TH"], "TR": ["TU", "TH"], "MWF": ["MO", "WE", "FR"], "MW": ["MO", "WE"]}
            for day in expand.get(abbr, []):
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

    # "Lecture: 51990 MWF 2 - 3 pm, GDC 1.304" - optional section number before days
    if not any(m.get("type") == "lecture" for m in meetings):
        for m in re.finditer(
            r"Lecture\s*:\s*(?:\d{5}\s+)?(MWF|MW|TR|TTH|TTh)\s+(\d{1,2})[\:]?(\d{2})?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?\s*(?:pm|am|PM|AM)?\s*,\s*([A-Za-z0-9][A-Za-z0-9\-\. ]*)",
            text[:3000],
            re.I,
        ):
            h1, m1 = int(m.group(2)), m.group(3) or "00"
            h2, m2 = int(m.group(4)), m.group(5) or "00"
            if re.search(r"pm|PM", m.group(0), re.I):
                if h1 < 12:
                    h1 += 12
                if h2 < 12:
                    h2 += 12
            elif not re.search(r"am|AM", m.group(0), re.I) and 1 <= h1 <= 7 and 1 <= h2 <= 7:
                h1, h2 = h1 + 12, h2 + 12
            start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
            loc = _normalize_location(m.group(6).strip())
            if not loc:
                continue
            abbr = m.group(1).upper().replace(" ", "")
            expand = {"TTH": ["TU", "TH"], "TR": ["TU", "TH"], "MWF": ["MO", "WE", "FR"], "MW": ["MO", "WE"]}
            for day in expand.get(abbr, []):
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

    # "Lectures: TTh 3:30-5pm, GDC 5.302" (plural)
    if not any(m.get("type") == "lecture" for m in meetings):
        for m in re.finditer(
            r"Lectures?\s*:\s*(MWF|MW|TR|TTH|TTh)\s+(\d{1,2})[\:]?(\d{2})?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?(?:pm|am|PM|AM)?\s*,\s*([A-Za-z0-9][A-Za-z0-9\-\. ]*)",
            text[:3000],
            re.I,
        ):
            h1, m1 = int(m.group(2)), m.group(3) or "00"
            h2, m2 = int(m.group(4)), m.group(5) or "00"
            if re.search(r"pm|PM", m.group(0), re.I):
                if h1 < 12:
                    h1 += 12
                if h2 < 12:
                    h2 += 12
            elif not re.search(r"am|AM", m.group(0), re.I) and 1 <= h1 <= 7 and 1 <= h2 <= 7:
                h1, h2 = h1 + 12, h2 + 12
            start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
            loc = _normalize_location(m.group(6).strip())
            if not loc:
                continue
            abbr = m.group(1).upper().replace(" ", "")
            expand = {"TTH": ["TU", "TH"], "TR": ["TU", "TH"], "MWF": ["MO", "WE", "FR"], "MW": ["MO", "WE"]}
            for day in expand.get(abbr, []):
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

    # "LECTURE: MWF 8:30 to 10:30 in PAI 2.48"
    if not any(m.get("type") == "lecture" for m in meetings):
        for m in re.finditer(
            r"LECTURE\s*:\s*(MWF|MW|TR|TTH|TTh)\s+(\d{1,2})[\:]?(\d{2})?\s+to\s+(\d{1,2})[\:]?(\d{2})?\s+in\s+([A-Za-z0-9][A-Za-z0-9\-\. ]*)",
            text[:3000],
            re.I,
        ):
            h1, m1 = int(m.group(2)), m.group(3) or "00"
            h2, m2 = int(m.group(4)), m.group(5) or "00"
            if 1 <= h1 <= 7 and 1 <= h2 <= 7:
                h1, h2 = h1 + 12, h2 + 12
            start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
            loc = _normalize_location(m.group(6).strip())
            if not loc:
                continue
            abbr = m.group(1).upper().replace(" ", "")
            expand = {"TTH": ["TU", "TH"], "TR": ["TU", "TH"], "MWF": ["MO", "WE", "FR"], "MW": ["MO", "WE"]}
            for day in expand.get(abbr, []):
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

    # "Class Meetings: MWF 12:00-1:00pm, GSB 2.126" (12:00-1:00pm = 12:00-13:00)
    if not any(m.get("type") == "lecture" for m in meetings):
        for m in re.finditer(
            r"Class\s+Meetings?\s*:\s*(MWF|MW|TR|TTH|TTh)\s+(\d{1,2})[\:]?(\d{2})?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?(?:pm|am|PM|AM)?\s*,\s*([A-Za-z0-9][A-Za-z0-9\-\. ]*)",
            text[:3000],
            re.I,
        ):
            h1, m1 = int(m.group(2)), m.group(3) or "00"
            h2, m2 = int(m.group(4)), m.group(5) or "00"
            if re.search(r"pm|PM", m.group(0), re.I):
                if h1 < 12:
                    h1 += 12
                if h2 < 12:
                    h2 += 12
            elif not re.search(r"am|AM", m.group(0), re.I) and 1 <= h1 <= 7 and 1 <= h2 <= 7:
                h1, h2 = h1 + 12, h2 + 12
            start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
            loc = _normalize_location(m.group(6).strip())
            if not loc:
                continue
            abbr = m.group(1).upper().replace(" ", "")
            expand = {"TTH": ["TU", "TH"], "TR": ["TU", "TH"], "MWF": ["MO", "WE", "FR"], "MW": ["MO", "WE"]}
            for day in expand.get(abbr, []):
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

    # "Time and Place: MWF, 11a-12n, RLM 6.118" (a=am, n=noon; 11a-12n = 11:00-12:00)
    if not any(m.get("type") == "lecture" for m in meetings):
        for m in re.finditer(
            r"Time\s+and\s+Place\s*:\s*(MWF|MW|TR|TTH|TTh)\s*,\s*(\d{1,2})a?\s*[-–]\s*(\d{1,2})n?\s*,\s*([A-Za-z0-9][A-Za-z0-9\-\. ]*)",
            text[:3000],
            re.I,
        ):
            h1, h2 = int(m.group(2)), int(m.group(3))
            # 12n = noon (12:00), 11a = 11am
            if h2 == 12:
                pass  # noon
            elif h2 < h1 and h2 <= 5:
                h2 += 12
            start, end = f"{h1:02d}:00", f"{h2:02d}:00"
            loc = _normalize_location(m.group(4).strip())
            if not loc:
                continue
            abbr = m.group(1).upper().replace(" ", "")
            expand = {"TTH": ["TU", "TH"], "TR": ["TU", "TH"], "MWF": ["MO", "WE", "FR"], "MW": ["MO", "WE"]}
            for day in expand.get(abbr, []):
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

    # "MWF 10-11 a.m." + next line "UTC 3.112 Office Hours:" (location before Office Hours; allow rest of line after a.m.)
    if not any(m.get("type") == "lecture" for m in meetings):
        for m in re.finditer(
            r"(?:^|\n)\s*(MWF|MW)\s+(\d{1,2})\s*[-–]\s*(\d{1,2})\s*(?:a\.m\.?|am|AM)[^\n]*\n\s*([A-Za-z0-9][A-Za-z0-9\-\. ]+?)\s+Office\s+Hours",
            text[:3000],
            re.I,
        ):
            h1, h2 = int(m.group(2)), int(m.group(3))
            if h1 == 12:
                h1 = 12
            elif h2 == 12:
                h2 = 12
            elif h2 < h1:
                h2 += 12
            start, end = f"{h1:02d}:00", f"{h2:02d}:00"
            loc = _normalize_location(m.group(4).strip())
            if not loc or len(loc) < 4:
                continue
            abbr = m.group(1).upper()
            expand = {"MWF": ["MO", "WE", "FR"], "MW": ["MO", "WE"]}
            for day in expand.get(abbr, []):
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

    # "Class meets: MWF 10–11 am in RLM 5.118"
    if not any(m.get("type") == "lecture" for m in meetings):
        for m in re.finditer(
            r"Class\s+meets\s*:\s*(MWF|MW|TR|TTH|TTh)\s+(\d{1,2})\s*[-–]\s*(\d{1,2})\s*(?:am|pm|AM|PM)?\s+in\s+([A-Za-z0-9][A-Za-z0-9\-\. ]*)",
            text[:3000],
            re.I,
        ):
            h1, h2 = int(m.group(2)), int(m.group(3))
            if re.search(r"pm|PM", m.group(0), re.I) and h1 < 12:
                h1, h2 = h1 + 12, h2 + 12
            elif not re.search(r"am|AM", m.group(0), re.I) and 1 <= h1 <= 7 and 1 <= h2 <= 7:
                h1, h2 = h1 + 12, h2 + 12
            start, end = f"{h1:02d}:00", f"{h2:02d}:00"
            loc = _normalize_location(m.group(4).strip())
            if not loc:
                continue
            abbr = m.group(1).upper().replace(" ", "")
            expand = {"TTH": ["TU", "TH"], "TR": ["TU", "TH"], "MWF": ["MO", "WE", "FR"], "MW": ["MO", "WE"]}
            for day in expand.get(abbr, []):
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

    # "Section: Unique #55895, Meets MWF, 2-3 PM, RLM 7.104" or "12-1 PM" (noon to 1pm)
    if not meetings:
        for m in re.finditer(
            r"Meets\s+(MWF|MW|TR|TTH|TTh)\s*,\s*(\d{1,2})\s*[-–]\s*(\d{1,2})\s*(?:AM|PM|am|pm)?\s*,\s*([A-Za-z0-9\s\-\.]+)",
            text[:3000],
            re.I,
        ):
            h1, h2 = int(m.group(2)), int(m.group(3))
            is_pm = bool(re.search(r"pm|PM", m.group(0)))
            if is_pm:
                if h1 < 12:
                    h1 += 12
                if h2 < 12:
                    h2 += 12
            elif not re.search(r"am|AM", m.group(0)) and 1 <= h1 <= 7 and 1 <= h2 <= 7:
                h1, h2 = h1 + 12, h2 + 12
            start, end = f"{h1:02d}:00", f"{h2:02d}:00"
            loc = _normalize_location(m.group(4).strip())
            if not loc:
                continue
            abbr = m.group(1).upper().replace(" ", "")
            expand = {"TTH": ["TU", "TH"], "TR": ["TU", "TH"], "MWF": ["MO", "WE", "FR"], "MW": ["MO", "WE"]}
            for day in expand.get(abbr, []):
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

    # "Spring 2015 TTH 12:30-2:00 CAL 100" - Season Year TTH time location
    if not meetings:
        for m in re.finditer(
            r"(?:Spring|Fall|Summer|Winter)\s+\d{4}\s+(TTH|TTh|TR|MWF|MW)\s+(\d{1,2})[\:]?(\d{2})?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?\s+([A-Za-z0-9\s\-\.]+)",
            text[:3000],
            re.I,
        ):
            h1, m1 = int(m.group(2)), m.group(3) or "00"
            h2, m2 = int(m.group(4)), m.group(5) or "00"
            if 1 <= h1 <= 7 and 1 <= h2 <= 7:
                h1, h2 = h1 + 12, h2 + 12
            start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
            loc = _normalize_location(m.group(6).strip())
            if not loc:
                continue
            abbr = m.group(1).upper().replace(" ", "")
            expand = {"TTH": ["TU", "TH"], "TR": ["TU", "TH"], "MWF": ["MO", "WE", "FR"], "MW": ["MO", "WE"]}
            for day in expand.get(abbr, []):
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

    # "Tuesdays and Thursdays, 3:30 to 5:30, in room RLM 5.114" or "Tuesdays and Thursdays, 3:30 to 5:30, room TBA"
    if not any(m.get("type") == "lecture" for m in meetings):
        for m in re.finditer(
            r"Tuesdays?\s+and\s+Thursdays?\s*,\s*(\d{1,2})[\:]?(\d{2})?\s+to\s+(\d{1,2})[\:]?(\d{2})?\s*,\s*(?:in\s+room\s+)?([A-Za-z0-9][A-Za-z0-9\-\. ]{1,45})",
            text[:10000],
            re.I,
        ):
            h1, m1 = int(m.group(1)), m.group(2) or "00"
            h2, m2 = int(m.group(3)), m.group(4) or "00"
            if 1 <= h1 <= 7 and 1 <= h2 <= 7:
                h1, h2 = h1 + 12, h2 + 12
            start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
            loc = (m.group(5) or "").strip()
            if loc and (re.search(r"\d", loc) or "TBA" in loc.upper()) and len(loc) < 50:
                loc = _normalize_location(loc) or loc
                for day in ["TU", "TH"]:
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
                break

    # "Time: TTh 11:00 - 12:30. Place: CAL 100" or "Time: MW 9:30-11:00am"
    if not meetings:
        for m in re.finditer(
            r"Time\s*:\s*(TTh|TTH|TR|MWF|MW)\s+(\d{1,2})[\:]?(\d{2})?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?\s*(?:\.|am|pm|AM|PM)?\s*(?:\s*\.?\s*Place:\s*([A-Za-z0-9\s\-\.]+))?",
            text[:3000],
            re.I,
        ):
            h1, m1 = int(m.group(2)), m.group(3) or "00"
            h2, m2 = int(m.group(4)), m.group(5) or "00"
            if re.search(r"pm|PM", m.group(0), re.I) and h1 < 12:
                h1, h2 = h1 + 12, h2 + 12
            elif not re.search(r"am|AM", m.group(0), re.I) and 1 <= h1 <= 7 and 1 <= h2 <= 7:
                h1, h2 = h1 + 12, h2 + 12
            start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
            loc = _normalize_location(m.group(6).strip()) if m.group(6) else None
            abbr = m.group(1).upper().replace(" ", "")
            expand = {"TTH": ["TU", "TH"], "TR": ["TU", "TH"], "MWF": ["MO", "WE", "FR"], "MW": ["MO", "WE"]}
            for day in expand.get(abbr, []):
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

    # "Meets: MWF 9:00a in RLM 5.120" - single start time, assume 50 min
    if not meetings:
        for m in re.finditer(
            r"Meets\s*:\s*(MWF|MW|TR|TTH)\s+(\d{1,2})[\:]?(\d{2})?\s*(?:a|am|p|pm)?\s+in\s+([A-Za-z0-9\s\-\.]+)",
            text[:3000],
            re.I,
        ):
            h1, m1 = int(m.group(2)), m.group(3) or "00"
            if re.search(r"p\b|pm", m.group(0), re.I) and h1 < 12:
                h1 += 12
            elif not re.search(r"a\b|am", m.group(0), re.I) and 1 <= h1 <= 7:
                h1 += 12
            start = f"{h1:02d}:{m1}"
            eh, em = h1, int(m1) + 50
            if em >= 60:
                eh, em = eh + 1, em - 60
            end = f"{eh:02d}:{em:02d}"
            loc = _abbreviate_location(m.group(4).strip())
            abbr = m.group(1).upper().replace(" ", "")
            expand = {"TTH": ["TU", "TH"], "TR": ["TU", "TH"], "MWF": ["MO", "WE", "FR"], "MW": ["MO", "WE"]}
            for day in expand.get(abbr, []):
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

    # "Unique #: 50480 ... F 3pm GDC 4.304" or "50480 F 3pm GDC 4.304"
    for m in re.finditer(
        r"(?:\d{5}\s+)?(M|T|W|R|F)\s+(\d{1,2})\s*(?:pm|am|p\.m\.?|a\.m\.?)?\s+([A-Z]{2,4}\s+[\d\.]+)",
        text[:5000],
        re.I,
    ):
        single_map = {"M": "MO", "T": "TU", "W": "WE", "R": "TH", "F": "FR"}
        day = single_map.get(m.group(1).upper())
        if not day or day in seen_days:
            continue
        h1 = int(m.group(2))
        if h1 < 12 and ("pm" in (m.group(0) or "").lower() or "p.m" in (m.group(0) or "").lower()):
            h1 += 12
        start = f"{h1:02d}:00"
        end = f"{(h1 + 1):02d}:00" if h1 < 23 else "23:00"
        loc = _abbreviate_location(m.group(3).strip())
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

    # "Fall 2024 (MW 1:30 – 3:00 pm, ECJ 1.316)" or "MW 1:30 – 3:00 pm, ECJ 1.316"
    for m in re.finditer(
        r"\b(MW|MWF|TR|T[\s\-]?TH)\s+(\d{1,2})[\:]?(\d{2})?\s*[–\-]\s*(\d{1,2})[\:]?(\d{2})?\s*(?:pm|am)?\s*[,]\s*([A-Za-z0-9\s\-\.]+)",
        text[:5000],
        re.I,
    ):
        abbr = m.group(1).replace("-", "").replace(" ", "").upper()
        if "T" in abbr and "R" in abbr:
            days_list = ["TU", "TH"]
        elif "M" in abbr and "W" in abbr and "F" in abbr:
            days_list = ["MO", "WE", "FR"]
        elif "M" in abbr and "W" in abbr:
            days_list = ["MO", "WE"]
        else:
            continue
        h1, m1 = int(m.group(2)), m.group(3) or "00"
        h2, m2 = int(m.group(4)), m.group(5) or "00"
        if h1 < 12 and "pm" in (m.group(0) or "").lower():
            h1, h2 = h1 + 12, h2 + 12
        start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
        loc = _abbreviate_location(m.group(6).strip())
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

    # Penn State: "Class Meeting Times: TR 1:35-2:50 p.m." / "Class Room: EAB, 102" (separate lines)
    for m in re.finditer(
        r"(?:Class\s+Meeting\s+Times|Class\s+Time|Class\s+Hours)\s*:\s*"
        r"(TR|MW|Mo\s+We|Tu\s+Th|Mo\s+Th|Tu\s+We)\s+"
        r"(\d{1,2})[\:]?(\d{2})?(?:\s*(?:p\.?m\.?|am\.?))?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?(?:\s*(?:p\.?m\.?|am\.?|P\.?M\.?|A\.?M\.?))?"
        r"(?:\s+Location\s*:\s*([A-Za-z0-9\s\-]+))?",
        text[:5000],
        re.I,
    ):
        h1, m1 = int(m.group(2)), m.group(3) or "00"
        h2, m2 = int(m.group(4)), m.group(5) or "00"
        if re.search(r"p\.?m\.?|pm\b|P\.?M\.?", m.group(0), re.I) and h1 < 12:
            h1, h2 = h1 + 12, h2 + 12
        start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
        loc = (m.group(6) or "").strip() if m.lastindex >= 6 and m.group(6) else None
        if not loc:
            after = text[m.end() : m.end() + 200]
            loc_m = re.search(r"(?:Class\s+Room|Classroom)\s*:\s*([A-Za-z0-9\s\-,\d]+?)(?:\n|$)", after, re.I)
            if loc_m:
                loc = loc_m.group(1).strip()
        if loc:
            loc = _abbreviate_location(loc)
        day_block = (m.group(1) or "").replace(".", "").strip().upper()
        abbrev_map = {"TR": ["TU", "TH"], "MW": ["MO", "WE"], "MO WE": ["MO", "WE"], "TU TH": ["TU", "TH"], "MO TH": ["MO", "TH"], "TU WE": ["TU", "WE"]}
        days_list = abbrev_map.get(day_block) or abbrev_map.get(day_block.replace(" ", ""))
        if not days_list:
            days_list = ["MO", "WE"] if "WE" in day_block or "W" in day_block else ["TU", "TH"]
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

    # "Monday and Wednesday, 8:30--9:50 in Living Learning Center South 101" - double-dash time, full day names
    for m in re.finditer(r"\b(Monday|Tuesday|Wednesday|Thursday|Friday)\s+and\s+(Monday|Tuesday|Wednesday|Thursday|Friday)\s*,\s*(\d{1,2})[\:]?(\d{2})?\s*[-]{2,}\s*(\d{1,2})[\:]?(\d{2})?\s*(?:in\s+)?([A-Za-z0-9\s\-]+)?", text[:5000], re.I):
        h1, m1 = int(m.group(3)), m.group(4) or "00"
        h2, m2 = int(m.group(5)), m.group(6) or "00"
        start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
        loc = (m.group(7) or "").strip() if m.lastindex >= 7 and m.group(7) else None
        if loc:
            loc = _abbreviate_location(loc)
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

    # "Tu, Th. 10:00 - 11:20" with location on next line (e.g. "180 Prince Lucien Campbell Hall (PLC)")
    for m in re.finditer(r"\b(Tu|Thu|Tue|Th|Wed|Mon|Fri|We|Mo|Fr)\.?\s*,\s*(Tu|Thu|Tue|Th|Wed|Mon|Fri|We|Mo|Fr)\.?\s+(\d{1,2})[\:]?(\d{2})?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?\s*(?:AM|PM)?", text[:5000], re.I):
        h1, m1 = int(m.group(3)), m.group(4) or "00"
        h2, m2 = int(m.group(5)), m.group(6) or "00"
        start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
        # Look for location on next line
        after = text[m.end():m.end() + 120]
        loc_m = re.match(r"\s*\n\s*([A-Za-z0-9][A-Za-z0-9\s\-().]+?)(?:\n|$)", after)
        loc = None
        if loc_m:
            loc = _abbreviate_location(loc_m.group(1).strip())
        days_abbr = {"tu": "TU", "th": "TH", "thu": "TH", "tue": "TU", "wed": "WE", "mon": "MO", "mo": "MO", "fri": "FR", "fr": "FR", "we": "WE"}
        for g in (m.group(1), m.group(2)):
            if not g:
                continue
            key = g.replace(".", "").lower()[:3]
            day = days_abbr.get(key) or days_map.get(key)
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

    # "Class Meet at 125 MCK - Mondays, Wednesdays, Fridays 12:00-12:50pm"
    for m in re.finditer(r"(?:Class\s+Meet\s+at|Meet\s+at)\s+([A-Za-z0-9\s\-]+?)\s+[-–]\s+(Mondays?|Wednesdays?|Fridays?)(?:\s*,\s*|\s+and\s+)(Mondays?|Wednesdays?|Fridays?)(?:\s*,\s*|\s+and\s+)(Mondays?|Wednesdays?|Fridays?)?\s*(\d{1,2})[\:]?(\d{2})?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?\s*(pm|am)?", text[:5000], re.I):
        loc = _abbreviate_location(m.group(1).strip())
        days_plural = {"monday": "MO", "mondays": "MO", "tuesday": "TU", "wednesday": "WE", "wednesdays": "WE", "thursday": "TH", "friday": "FR", "fridays": "FR"}
        h1, m1 = int(m.group(5)), m.group(6) or "00"
        h2, m2 = int(m.group(7)), m.group(8) or "00"
        ampm = (m.group(9) or "").lower()
        if ampm == "pm" and h1 < 12:
            h1, h2 = h1 + 12, h2 + 12
        if not ampm and 12 <= h1 <= 12 and 12 <= h2 <= 12:
            pass  # noon
        start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
        for g in (m.group(2), m.group(3), m.group(4)):
            if not g:
                continue
            day = days_plural.get(g.lower())
            if day and day not in seen_days:
                seen_days.add(day)
                meetings.append({"id": f"mt-{len(meetings)+1}", "day_of_week": day, "start_time": start, "end_time": end, "timezone": "America/Los_Angeles", "location": loc, "type": "lecture"})

    # "Class: 1:00-1:50pm, MWF, 191 ANS" - time first, then days, then location
    for m in re.finditer(r"Class\s*:\s*(\d{1,2})[\:]?(\d{2})?\s*(pm|am)?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?\s*(pm|am)?\s*[,]\s*(MTWRF|MTWR|MTWF|MWF|MW|MF|TR|WF)\s*,\s*([A-Za-z0-9\s\-]+)", text[:5000], re.I):
        h1, m1 = int(m.group(1)), m.group(2) or "00"
        h2, m2 = int(m.group(4)), m.group(5) or "00"
        ampm = (m.group(6) or m.group(3) or "").lower()
        if ampm == "pm" and h1 < 12:
            h1, h2 = h1 + 12, h2 + 12
        if not ampm and 1 <= h1 <= 7 and 1 <= h2 <= 7:
            h1, h2 = h1 + 12, h2 + 12
        start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
        loc = _abbreviate_location(m.group(8).strip())
        abbr = m.group(7).replace(".", "").upper()
        expand = {"MW": ["MO", "WE"], "MTWR": ["MO", "TU", "WE", "TH"], "MTWRF": ["MO", "TU", "WE", "TH", "FR"], "MTWF": ["MO", "TU", "WE", "FR"], "MWF": ["MO", "WE", "FR"], "MF": ["MO", "FR"], "TR": ["TU", "TH"], "WF": ["WE", "FR"]}
        for day in expand.get(abbr, []):
            if day not in seen_days:
                seen_days.add(day)
                meetings.append({"id": f"mt-{len(meetings)+1}", "day_of_week": day, "start_time": start, "end_time": end, "timezone": "America/Los_Angeles", "location": loc, "type": "lecture"})

    # "Winter 2024, 2:00–3:20p, M & W; Lawrence 166" - term, time, M & W; location
    for m in re.finditer(r"[A-Za-z]+\s+\d{4}\s*,\s*(\d{1,2})[\:]?(\d{2})?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?\s*p\s*,\s*M\s*&\s*W\s*;\s*([A-Za-z0-9\s\-]+)", text[:5000], re.I):
        h1, m1 = int(m.group(1)), m.group(2) or "00"
        h2, m2 = int(m.group(3)), m.group(4) or "00"
        if h1 < 12:
            h1, h2 = h1 + 12, h2 + 12
        start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
        loc = _abbreviate_location(m.group(5).strip())
        for day in ["MO", "WE"]:
            if day not in seen_days:
                seen_days.add(day)
                meetings.append({"id": f"mt-{len(meetings)+1}", "day_of_week": day, "start_time": start, "end_time": end, "timezone": "America/Los_Angeles", "location": loc, "type": "lecture"})

    # "MW, 4:00 PM -- 5:50 PM, FEN 105" or "Time and Place: MW, 4:00 PM - 5:50 PM, FEN105"
    for m in re.finditer(r"(?:Time\s*and\s*Place|Timeand\s*Place|Place)\s*:\s*(MW|MTWRF?|TR)\s*[,，\s]\s*(\d{1,2})[\:]?(\d{2})?\s*(?:PM|AM)\s*[-–]{1,2}\s*(\d{1,2})[\:]?(\d{2})?\s*(?:PM|AM)\s*[,，\s]\s*([A-Za-z0-9\s\-]+)", text[:5000], re.I):
        abbr = m.group(1).upper()
        h1, m1 = int(m.group(2)), m.group(3) or "00"
        h2, m2 = int(m.group(4)), m.group(5) or "00"
        if "pm" in m.group(0).lower() and h1 < 12:
            h1, h2 = h1 + 12, h2 + 12
        start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
        loc = _abbreviate_location(m.group(6).strip())
        expand = {"MW": ["MO", "WE"], "MTWR": ["MO", "TU", "WE", "TH"], "MTWRF": ["MO", "TU", "WE", "TH", "FR"], "TR": ["TU", "TH"]}
        for day in expand.get(abbr, []):
            if day not in seen_days:
                seen_days.add(day)
                meetings.append({"id": f"mt-{len(meetings)+1}", "day_of_week": day, "start_time": start, "end_time": end, "timezone": "America/Los_Angeles", "location": loc, "type": "lecture"})

    # "M 3:30-4:50 - 220 DES" or "W 4-5:20, 140 TYKE" - single day letter with time and location
    for m in re.finditer(r"\b(M|T|W|R|F)\s+(\d{1,2})[\:]?(\d{2})?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?\s*[,]\s*([A-Za-z0-9\s\-]+)", text[:5000], re.I):
        single_map = {"M": "MO", "T": "TU", "W": "WE", "R": "TH", "F": "FR"}
        day = single_map.get(m.group(1).upper())
        if not day or day in seen_days:
            continue
        h1, m1 = int(m.group(2)), m.group(3) or "00"
        h2, m2 = int(m.group(4)), m.group(5) or "00"
        if 4 <= h1 <= 7 and 4 <= h2 <= 7:
            h1, h2 = h1 + 12, h2 + 12
        start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
        loc = _abbreviate_location(m.group(6).strip())
        seen_days.add(day)
        meetings.append({"id": f"mt-{len(meetings)+1}", "day_of_week": day, "start_time": start, "end_time": end, "timezone": "America/Los_Angeles", "location": loc, "type": "lecture"})
    for m in re.finditer(r"\b(M|T|W|R|F)\s+(\d{1,2})[\:]?(\d{2})?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?\s*[-–]\s*([A-Za-z0-9\s\-]+)", text[:5000], re.I):
        single_map = {"M": "MO", "T": "TU", "W": "WE", "R": "TH", "F": "FR"}
        day = single_map.get(m.group(1).upper())
        if not day or day in seen_days:
            continue
        h1, m1 = int(m.group(2)), m.group(3) or "00"
        h2, m2 = int(m.group(4)), m.group(5) or "00"
        if 3 <= h1 <= 7 and 4 <= h2 <= 7:
            h1, h2 = h1 + 12, h2 + 12
        start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
        loc = _abbreviate_location(m.group(6).strip())
        seen_days.add(day)
        meetings.append({"id": f"mt-{len(meetings)+1}", "day_of_week": day, "start_time": start, "end_time": end, "timezone": "America/Los_Angeles", "location": loc, "type": "lecture"})

    # "MTWR 4:00-4:50", "MWF 3:00-3:50", "MWF 1-1:50 - 221 MCK", "MTWRF 10:00 am - 11:50 am" - abbreviated days
    for m in re.finditer(r"\b(MTWRF|MTWR|MTWF|MWF|MW|MF|TR|WF|WR|T\.?R|M\.?W)\s+(\d{1,2})[\:]?(\d{2})?\s*(pm|am)?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?\s*(pm|am)?\s*(?:\s+[-–]\s+|\t|\,|\s)([A-Za-z0-9\s\-]+)?", text[:5000], re.I):
        abbr = m.group(1).replace(".", "").replace(" ", "").upper()
        h1, m1 = int(m.group(2)), m.group(3) or "00"
        h2, m2 = int(m.group(5)), m.group(6) or "00"  # groups 5,6 = end time (4,7 = ampm)
        ampm = ((m.group(7) or m.group(4)) or "").lower()  # prefer second am/pm
        if ampm == "pm" and h1 < 12:
            h1 += 12
        if ampm == "pm" and h2 < 12:
            h2 += 12
        # Common afternoon class times (1-7) without am/pm -> assume pm
        if not ampm and 1 <= h1 <= 7 and 1 <= h2 <= 7:
            h1, h2 = h1 + 12, h2 + 12
        start = f"{h1:02d}:{m1}"
        end = f"{h2:02d}:{m2}"
        loc = (m.group(8) or "").strip() if m.lastindex >= 8 and m.group(8) else None
        if loc:
            loc = _abbreviate_location(loc)
        if not loc:
            after = text[m.end() : m.end() + 150]
            loc_m = re.search(r"(?:Class\s+)?[Ll]ocation\s*:\s*([A-Za-z0-9\s\-]+?)(?:\n|$)", after, re.I)
            if loc_m:
                loc = _abbreviate_location(loc_m.group(1).strip())
        expand = {"MW": ["MO", "WE"], "MTWR": ["MO", "TU", "WE", "TH"], "MTWRF": ["MO", "TU", "WE", "TH", "FR"], "MTWF": ["MO", "TU", "WE", "FR"], "MWF": ["MO", "WE", "FR"], "MF": ["MO", "FR"], "TR": ["TU", "TH"], "WF": ["WE", "FR"], "WR": ["WE", "TH"]}
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
    # Skip slots already added as office hours; validate location to avoid day-name fragments.
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
        start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
        if (day, start, end) in seen_oh_keys:
            continue
        raw_loc = (m.group(6) or "").strip() if m.lastindex >= 6 and m.group(6) else None
        loc = _normalize_location(raw_loc) if raw_loc else None
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

    # "Monday / Wednesday / Friday, 9:00 am – 10:00 am, WEL 2.304" - 3 days with slashes
    for m in re.finditer(r"\b(Monday|Tuesday|Wednesday|Thursday|Friday)\s*/\s*(Monday|Tuesday|Wednesday|Thursday|Friday)\s*/\s*(Monday|Tuesday|Wednesday|Thursday|Friday)\s*,\s*(\d{1,2})[\:]?(\d{2})?\s*(?:am|pm)?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?\s*(?:am|pm)?\s*(?:,\s*)?([A-Za-z0-9\s\-\.]+)?", text[:5000], re.I):
        days_map = {"monday": "MO", "tuesday": "TU", "wednesday": "WE", "thursday": "TH", "friday": "FR"}
        h1, m1 = int(m.group(4)), m.group(5) or "00"
        h2, m2 = int(m.group(6)), m.group(7) or "00"
        # 9:00 am – 10:00 am: keep as 09:00-10:00; 2:00 pm: add 12
        if "pm" in m.group(0).lower() and h1 < 12 and h1 >= 1:
            h1, h2 = h1 + 12, h2 + 12
        loc_raw = (m.group(8) or "").strip()
        loc = _normalize_location(loc_raw) if len(loc_raw) > 2 else None
        for g in (m.group(1), m.group(2), m.group(3)):
            if not g:
                continue
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

    # "Tuesday/Thursday, 16:00-17:20, 125 McKenzie Hall" - slash, 24h time (2 days)
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

    # "Tuesday and Thursday, 10:00 - 11:20" (no am/pm) with optional location on next line
    days_map_full = {"monday": "MO", "tuesday": "TU", "wednesday": "WE", "thursday": "TH", "friday": "FR"}
    for m in re.finditer(r"\b(Tuesday|Thursday|Monday|Wednesday|Friday)s?\s+and\s+(Tuesday|Thursday|Monday|Wednesday|Friday)s?\s*,\s*(\d{1,2})[\:]?(\d{2})?\s*[-–]\s*(\d{1,2})[\:]?(\d{2})?\s*(?:\.|AM|PM)?", text[:5000], re.I):
        h1, m1 = int(m.group(3)), m.group(4) or "00"
        h2, m2 = int(m.group(5)), m.group(6) or "00"
        start, end = f"{h1:02d}:{m1}", f"{h2:02d}:{m2}"
        after = text[m.end():m.end() + 250]
        loc = None
        # Find first line that looks like a location (room number, building name)
        for line in after.split("\n")[:5]:
            line = line.strip()
            if not line or len(line) < 5:
                continue
            if line.lower() in ("lecture", "lab", "labs", "discussion"):
                continue
            if re.match(r"\d+\s+[A-Za-z]", line) or "hall" in line.lower() or "center" in line.lower() or "mckenzie" in line.lower():
                loc = _abbreviate_location(re.sub(r"\s*\(https?://[^)]*\).*", "", line).strip())
                break
        else:
            loc = None
        for g in (m.group(1), m.group(2)):
            if not g:
                continue
            day = days_map_full.get(g.lower())
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

    # "LAB will be on Thursday, B026 Klamath" - single day, location, no time (lab type)
    seen_labs: set[tuple[str, str]] = set()
    for m in re.finditer(r"(?:LAB|Lab)\s+will\s+be\s+on\s+(Monday|Tuesday|Wednesday|Thursday|Friday)s?\s*[,]\s*([A-Za-z0-9\s\-]{3,30})", text[:4000], re.I):
        days_map = {"monday": "MO", "tuesday": "TU", "wednesday": "WE", "thursday": "TH", "friday": "FR"}
        day = days_map.get(m.group(1).lower())
        loc = _normalize_location(m.group(2).strip())
        if day and loc and "room" not in (loc or "").lower()[:10]:
            key = (day, loc)
            if key not in seen_labs:
                seen_labs.add(key)
                meetings.append({
                    "id": f"mt-{len(meetings)+1}",
                    "day_of_week": day,
                    "start_time": None,
                    "end_time": None,
                    "timezone": "America/Los_Angeles",
                    "location": loc,
                    "type": "lab",
                })
    # "will be on Thursday, B026 Klamath" - generic (no LAB prefix), only if day not yet seen
    for m in re.finditer(r"(?:will be\s+)?on\s+(Monday|Tuesday|Wednesday|Thursday|Friday)s?\s*[,]\s*([A-Za-z0-9\s\-]{3,30})", text[:4000], re.I):
        days_map = {"monday": "MO", "tuesday": "TU", "wednesday": "WE", "thursday": "TH", "friday": "FR"}
        day = days_map.get(m.group(1).lower())
        loc = m.group(2).strip()
        if day and day not in seen_days and "room" not in loc.lower()[:10]:
            prev = text[max(0, m.start() - 50) : m.start()]
            if "LAB" in prev or "Lab" in prev:
                continue  # already handled by LAB pattern above
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

    # Cleanup: strip "Lectures" suffix from location (e.g. "B040 PSC\nLectures" -> "B040 PSC")
    for mt in meetings:
        loc = mt.get("location")
        if loc:
            cleaned = re.sub(r"\s*\n\s*Lectures\s*$", "", loc, re.I)
            cleaned = re.sub(r"\s+Lectures\s*$", "", cleaned, re.I)
            if cleaned != loc:
                mt["location"] = cleaned.strip() or None

    # Filter: drop meetings with location that looks like a person's name or day fragment
    def _valid_location(loc):
        if not loc:
            return True  # None is ok
        if _location_looks_invalid(loc):
            return False
        if re.search(r"\d", loc):
            return True  # has digit = room/building
        if len(loc) >= 10 or "hall" in loc.lower() or "center" in loc.lower() or "building" in loc.lower():
            return True
        if loc.lower() in ("plc", "mck", "llc", "llcs", "emu", "fen", "des", "tyke", "ans", "lawrence", "deschutes"):
            return True
        return False  # short strings like "mpong" with no context
    meetings = [mt for mt in meetings if _valid_location(mt.get("location"))]

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
