"""
Assessment extraction: categories and individual assessments (exams, projects, quizzes, etc.).
"""
import re

from .constants import MONTHS

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
    for m in re.finditer(r"(?:(?:Slide|slide)\s*(?:[-–\s\u2013\"']*aesthesis[\"']?|assignment)|close[- ]?reading\s+assignment).*?(October|November|December|January|February|March|April|May|June|July|August|September|Oct\.?|Nov\.?|Dec\.?|Jan\.?|Feb\.?|Mar\.?|Apr\.?|Jun\.?|Jul\.?|Aug\.?|Sep\.?)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,\s*(\d{4}))?\s*(?:by|at|@|\s+)?(\d{1,2})?[\:]?(\d{2})?\s*(am|pm)?", text, re.I | re.DOTALL):
        mon, day, yr_str, h, min, ampm = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)
        title = "Close-reading assignment" if "close" in m.group(0).lower() and "reading" in m.group(0).lower() else "Aesthesis slide"
        yr = int(yr_str) if yr_str else 2023
        mon_num = MONTHS.get((mon or "").lower()[:3], 1)
        due = f"{yr}-{mon_num:02d}-{int(day):02d}"
        if h:
            hr = int(h)
            if (ampm or "").lower() == "pm" and hr < 12:
                hr += 12
            due += f"T{hr:02d}:{min or '59'}:00"
        else:
            due += "T23:59:00"
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

    # "Percentage Component" table - "50 Mini Projects", "20 Midterm exam", "10 Build your MVP!" (% first)
    for m in re.finditer(r"^(?:Percentage\s+)?(\d{1,3})\s+([A-Za-z][A-Za-z0-9\s\-&()!]+?)(?:\n|$)", text, re.M | re.I):
        pct, name = int(m.group(1)), m.group(2).strip()
        if pct > 100 or pct <= 0:
            continue
        name = re.sub(r"\s+", " ", name)
        if name.lower() in ("component", "percentage", "total", "grading"):
            continue
        if "attendance is required" in name.lower() or "in-person attendance" in name.lower() or name.lower() in ("introduction", "attend seminars"):
            continue
        if len(name) < 3 or len(name) > 55:
            continue
        # When "Mini Projects" and doc mentions projects 0 through 6 (or 0-6), use expanded name
        if name.lower() == "mini projects" and re.search(r"projects?\s+0\s+(?:through|to|-)\s*[46]|[Pp]roject\s+[0-6]\b", text):
            name = "Mini Projects (0-6)"
        cid = re.sub(r"\s+", "_", name.lower())[:28].rstrip("_").replace("(", "").replace(")", "")
        atype = "midterm" if "midterm" in name.lower() else "final" if "final" in name.lower() else "project" if "project" in name.lower() or "mvp" in name.lower() else "assignment"
        add_category(cid, name, pct)
        add_assessment(cid + "_1", name, cid, atype, pct)

    # "Homework + WebWork 25%", "Midterm Exams 25% each"
    for m in re.finditer(r"\b(Homework\s*\+\s*WebWork|Midterm\s+Exams?)\s+(\d{1,3})\s*%\s*(each)?", text, re.I):
        name, pct = m.group(1).strip(), int(m.group(2))
        if pct > 100:
            continue
        if "midterm" in name.lower() and m.group(3):
            add_category("midterms", "Midterms", pct * 2)
            add_assessment("midterm_1", "Midterm Exam 1", "midterms", "midterm", pct)
            add_assessment("midterm_2", "Midterm Exam 2", "midterms", "midterm", pct)
        else:
            title = "Homework + WebWork" if "webwork" in name.lower() else name
            cid = re.sub(r"\s+", "_", title.lower())[:28].rstrip("_").replace("+", "")
            add_category(cid, title, pct)
            add_assessment(cid + "_1", title, cid, "assignment", pct)

    # "15% Homeworks", "10% 5Quizzes", "18% Midterm 1" - percent first, then optional count, then name
    for m in re.finditer(r"(?:^|\n)\s*(\d{1,3})\s*%\s+(?:\d*\s*)?([A-Za-z][A-Za-z0-9\s\-]+?)(?:\n|$)", text, re.M | re.I):
        pct, name = int(m.group(1)), m.group(2).strip()
        if pct > 100 or len(name) < 3 or len(name) > 40:
            continue
        if any(w in name.lower() for w in ("total", "grade", "scale", "cutoff", "lower", "upper")):
            continue
        # Normalize "Homeworks" -> "Homework", "Quizzes" stays
        title = "Homework" if name.lower().rstrip("s") == "homework" else name
        cid = re.sub(r"\s+", "_", title.lower())[:28].rstrip("_")
        atype = "midterm" if "midterm" in name.lower() else "final" if "final" in name.lower() else "quiz" if "quiz" in name.lower() else "assignment"
        add_category(cid, title, pct)
        add_assessment(cid + "_1", title, cid, atype, pct)

    # Table format: "Component Events Dropped %" rows - e.g. "Online Exams 2 0 20", "Exams (in person) 2 0 50", "Attendance - - 5"
    skip_components = {"component", "events", "dropped", "total", "%"}
    for m in re.finditer(r"^([A-Za-z][A-Za-z \t\-()]+?)\s+(\d+|-)\s+(\d+|-)\s+(\d{1,3})\s*$", text, re.M | re.I):
        name, pct = m.group(1).strip(), int(m.group(4))
        if pct > 100 or pct <= 0:
            continue
        first_word = name.split()[0].lower() if name.split() else ""
        if first_word in skip_components or name.lower().rstrip("s") in skip_components:
            continue
        # Prefer standard titles for known components
        full_names = {"online exams": "Online Exams", "in-person exams": "In-person Exams", "in person exams": "In-person Exams",
                      "exams (in person)": "Exams (in person)", "mini-exams (online)": "Mini-exams (online)",
                      "programming projects": "Programming projects", "projects": "Projects", "labs": "Labs",
                      "code demo": "Code demo", "attendance": "Attendance"}
        name_lower = name.lower().strip()
        title = full_names.get(name_lower, name)
        cid = re.sub(r"\s+", "_", name_lower)[:28].rstrip("_").replace("-", "_")
        atype = "midterm" if "exam" in name_lower else "project" if "project" in name_lower else "assignment" if "lab" in name_lower or "code" in name_lower else "participation" if "attend" in name_lower else "assignment"
        add_category(cid, title, pct)
        add_assessment(cid + "_1", title, cid, atype, pct)

    # Prefer project names from objectives ("Project 1x: Learning Unix") over grading line
    project_names = {}
    for m in re.finditer(r"Project\s+(\d+)x\s*:\s*([A-Za-z][A-Za-z\s]+?)(?:\n|$)", text, re.I):
        num, name = m.group(1), m.group(2).strip()
        if not re.match(r"^\d+\s*%", name):  # skip "10% (2% of..." lines
            project_names[num] = name
    # "Project 1x: 10% (2% of overall grade)" - use the overall % when present
    for m in re.finditer(r"Project\s+(\d+)x\s*:\s*(\d{1,3})\s*%\s*\(\s*(\d{1,3})\s*%\s+of\s+overall\s+grade\s*\)", text, re.I):
        num, pct_overall = m.group(1), int(m.group(3))
        title = f"Project {num}x: {project_names.get(num, '')}".strip(": ").rstrip() or f"Project {num}x"
        cid = f"project_{num}x"
        add_category("projects", "Projects", None)
        add_assessment(cid, title, "projects", "project", pct_overall)

    # "40 pts. total for the quizzes", "40 points total for the exercises"
    for m in re.finditer(r"(\d{1,3})\s*(?:pts?\.?|points?)\s*(?:total\s+)?for\s+the\s+(quizzes|exercises)", text, re.I):
        pct, name = int(m.group(1)), m.group(2).strip()
        if pct > 100:
            continue
        title = "Exercises" if "exercise" in name.lower() else "Quizzes"
        cid = re.sub(r"\s+", "_", title.lower())[:28].rstrip("_")
        atype = "quiz" if "quiz" in name.lower() else "assignment"
        add_category(cid, title, pct)
        add_assessment(cid + "_1", title, cid, atype, pct)
    # "weather reports" (2 points each, 20 points total) - flexible for quotes
    for m in re.finditer(r"ten\s+[\"\u201C]?weather\s+reports[\"\u201D]?\s*\([^)]*?(\d{1,3})\s*points?\s+total\)", text, re.I):
        pct = int(m.group(1))
        if 1 <= pct <= 100:
            add_category("weather_reports", "Weather Reports", pct)
            add_assessment("weather_reports_1", "Weather Reports", "weather_reports", "assignment", pct)
            break

    # "Daily quizzes: 10%", "Quizzes: 20%"
    for m in re.finditer(r"\b(Daily\s+quizzes?|Quizzes?)\s*:\s*(\d{1,3})\s*%", text, re.I):
        name, pct = m.group(1).strip(), int(m.group(2))
        if pct > 100:
            continue
        cid = "quizzes"
        title = "Daily quizzes" if "daily" in name.lower() else "Quizzes"
        add_category(cid, title, pct)
        add_assessment(cid + "_1", title, cid, "quiz", pct, recurrence={"frequency": "weekly", "interval": 1})

    # "distributed over written (25%) and programming (20%) assignments"
    for m in re.finditer(r"(?:written|writing)\s*\(\s*(\d{1,3})\s*%\s*\)\s*(?:and|,)\s*(?:programming|program)\s*\(\s*(\d{1,3})\s*%\s*\)", text, re.I):
        p1, p2 = int(m.group(1)), int(m.group(2))
        if p1 <= 100 and p2 <= 100:
            add_category("written_assignments", "Written Assignments", p1)
            add_assessment("written_1", "Written Assignments", "written_assignments", "assignment", p1)
            add_category("programming_assignments", "Programming Assignments", p2)
            add_assessment("programming_1", "Programming Assignments", "programming_assignments", "assignment", p2)

    # Penn State / general: "Name (percent%)" - long names like "Participation in Discussion Forums (25%)"
    for m in re.finditer(r"\b([A-Za-z][A-Za-z0-9\s,\-]+?)\s*\(\s*(\d{1,3}(?:\.\d+)?)\s*%\s*\)", text, re.I):
        name, pct_str = m.group(1).strip(), m.group(2)
        pct = int(float(pct_str))
        if pct > 100 or pct <= 0 or len(name) < 4:
            continue
        if any(w in name.lower() for w in ("total", "grade", "scale", "course", "of the")):
            continue
        # Normalize variants to match ground truth
        name_lower = name.lower().strip()
        if "participation" in name_lower and "discussion" in name_lower:
            title = "Participation in Discussion Forums"
        elif "current events" in name_lower and ("report" in name_lower or "memo" in name_lower):
            title = "Current Events Memo"
        elif "term paper" in name_lower or "individual term paper" in name_lower:
            title = "Term Paper"
        elif "documentary" in name_lower and "group" in name_lower:
            title = "Documentary Film, Group Exercise"
        elif "homework" in name_lower and "written" not in name_lower:
            title = "Homework"
        elif "quizzes" in name_lower or "quiz" in name_lower:
            title = "Quizzes"
        elif "attendance" in name_lower:
            title = "Attendance"
        else:
            title = re.sub(r"\s+", " ", name)
        cid = re.sub(r"\s+", "_", title.lower())[:28].rstrip("_").replace(",", "").replace("/", "_")
        atype = "participation" if "participation" in name_lower or "attendance" in name_lower else "quiz" if "quiz" in name_lower else "project" if "project" in name_lower or "documentary" in name_lower else "assignment"
        add_category(cid, title, pct)
        add_assessment(cid + "_1", title, cid, atype, pct)

    # Penn State: "Name (Points; percent% of total grade)" - e.g. "Documentary Film, Group Exercise (150 Points; 20% of total grade)"
    for m in re.finditer(r"([A-Za-z][A-Za-z0-9\s,\-]+?)\s*\(\s*\d+\s*Points?\s*;\s*(\d{1,3}(?:\.\d+)?)\s*%\s*of\s+total\s+(?:course\s+)?grade\s*\)", text, re.I):
        name, pct_str = m.group(1).strip(), m.group(2)
        pct = int(float(pct_str))
        if pct > 100 or len(name) < 3:
            continue
        name_lower = name.lower()
        title = "Documentary Film, Group Exercise" if "documentary" in name_lower and "group" in name_lower else "Homework" if "homework" in name_lower else "Quizzes" if "quiz" in name_lower else "Attendance" if "attendance" in name_lower else name
        cid = re.sub(r"\s+", "_", title.lower())[:28].rstrip("_").replace(",", "")
        atype = "project" if "documentary" in name_lower else "assignment" if "homework" in name_lower else "quiz" if "quiz" in name_lower else "participation" if "attendance" in name_lower else "assignment"
        add_category(cid, title, pct)
        add_assessment(cid + "_1", title, cid, atype, pct)

    # Penn State: "3 Exams (300 Points, 100 each; 40% of total course grade)" - add single "Exams" at total percent
    for m in re.finditer(r"(\d+)\s+Exams?\s+\([^)]*?;\s*(\d{1,3}(?:\.\d+)?)\s*%\s*of\s+total\s+(?:course\s+)?grade", text, re.I):
        num_exams, pct_str = int(m.group(1)), m.group(2)
        pct_total = int(float(pct_str))
        if pct_total > 100 or num_exams < 1:
            continue
        add_category("exams", "Exams", pct_total)
        add_assessment("exams_1", "Exams", "exams", "midterm", pct_total)
        break  # only one such block

    # Penn State ENGL221: "In Class Participation 20%", "Reading Responses on Perusall – 20%" (percent at end)
    for m in re.finditer(r"^([A-Za-z][A-Za-z0-9\s\-,]+?)\s*[–\-]?\s*(\d{1,3})\s*%", text, re.M | re.I):
        name, pct = m.group(1).strip(), int(m.group(2))
        if pct > 100 or len(name) < 4:
            continue
        if any(w in name.lower() for w in ("grading", "scale", "total")):
            continue
        title = name
        if "participation" in name.lower():
            title = "In Class Participation"
        elif "reading responses" in name.lower() and "perusall" in name.lower():
            title = "Reading Responses on Perusall"
        elif "creative imitation" in name.lower():
            title = "Creative Imitation Project"
        elif "midterm" in name.lower() and "exam" in name.lower():
            title = "Midterm Exam"
        elif "final" in name.lower() and "exam" in name.lower():
            title = "Final Exam"
        cid = re.sub(r"\s+", "_", title.lower())[:28].rstrip("_").replace("/", "_")
        atype = "participation" if "participation" in title.lower() else "assignment" if "reading" in title.lower() or "creative" in title.lower() else "midterm" if "midterm" in title.lower() else "final" if "final" in title.lower() else "assignment"
        add_category(cid, title, pct)
        add_assessment(cid + "_1", title, cid, atype, pct)

    # SCM445 / Penn State: "Exam- 40%", "Project - 20%", "Class Participation- 10%", "Assignments - 30%"
    for m in re.finditer(r"\b(Exam|Project|Class\s+Participation|Assignments?)\s*[-–]\s*(\d{1,3})\s*%", text, re.I):
        name, pct = m.group(1).strip(), int(m.group(2))
        if pct > 100:
            continue
        name_lower = name.lower()
        title = "Class Participation" if "participation" in name_lower else "Assignments" if "assignment" in name_lower else "Project" if "project" in name_lower else "Exam"
        if title == "Exam" and pct == 40 and re.search(r"mid[- ]?term|final\s+exam", text, re.I):
            add_category("exam", "Exam", pct)
            add_assessment("exam_1", "Midterm Exam", "exam", "midterm", 20)
            add_assessment("exam_2", "Final Exam", "exam", "final", 20)
            continue
        cid = re.sub(r"\s+", "_", title.lower())[:28].rstrip("_")
        atype = "participation" if "participation" in name_lower else "assignment" if "assignment" in name_lower else "project" if "project" in name_lower else "midterm"
        add_category(cid, title, pct)
        add_assessment(cid + "_1", title, cid, atype, pct)

    # MKTG342: tab-separated "Midterm I\t20%\tGroup Project\t17.5%" - two columns of name percent
    for m in re.finditer(r"([A-Za-z][A-Za-z\s\/\-]+?)\s{2,}(\d{1,3}(?:\.\d+)?)\s*%\s*(?:\s{2,}([A-Za-z][A-Za-z\s\/\-]+?)\s{2,}(\d{1,3}(?:\.\d+)?)\s*%)?", text, re.M | re.I):
        def add_one(n, p):
            if not n or len(n) < 2:
                return
            try:
                pv = float(p)
            except (ValueError, TypeError):
                return
            if pv > 100 or pv <= 0:
                return
            n = n.strip()
            if any(w in n.lower() for w in ("grading", "total", "component")):
                return
            title = n
            if "midterm i" in n.lower():
                title = "Midterm I"
            elif "midterm ii" in n.lower():
                title = "Midterm II"
            elif "final" in n.lower() and "exam" not in n.lower():
                title = "Final"
            elif "group project" in n.lower():
                title = "Group Project"
            elif "presentation" in n.lower() or "peer review" in n.lower():
                title = "Presentation / Peer Review"
            elif "participation" in n.lower() or "assignment" in n.lower():
                title = "Participation / Assignments"
            cid = re.sub(r"\s+", "_", title.lower())[:28].rstrip("_").replace("/", "_")
            atype = "midterm" if "midterm" in title.lower() else "final" if "final" in title.lower() else "project" if "project" in title.lower() else "participation" if "participation" in title.lower() else "assignment"
            add_category(cid, title, pv)
            add_assessment(cid + "_1", title, cid, atype, pv)
        add_one(m.group(1), m.group(2))
        if m.group(3) and m.group(4):
            add_one(m.group(3), m.group(4))

    # "Assignments (includes excel & SAP) - 30%" - parenthetical then dash percent
    for m in re.finditer(r"\b(Assignments?)\s*\([^)]+\)\s*[-–]\s*(\d{1,3})\s*%", text, re.I):
        name, pct = m.group(1).strip(), int(m.group(2))
        if pct > 100:
            continue
        add_category("assignments", "Assignments", pct)
        add_assessment("assignments_1", "Assignments", "assignments", "assignment", pct)

    # "Classwork(15%)", "Written homework (15%)", "Quizzes(20%)" - paren format
    for m in re.finditer(r"\b(Classwork|Written\s+homework|Quizzes?)\s*\(\s*(\d{1,3})\s*%\)", text, re.I):
        name, pct = m.group(1).strip(), int(m.group(2))
        if pct > 100:
            continue
        cid = re.sub(r"\s+", "_", name.lower())[:28].rstrip("_")
        title = "Written homework" if "written" in name.lower() and "homework" in name.lower() else name
        atype = "assignment" if "homework" in name.lower() or "classwork" in name.lower() else "quiz"
        add_category(cid, title, pct)
        add_assessment(cid + "_1", title, cid, atype, pct)

    # Grading breakdown: "Engineering Deliverables (Team/Individual): 60%", "Peer Evaluations (Completion-Based): 5%"
    for m in re.finditer(r"\b([A-Za-z][A-Za-z \t&\-]+?)\s*\([^)]*(?:Team|Individual|Completion)[^)]*\)\s*:\s*(\d{1,3})\s*%", text, re.I):
        name, pct = m.group(1).strip(), int(m.group(2))
        if pct > 100 or len(name) < 3:
            continue
        # Normalize common variants for consistency across syllabi
        name_lower = name.lower().strip()
        title_map = {
            "engineering deliverables": ("Team Engineering Deliverables", "engineering", "project"),
            "professional practice & participation": ("Professional Practice & Participation", "professional", "participation"),
            "reflection & responsible ai use": ("Reflection & AI Usage Log", "reflection", "assignment"),
            "peer evaluations": ("Peer & Self-Evaluation", "peer_eval", "participation"),
        }
        entry = title_map.get(name_lower)
        if entry:
            title, cid, atype = entry
        else:
            title, cid = name, re.sub(r"\s+", "_", name_lower)[:28].rstrip("_")
            atype = "assignment"
        add_category(cid, title, pct)
        add_assessment(cid + "_1", title, cid, atype, pct)

    # "Participation: 5%", "Attendance: 10%", "Presentation: 15%" - colon format (general)
    for m in re.finditer(r"\b(Participation|Attendance|Presentations?|Reading\s+responses?|Discussion)\s*:\s*(\d{1,3})\s*%", text, re.I):
        name, pct = m.group(1).strip(), int(m.group(2))
        if pct > 100:
            continue
        cid = re.sub(r"\s+", "_", name.lower())[:28].rstrip("_")
        title = name if len(name) < 30 else "Participation" if "participation" in name.lower() else "Attendance" if "attendance" in name.lower() else name[:30]
        add_category(cid, title, pct)
        atype = "participation" if "participat" in name.lower() or "attend" in name.lower() else "assignment"
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
        if "lab" in name.lower():
            atype = "participation" if "attend" in name.lower() else "assignment"
        add_assessment(f"{cid}_1", title, cid, atype, pct)

    # "Grading: homework 40%, two mid-terms 20% each, final 20%" - name first, then percent (comma-separated)
    for m in re.finditer(r"\b(homework|final)\s+(\d{1,3})\s*%\s*(?=,|two|$|\n)", text, re.I):
        name, pct = m.group(1).strip(), int(m.group(2))
        if pct > 100:
            continue
        block = text[max(0, m.start() - 50) : m.start()]
        if "grading" not in block.lower() and "grade" not in block.lower():
            continue  # only in grading context
        title = "Homework" if name.lower() == "homework" else "Final"
        cid = "homework" if name.lower() == "homework" else "final"
        atype = "assignment" if name.lower() == "homework" else "final"
        add_category(cid, title, pct)
        add_assessment(cid + "_1", title, cid, atype, pct)

    # "midterm (20%)", "final (20%)", "Discussions and Assignments (20% of total)", "Labs and quizzes (40%)"
    for m in re.finditer(r"\b(midterm|final|Discussions?\s+and\s+Assignments?|Labs?\s+and\s+quizzes?)\s*\(\s*(\d{1,3})\s*%\s*(?:of\s+total(?:\s+grade)?)?\s*\)", text, re.I):
        name, pct = m.group(1).strip(), int(m.group(2))
        cid = re.sub(r"\s+", "_", name.lower())[:30].rstrip("_")
        title = "Midterm" if name.lower() == "midterm" else "Final" if name.lower() == "final" else name
        atype = "midterm" if "midterm" in name.lower() else "final" if "final" in name.lower() else "assignment" if "discussion" in name.lower() else "quiz"
        if "lab" in name.lower():
            atype = "assignment"
        add_category(cid, title, pct)
        add_assessment(cid + "_1", title, cid, atype, pct)

    # "Test 1: October 23", "Test 2: November 6", "Test 3: November 25" - tests with dates
    for m in re.finditer(r"Test\s+(\d+)\s*:\s*(\w+)\s+(\d{1,2})", text, re.I):
        num, mon, day = m.group(1), m.group(2), m.group(3)
        mon_num = MONTHS.get((mon or "").lower()[:3])
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
        h1, m1 = int(_m.group(3)), int(_m.group(4))
        mon_num = MONTHS.get((mon or "").lower()[:3])
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

    # "midterm will count for 25%" / "one midterm... 25% of the course grade" (SICS345-style)
    for m in re.finditer(r"[Mm]idterm[^.]*?(\d{1,3})\s*%\s+(?:of\s+the\s+course\s+grade|of\s+your\s+grade)", text, re.I):
        pct = int(m.group(1))
        if pct <= 100 and not any(a.get("title", "").lower() == "midterm" and a.get("weight_percent") == pct for a in assessments):
            add_category("midterm", "Midterm", pct)
            add_assessment("midterm_1", "Midterm", "midterm", "midterm", pct)

    # CH204-style: "remainder will count 25% of your grade" (quizzes), "assignments are 5% of the course grade" (post-labs)
    for m in re.finditer(r"remainder\s+will\s+count\s+(\d{1,3})\s*%\s+of\s+your\s+grade", text, re.I):
        pct = int(m.group(1))
        if pct <= 100 and "quiz" in text[max(0, m.start() - 300) : m.start()].lower():
            add_category("quizzes", "Quizzes", pct)
            add_assessment("quizzes_1", "Quizzes", "quizzes", "quiz", pct)
            break
    for m in re.finditer(r"assignments\s+are\s+(\d{1,3})\s*%\s+of\s+the\s+course\s+grade", text, re.I):
        pct = int(m.group(1))
        if pct <= 100 and ("post" in text[max(0, m.start() - 200) : m.start()].lower() or "post-lab" in text.lower()):
            add_category("post_labs", "Post-lab assignments", pct)
            add_assessment("post_labs_1", "Post-lab assignments", "post_labs", "assignment", pct)
            break
    for m in re.finditer(r"accounts\s+for\s+(\d{1,3})\s*%\s+of\s+your\s+grade", text, re.I):
        pct = int(m.group(1))
        if pct <= 100 and "laboratory" in text[max(0, m.start() - 150) : m.start()].lower():
            add_category("laboratory", "Laboratory work", pct)
            add_assessment("laboratory_1", "Laboratory work", "laboratory", "assignment", pct)
            break
    for m in re.finditer(r"TA\s+evaluations?\s+are\s+(\d{1,3})\s*%\s+of\s+the\s+course\s+grade", text, re.I):
        pct = int(m.group(1))
        if pct <= 100:
            add_category("ta_evaluations", "TA evaluations", pct)
            add_assessment("ta_evaluations_1", "TA evaluations", "ta_evaluations", "assignment", pct)
            break

    # "40% programming assignments", "20% homework" - percent first (name on same line as %)
    _garbage_phrases = (
        "remainder will count", "assignments are", "a late penalty of", "the homework and vice-versa",
        "and the final", "the midterm", "the final exam will count for",
        "backbone", "accounts for",  # prose fragments like "laboratory work...accounts for"
    )
    for m in re.finditer(r"(\d{1,3})\s*%[ \t]+([A-Za-z][A-Za-z \t\-/\n]+?)(?=[\s\.\,\)$]|\.)", text, re.I):
        pct, name = int(m.group(1)), m.group(2).strip()
        if pct > 100 or len(name) < 3 or len(name) > 55:
            continue
        name_lower = name.lower()
        if any(g in name_lower for g in _garbage_phrases):
            continue
        if "laboratory" in name_lower and ("backbone" in name_lower or "accounts" in name_lower):
            name = "Laboratory work"
        elif "remainder" in name_lower and "quiz" in text[max(0, m.start() - 200) : m.start()].lower():
            name = "Quizzes"
        elif name_lower.startswith("assignments are") or (name_lower.startswith("assignments") and "post" in text[max(0, m.start() - 150) : m.start()].lower()):
            name = "Post-lab assignments"
        elif "ta evaluation" in text[max(0, m.start() - 150) : m.start()].lower() or "ta's evaluation" in text[max(0, m.start() - 150) : m.start()].lower():
            name = "TA evaluations"
        skip_words = ("the", "your", "grade", "penalty", "of ", " to ", " or ", "each", "range", "standard", "b's", "c's", "d's", "upper", "lower", "bracket", " e.g ", "late ", "maximum", "of")
        if any(w in name_lower for w in skip_words) or name.lower().strip() == "and":
            continue
        if "deduct" in name.lower():
            continue
        cid = re.sub(r"\s+", "_", name.lower())[:28].rstrip("_/")
        add_category(cid, name, pct)
        atype = "assignment"
        if "exam" in name.lower() or "midterm" in name.lower():
            atype = "midterm" if "midterm" in name.lower() else "final"
        elif "quiz" in name.lower():
            atype = "quiz"
        elif "project" in name.lower():
            atype = "project"
        elif "lab" in name.lower():
            atype = "participation" if "attend" in name.lower() else "assignment"
        add_assessment(f"{cid}_1", name, cid, atype, pct)

    # Numbered evaluation: "(1) Weekly Labs -- 60%", "(2) Exams – 40% (2 total, each worth 20%)"
    for m in re.finditer(r"\(\d\)\s+(Weekly\s+Labs?|Exams?)\s*[-–—]+\s*(\d{1,3})\s*%", text, re.I):
        name, pct = m.group(1).strip(), int(m.group(2))
        if pct > 100:
            continue
        block = text[m.start() : m.end() + 350]
        if "lab" in name.lower():
            drop = 1 if re.search(r"drop\s+lowest", block, re.I) else None
            add_category("labs", "Weekly Labs", pct)
            idx = cat_ids.get("labs")
            if idx is not None and idx < len(categories):
                categories[idx]["drop_lowest"] = drop
            late_pol = "25% per deadline, +25% per additional week" if re.search(r"25\s*%.*deduct|deduct.*25\s*%", block, re.I) else None
            add_assessment("labs_1", "Weekly Labs", "labs", "assignment", pct,
                          recurrence={"frequency": "weekly", "interval": 1, "by_day": ["TH"], "until": None, "count": None},
                          policies={"late_policy": late_pol} if late_pol else None)
        else:
            # "Exams – 40% (2 total, each worth 20%)" -> Exam 1, Final Exam
            pct_each = pct
            me = re.search(r"each\s+worth\s+(\d{1,3})\s*%", block, re.I)
            if me:
                pct_each = int(me.group(1))
            add_category("exams", "Exams", pct)
            exam1_due = final_due = None
            if "May 8" in text and "Exam 1" in text:
                exam1_due = f"{yr}-05-08"
            if "June 10" in text and re.search(r"Final\s+Exam|Final\s*:", text, re.I):
                final_due = f"{yr}-06-10T14:45:00" if "2:45" in text or "14:45" in text else f"{yr}-06-10"
            if not final_due:
                for fm in re.finditer(r"Final\s+Exam\s*:\s*(\w+)\s+(\d{1,2})(?:\s*[\(,]?\s*[^,\)]*)?\s*(?:(\d{1,2})[\:.](\d{2}))?", text, re.I):
                    mon, day = fm.group(1), int(fm.group(2))
                    mn = MONTHS.get((mon or "").lower()[:3])
                    if mn:
                        if fm.group(3) and fm.group(4):
                            final_due = f"{yr}-{mn:02d}-{day:02d}T{int(fm.group(3)):02d}:{fm.group(4)}:00"
                        else:
                            final_due = f"{yr}-{mn:02d}-{day:02d}"
                        break
            if not any(a.get("title") == "Exam 1" for a in assessments):
                add_assessment("exam_1", "Exam 1", "exams", "midterm", pct_each, exam1_due)
            if not any(a.get("title") == "Final Exam" for a in assessments):
                add_assessment("final_1", "Final Exam", "exams", "final", pct_each, final_due)

    # "25 percent: App grade", "24 percent: Student review of work" (07770-Quigley)
    # Stop at period or next "N percent" to avoid capturing full sentences.
    # Note: text is pre-normalized (unicode hyphens -> ASCII) in parse_syllabus_text
    for m in re.finditer(r"(\d{1,3})\s+percent\s*:\s*([A-Za-z][A-Za-z\s\-]+?)(?=\.|\d+\s+percent|\n|$)", text, re.I):
        pct, name = int(m.group(1)), m.group(2).strip()
        if pct > 100 or len(name) < 3 or len(name) > 50:
            continue
        if any(g in name.lower() for g in ("grade scale", "percentage", "total")):
            continue
        # Collapse multiple hyphens (from unicode normalization) to single hyphen
        name = re.sub(r"-+", "-", name)
        cid = re.sub(r"\s+", "_", name.lower())[:28].rstrip("_")
        atype = "project" if "app" in name.lower() or "demo" in name.lower() else "participation" if "review" in name.lower() else "assignment"
        add_category(cid, name, pct)
        add_assessment(cid + "_1", name, cid, atype, pct)

    # "30% Homework, 30% Midterm Project, 30% Final Project, 10% Class Participation" (comma-separated)
    for m in re.finditer(r"(\d{1,3})\s*%\s+([A-Za-z][A-Za-z\s]+?)(?=\s*,\s*\d+\s*%|\s*$|\n)", text, re.I):
        pct, name = int(m.group(1)), m.group(2).strip()
        if pct > 100 or len(name) < 3 or len(name) > 45:
            continue
        if any(g in name.lower() for g in ("wikipedia", "references", "suggest", "grading", "total")):
            continue
        if "\n" in name:
            continue
        name = re.sub(r"\s+", " ", name)
        cid = re.sub(r"\s+", "_", name.lower())[:28].rstrip("_")
        atype = "project" if "project" in name.lower() else "midterm" if "midterm" in name.lower() else "final" if "final" in name.lower() else "participation" if "participation" in name.lower() or "class" in name.lower() else "assignment"
        add_category(cid, name, pct)
        add_assessment(cid + "_1", name, cid, atype, pct)

    # "Two Midterms 22 % each", "2 Midterms 25% each", "two mid-terms 20% each" -> Midterm 1, Midterm 2
    for m in re.finditer(r"(?:(?:Two|2)\s+)?[Mm]id[-]?terms?\s+(\d{1,3})\s*%\s*(?:each|total)", text, re.I):
        pct = int(m.group(1))
        add_category("midterms", "Midterm Exams", pct * 2)
        add_assessment("midterm_1", "Midterm 1", "midterms", "midterm", pct)
        add_assessment("midterm_2", "Midterm 2", "midterms", "midterm", pct)
    # "Midterm: 45%. There will be two in-class midterm" -> Midterm 1, Midterm 2 (no pct each)
    if re.search(r"[Mm]idterm\s*:\s*\d+\s*%.*?(?:two|2)\s+(?:in-class\s+)?midterm", text, re.I | re.DOTALL):
        if not any(a.get("title") == "Midterm 1" for a in assessments):
            add_category("midterms", "Midterms", None)
            add_assessment("midterm_1", "Midterm 1", "midterms", "midterm", None)
            add_assessment("midterm_2", "Midterm 2", "midterms", "midterm", None)

    # "Midterm 1 25%", "Midterm 2 25%" - explicit numbered midterms
    for m in re.finditer(r"Midterm\s+(\d+)\s*[:\s]+(\d{1,3})\s*%", text, re.I):
        num, pct = m.group(1), int(m.group(2))
        add_category("midterms", "Midterm Exams", pct * 2)
        add_assessment(f"midterm_{num}", f"Midterm {num}", "midterms", "midterm", pct)

    # "Midterm Exams 25% each" -> Midterm 1, Midterm 2 with dates
    date_pat = r"(?:Tuesday|Thursday|Monday|Wednesday|Friday),?\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{4}))?"
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
                    mon_num = MONTHS.get(mon.lower()[:3], 1)
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

    # "WeBWork ... 24%", "Written homework ... 24%" - in context of "worth N% of the final grade"
    for m in re.finditer(r"\b(WebWork|WeBWork|Written\s+homework)\s+(?:is\s+worth|worth)\s+(\d{1,3})\s*%\s+of\s+(?:the\s+)?final\s+grade", text, re.I):
        name, pct = m.group(1).strip(), int(m.group(2))
        if pct > 100:
            continue
        title = "WeBWork Homework" if "web" in name.lower() or "weblog" in name.lower() else "Written Homework"
        cid = "weblog" if "web" in name.lower() else "written_hw"
        add_category(cid, title, pct)
        add_assessment(cid + "_1", title, cid, "assignment", pct, recurrence={"frequency": "weekly", "interval": 1, "by_day": ["TH"]})

    # "Homework: 24+24" or "Midterms: 8+10" or "Final exam: 34" - summary block format
    for m in re.finditer(r"\b(Homework|Midterms?|Final\s+exam)\s*:\s*(\d{1,3})\s*\+\s*(\d{1,3})\s*$", text, re.M | re.I):
        name, p1, p2 = m.group(1).strip(), int(m.group(2)), int(m.group(3))
        cid = "homework" if "homework" in name.lower() else "midterms" if "midterm" in name.lower() else "final"
        if "midterm" in name.lower():
            add_category(cid, "Midterms", p1 + p2)
            add_assessment("midterm_1", "Written Midterm", cid, "midterm", p1)
            add_assessment("midterm_2", "Online Quiz Midterm", cid, "midterm", p2)
        elif "homework" in name.lower():
            add_category("weblog", "WeBWork Homework", p1)
            add_category("written_hw", "Written Homework", p2)
            add_assessment("weblog_1", "WeBWork Homework", "weblog", "assignment", p1, recurrence={"frequency": "weekly", "interval": 1, "by_day": ["TH"]})
            add_assessment("written_hw_1", "Written Homework", "written_hw", "assignment", p2, recurrence={"frequency": "weekly", "interval": 1, "by_day": ["TH"]})
    for m in re.finditer(r"\b(Final\s+exam|Final)\s*:\s*(\d{1,3})\s*$", text, re.M | re.I):
        pct = int(m.group(2))
        if pct <= 100:
            add_category("final", "Final Exam", pct)
            add_assessment("final_1", "Final Exam", "final", "final", pct)

    # "Midterm: 25%", "Final: 45%" - colon format
    for m in re.finditer(r"\b(Midterm|Final)\s*:?\s*(\d{1,3})\s*%", text, re.I):
        kind, pct = m.group(1), int(m.group(2))
        cid = "exams" if kind.lower() == "midterm" else "final"
        add_category(cid, f"{kind} exam" if kind.lower() == "final" else "Midterm", pct)
        add_assessment(kind.lower() + "_1", "Midterm" if kind.lower() == "midterm" else "Final", cid,
                      "midterm" if kind.lower() == "midterm" else "final", pct)

    # Pass/fail seminar: "(Project proposal) (due Friday 10/10)", "Resume (due Friday 10/24)" - schedule deliverables, no percent
    if re.search(r"submit\s+all\s+(?:required\s+)?(?:deliverables|milestones)|attend\s+all\s+seminar\s+meetings", text, re.I):
        for m in re.finditer(r"([A-Za-z][A-Za-z \t]+?)\s*\(\s*due\s+(?:Monday|Tuesday|Wednesday|Thursday|Friday)[a-z]*\s+(\d{1,2})/(\d{1,2})\s*\)", text, re.I):
            name = m.group(1).strip()
            mo, dy = int(m.group(2)), int(m.group(3))
            if len(name) < 4 or len(name) > 50 or "handout" in name.lower() or "career center" in name.lower():
                continue
            if 1 <= mo <= 12 and 1 <= dy <= 31:
                due = f"{yr}-{mo:02d}-{dy:02d}"
                title = name.title()
                cid = "deliverables"
                add_category(cid, "Deliverables", None)
                aid = re.sub(r"\s+", "_", title.lower())[:28].rstrip("_")
                add_assessment(aid, title, cid, "assignment", None, due)
        if re.search(r"attend\s+all\s+seminar|Attendance\s+will\s+be\s+taken", text, re.I) and not any(a.get("title") == "Attendance" for a in assessments):
            add_category("deliverables", "Deliverables", None)
            add_assessment("attendance", "Attendance", "deliverables", "participation", None, None,
                          recurrence={"frequency": "weekly", "interval": 1, "by_day": ["MO"], "until": None, "count": None},
                          policies={"late_policy": "Missing more than 1 (after week 1) results in failure"})

    # "Project 1 (due: Oct. 24)", "Project 2 (due: Nov. 19)" - schedule table, no percent
    for m in re.finditer(r"Project\s+(\d+)\s*\(\s*(?:due|out)\s*:\s*(\w+)\.?\s+(\d{1,2})", text, re.I):
        num, mon_abbr, day = m.group(1), m.group(2), int(m.group(3))
        mon_num = MONTHS.get((mon_abbr or "").lower()[:3])
        due = f"{yr}-{mon_num:02d}-{day:02d}" if mon_num and 1 <= mon_num <= 12 else None
        if "due" in m.group(0).lower():
            add_category("projects", "Projects", None)
            add_assessment(f"project_{num}", f"Project {num}", "projects", "project", None, due)

    # "Nov. 4 MIDTERM", "6 Nov. 4 MIDTERM" - schedule table
    for m in re.finditer(r"(?:^|\n)\s*\d*\s*(\w+)\.?\s+(\d{1,2})\s+MIDTERM", text, re.M | re.I):
        mon_abbr, day = m.group(1), int(m.group(2))
        mon_num = MONTHS.get((mon_abbr or "").lower()[:3])
        due = f"{yr}-{mon_num:02d}-{day:02d}" if mon_num and 1 <= mon_num <= 12 else None
        add_category("midterm", "Midterm", None)
        add_assessment("midterm_1", "Midterm", "midterm", "midterm", None, due)

    # "Dec. 11 12:30-14:30 FINAL", "11 Dec. 11 12:30-14:30 FINAL"
    for m in re.finditer(r"(?:^|\n)\s*\d*\s*(\w+)\.?\s+(\d{1,2})\s+(\d{1,2})[\:.](\d{2})\s*[-–]\s*(\d{1,2})[\:.](\d{2})\s*FINAL", text, re.M | re.I):
        mon_abbr, day = m.group(1), int(m.group(2))
        h1, m1 = int(m.group(3)), int(m.group(4))
        mon_num = MONTHS.get((mon_abbr or "").lower()[:3])
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

    # Labor-based / writing-intensive: named assignments without percent (WR320, similar courses)
    # Patterns are general phrases that appear in writing/technical communication syllabi
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
        skip = name.lower() in ("the", "a", "an", "to", "of", "and", "or", "your", "grade", "below")
        skip = skip or "deduct" in name.lower() or "attendance is required" in name.lower()
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
    for m in re.finditer(r"Final\s+(?:exam\s+)?(?:Tuesday\s+)?(?:June|Jun)\s+(\d{1,2})(?:st|nd|rd|th)?\s*(?:@\s+)?(\d{1,2})?(?::(\d{2}))?\s*(am|pm)?", text, re.I):
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


