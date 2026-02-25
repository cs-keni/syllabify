"""
Course metadata extraction: code, title, term, instructors.
"""
import re


# Department name -> standard course prefix (e.g. Physics -> PHY)
_DEPT_ABBREV = {
    "physics": "PHY", "phys": "PHY", "philosophy": "PHIL", "phil": "PHIL",
    "computer": "CS", "mathematics": "MATH", "math": "MATH",
    "chemistry": "CH", "biology": "BIO", "economics": "ECO",
    "electrical": "EE", "engineering": "EE", "mechanical": "ME",
}


def parse_course_code(text: str, folder: str) -> str:
    """Extract course code (e.g. CS 210) from text or folder."""
    skip_prefixes = {
        "ROOM", "WEEK", "OCT", "NOV", "DEC", "JAN", "FEB", "MAR", "APR",
        "JUN", "JUL", "AUG", "SEP", "MTWR", "PLC", "DES", "MCK", "LIL",
    }
    # Prefer "Subject Number" from first line (e.g. "Physics 336k", "CS 331")
    skip_subjects = {"spring", "fall", "summer", "winter", "section", "unique", "time", "place"}
    first_block = text[:600]
    # "EE 382 N" -> "EE 382N" (space before letter suffix on first line)
    for m in re.finditer(r"^([A-Z]{2,4})\s+(\d{3})\s+([A-Z])\b", first_block, re.M | re.I):
        prefix, base, suffix = m.group(1), m.group(2), m.group(3)
        if prefix.upper() not in skip_prefixes:
            return f"{prefix} {base}{suffix}".strip()
    # "Physics n303L" -> PHY 303L (lowercase letter prefix in number, strip it)
    for m in re.finditer(r"^([A-Za-z]+)\s+([a-z]?\d{3}[A-Za-z]?)\b", first_block, re.M | re.I):
        subj, num = m.group(1).strip(), m.group(2)
        if len(num) > 1 and num[0].islower() and num[0].isalpha():  # "n303L" -> "303L"
            num = num[1:]
        subj_lower = subj.lower()
        if subj_lower in skip_prefixes or subj_lower in skip_subjects or len(subj) < 2:
            continue
        if num.startswith("20") and len(num) >= 3:  # year like 2014
            continue
        abbrev = _DEPT_ABBREV.get(subj_lower) or subj.upper()[:4]
        code = f"{abbrev} {num.upper()}"
        if len(code) >= 5 and not any(c in code for c in ".#"):
            return code
    # Prefer "EE 382N" over "EE 382" when text has "382 N" (letter suffix)
    skip_suffix = {"or", "and", "to"}
    for m in re.finditer(r"\b([A-Z]{2,4})\s*(\d{3})\s*([A-Z])\b", text[:800], re.I):
        prefix, base, suffix = m.group(1), m.group(2), m.group(3)
        if prefix.upper() in skip_prefixes or prefix.lower() in skip_suffix:
            continue
        return f"{prefix} {base}{suffix}".strip()
    m0 = re.match(r"^([A-Za-z]+)(\d{3}[A-Za-z]?)$", folder.replace("_", ""))
    if m0:
        folder_prefix, folder_num = m0.group(1), m0.group(2)
        folder_code = f"{folder_prefix} {folder_num}"
        pat = re.escape(folder_prefix) + r"\s*" + re.escape(folder_num)
        if re.search(pat, text[:1500], re.I):
            return folder_code
    # Prefer "EE 382N" over "EE 382" when text has "382 N" or "382N" (letter suffix)
    for m in re.finditer(r"\b([A-Z]{2,4})\s*(\d{3})\s*([A-Z])\b", text[:800], re.I):
        prefix, base, suffix = m.group(1), m.group(2), m.group(3)
        if prefix.upper() in skip_prefixes:
            continue
        if m0 and prefix.upper() != folder_prefix.upper():
            continue
        return f"{prefix} {base}{suffix}".strip()
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
    course_title_keywords = [
        "Data Structures", "Software Methodologies I", "Operating Systems",
        "Mobile News App Design", "Competitive Programming", "Solid State Physics I",
        "Carbon and 2D Devices", "C++ Programming",
        "Computer & Network Security", "Intermediate Algorithms",
        "Applied Cryptography", "Statistical Methods",
        "Elementary Discrete Mathematics II", "Computer Science I",
        "Computer Science III", "Introduction to Computer Science 2",
        "Concepts in Programming Languages", "Introduction to Computer Networks",
        "C/C++ and Unix", "The Solar System",
        "Introduction to Comparative Literature I", "Natural Environment",
        "Personal Finance", "Foundations of Data Science I",
        "Introduction to Modern Cryptography", "Mathematical Reasoning",
        "Introduction to Statistics", "Scientific and Technical Writing",
        "Tennis I", "Introduction to the Practice of Statistics",
        "Calculus III", "Geomorphology", "Entrepreneurship in CS",
        "Introduction to Software Engineering", "Climatology",
        "Career/Internship seminar", "Statistical Models and Methods",
        "Computer Fluency",
    ]
    # "Physics 336k, Classical Dynamics, Spring 2016" or "CS 331, Algorithms and Complexity"
    for line in lines[:8]:
        line = line.strip()
        m = re.match(r"^[A-Za-z]+\s+\d{3}[A-Za-z]?\s*,\s*([^,]{5,70}?)(?:\s*,\s*(?:Fall|Spring|Summer|Winter)\s+\d{4})?\s*$", line, re.I)
        if m:
            t = m.group(1).strip()
            if t and len(t) > 4 and not t.endswith("%"):
                return t[:80]
    for line in lines[:25]:
        line = line.strip()
        # "Math 253 - 33082, Calculus III - Syllabus"
        m = re.search(
            r"[A-Z]{2,4}\s*\d{3}[A-Z]?\s*[-–]\s*\d+\s*,\s*([^\-]+?)\s*[-–]\s*Syllabus",
            line, re.I
        )
        if m:
            t = m.group(1).strip()
            if 5 < len(t) < 60:
                return t
        m = re.search(
            r"[A-Z]{2,4}\s*\d{3}[A-Z]?\s*[\(\-\s]*(?:Fall|Winter|Spring|Summer)?\s*\d{4}?\s*"
            r"[;\)\s]*\s*([^\.\n]{5,80}?)(?:\s*$|\s+[A-Z]|\s+Syllabus)",
            line, re.I
        )
        if m:
            title = m.group(1).strip()
            if title and len(title) < 80 and not title.endswith("%"):
                if title.lower().startswith(("or ", "and ", "to ")):
                    continue
                return title[:100]
        m = re.search(
            r"(?:Welcome to|Course:?)\s*[A-Z]{2,4}\s*\d{3}[A-Z]?[,:\s]+(.+?)(?:\.|$)",
            line, re.I
        )
        if m:
            title = m.group(1).strip()
            if title and 5 < len(title) < 80:
                return title[:100]
        m = re.match(
            r"^[A-Z]{2,4}\s*\d{3}[A-Z]?\s+[\-\s]+(.{5,80})$", line, re.I
        )
        if m:
            return m.group(1).strip()[:100]
        for kw in course_title_keywords:
            if kw.lower() in line.lower() and len(line) < 120:
                return kw
    return ""


