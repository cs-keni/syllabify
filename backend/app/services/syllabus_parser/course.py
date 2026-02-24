"""
Course metadata extraction: code, title, term, instructors.
"""
import re


def parse_course_code(text: str, folder: str) -> str:
    """Extract course code (e.g. CS 210) from text or folder."""
    skip_prefixes = {
        "ROOM", "WEEK", "OCT", "NOV", "DEC", "JAN", "FEB", "MAR", "APR",
        "JUN", "JUL", "AUG", "SEP", "MTWR", "PLC", "DES", "MCK", "LIL",
    }
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