def parse_instructors(text: str) -> list:
    """Extract instructor and TA names and emails."""
    instructors = []
    seen_emails: set[str] = set()

    # --- Teaching Team block: "Teaching Team" with two-column "Name (Instructor) Name (GE)" format
    # e.g. "Juan Flores (Instructor) Hritvik Jekki (GE)" then "Office: X Office: Y", "Email: X E-mail: Y", "Zoom: X Zoom: Y"
    teaching_team = re.search(
        r"(?:^|\n)\s*Teaching\s+Team\s*(?:\n|$)(.+?)(?=(?:^|\n)\s*(?:Course\s+Overview|Description|Prerequisites|1\.\s|2\.\s|\d+\.\s))",
        text[:4000], re.I | re.DOTALL
    )
    if teaching_team:
        block = teaching_team.group(1).strip()
        # Extract names with roles: "Name (Instructor)", "Name (GE)", "Name (TA)"
        names_with_roles = []
        for role in ["Instructor", "GE", "TA"]:
            for name_m in re.finditer(
                r"([A-Za-z][A-Za-z\.\s\-']{2,40}?)\s*\(\s*" + re.escape(role) + r"\s*\)",
                block, re.I
            ):
                name = re.sub(r"\s+", " ", name_m.group(1).strip())
                if len(name) >= 3 and name.lower() not in ("email", "office", "zoom"):
                    names_with_roles.append((name, name_m.start()))
        names_with_roles.sort(key=lambda x: x[1])
        # Extract emails, offices, zoom URLs in order (two columns = 2 of each)
        emails = re.findall(r"(?:Email|E-mail)\s*:\s*([a-z0-9_.+-]+@[a-z0-9.-]+\.(?:edu|com|org))", block, re.I)
        offices = re.findall(r"Office\s*:\s*([A-Za-z0-9\s\-]+?)(?=\s*Office\s*:|\s*(?:Email|E-mail|Zoom)|\s*$|\n)", block, re.I)
        zooms = re.findall(r"Zoom\s*:\s*(https?://[^\s\)]+)", block, re.I)
        for idx, (name, _) in enumerate(names_with_roles):
            email = emails[idx].lower() if idx < len(emails) else None
            office = offices[idx].strip() if idx < len(offices) else None
            zoom_url = zooms[idx].strip() if idx < len(zooms) else None
            if email and email in seen_emails:
                continue
            if email:
                seen_emails.add(email)
            if not any(i.get("name") == name for i in instructors):
                inst = {"id": f"inst-{len(instructors)}", "name": name, "email": email}
                if office:
                    inst["office"] = office
                if zoom_url:
                    inst["zoom_url"] = zoom_url
                instructors.append(inst)

    # --- Instructor block: "Instructor" or "Course Instructor" header, then bullet lines with name + Email:
    # e.g. "Instructor\n• Prof Jun Li\n• Email: lijun@uoregon.edu"
    inst_blocks = list(re.finditer(
        r"(?:^|\n)\s*(?:Course\s+)?Instructor\s*(?:\n|$)",
        text[:5000], re.I
    ))
    for inst_m in inst_blocks:
        block_start = inst_m.end()
        block_end = min(block_start + 600, len(text))
        block = text[block_start:block_end]
        # Stop at next major section (TA, Prerequisites, etc.)
        next_section = re.search(r"(?:^|\n)(?:TA|Teaching\s+Assistant|Prerequisites|Textbooks|Course\s+Description)\s", block, re.I | re.M)
        if next_section:
            block = block[:next_section.start()]
        for name_m in re.finditer(
            r"(?:^|\n)\s*[•\-\*]?\s*([A-Za-z][A-Za-z\.\s\-']{2,50}?)(?=\s*\n|\s+Email\s*:|\s*$)",
            block, re.M
        ):
            name = re.sub(r"\s+", " ", name_m.group(1).strip())
            if len(name) < 3 or name.lower() in ("email", "office", "hours", "name", "n/a", "tbd"):
                continue
            if re.match(r"^(Instructor|Professor|Office|Email|Course)\s*$", name, re.I):
                continue
            # Skip "Prof" as standalone - look for "Prof Jun Li" style
            if name.lower() == "prof":
                continue
            after_name = block[name_m.end():name_m.end() + 250]
            email_m = re.search(r"Email\s*:\s*([a-z0-9_.+-]+@[a-z0-9.-]+\.(?:edu|com|org))", after_name, re.I)
            email = email_m.group(1).lower() if email_m else None
            if email and email in seen_emails:
                continue
            if email:
                seen_emails.add(email)
            if not any(i.get("name") == name and (i.get("email") == email or (not i.get("email") and not email)) for i in instructors):
                instructors.append({
                    "id": f"inst-{len(instructors)}", "name": name, "email": email
                })
            break  # one instructor per block

    # --- Primary instructor: "Instructor", "Professor", "Name" : Name ...
    for m in re.finditer(
        r"(?:Instructor|Course instructor|Professor|Name)\s*(?:Contact)?\s*[:\t]+\s*"
        r"([A-Za-z][A-Za-z\.\s\-']+?)(?:\s+Office|\s+Email|\s*$|\s*\n|\t)",
        text[:4000], re.I,
    ):
        name = re.sub(r"\s+", " ", m.group(1).strip())
        if 3 < len(name) < 60 and name.lower() not in ("download", "none", "n/a"):
            if not any(i.get("name") == name for i in instructors):
                instructors.append({
                    "id": f"inst-{len(instructors)}", "name": name, "email": None
                })

    # --- "Name Instructor/Professor/TA email@..." on one line
    for m in re.finditer(
        r"^([A-Za-z][A-Za-z\.\s\-']+)\s+(?:Instructor|Professor|TA)\s+"
        r"([a-z0-9_.+-]+@[a-z0-9.-]+\.(?:edu|com|org))",
        text[:5000], re.M | re.I
    ):
        name = re.sub(r"\s+", " ", m.group(1).strip())
        email = m.group(2).lower()
        if email not in seen_emails:
            seen_emails.add(email)
            instructors.append({
                "id": f"inst-{len(instructors)}", "name": name, "email": email
            })

    # --- TA block: line "TA" or "Teaching Assistant" or "Graduate Teaching Assistants" then name + Email:
    ta_blocks = list(re.finditer(
        r"(?:^|\n)\s*(?:TA|Teaching\s+Assistant|Graduate\s+Teaching\s+Assistants?|Undergraduate\s+Learning\s+Assistants?)\s*(?:\n|$)",
        text[:5000], re.I
    ))
    for ta_m in ta_blocks:
        block_start = ta_m.end()
        block_end = min(block_start + 800, len(text))
        block = text[block_start:block_end]
        # Name on next line(s): "• Name" or "Name" at start of line (2-4 words), then optional "Email: ..."
        for name_m in re.finditer(
            r"(?:^|\n)\s*[•\-\*]?\s*([A-Za-z][A-Za-z\.\s\-']{2,50}?)(?=\s*\n|\s+Email\s*:|\s*$)",
            block, re.M
        ):
            name = re.sub(r"\s+", " ", name_m.group(1).strip())
            if len(name) < 4 or name.lower() in ("email", "office", "hours", "name", "n/a", "tbd"):
                continue
            # Skip if it looks like a section header
            if re.match(r"^(Instructor|Professor|Office|Email|Course)\s*$", name, re.I):
                continue
            # Find Email: on same or following lines within this block
            after_name = block[name_m.end():name_m.end() + 200]
            email_m = re.search(r"Email\s*:\s*([a-z0-9_.+-]+@[a-z0-9.-]+\.(?:edu|com|org))", after_name, re.I)
            email = email_m.group(1).lower() if email_m else None
            if email and email in seen_emails:
                continue
            if email:
                seen_emails.add(email)
            if not any(i.get("name") == name and (i.get("email") == email or (not i.get("email") and not email)) for i in instructors):
                instructors.append({
                    "id": f"inst-{len(instructors)}", "name": name, "email": email
                })
            break  # one TA per block

    # --- Assign first unassigned edu email to first instructor missing email
    for m in re.finditer(r"([a-z0-9_.+-]+)@[a-z0-9.-]+\.(?:edu|com|org)", text[:6000], re.I):
        email = m.group(0).lower()
        if email in seen_emails:
            continue
        local = m.group(1).lower()
        assigned = False
        for inv in instructors:
            if inv.get("email"):
                continue
            name = (inv.get("name") or "").lower().split()
            first = (name[0][:5] if name else "").replace(".", "")
            if first and (local.startswith(first) or first in local):
                inv["email"] = email
                seen_emails.add(email)
                assigned = True
                break
        if not assigned and instructors and instructors[0].get("email") is None:
            instructors[0]["email"] = email
            seen_emails.add(email)
        break
    return instructors[:10] if instructors else []


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
