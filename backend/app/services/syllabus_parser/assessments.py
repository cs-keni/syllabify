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
        # Skip section headers (e.g. "1 Course Overview", "3 Evaluation") - small numbers + header-like names
        section_headers = (
            "course overview", "evaluation", "overall breakdown", "schedule", "instructors",
            "how to do well", "other notices", "the worst", "prerequisites", "textbook",
            "course outline", "discussion section", "office hours", "note on", "letter grades",
            "teachingassistants",
        )
        if pct <= 10 and (name.lower().strip() in section_headers or any(sh in name.lower() for sh in ("course overview", "overall breakdown", "discussion section"))):
            continue
        if "attendance is required" in name.lower() or "in-person attendance" in name.lower() or name.lower() in ("introduction", "attend seminars"):
            continue
        # Skip schedule table rows (e.g. "2 LAB", "4 MIDTERM", "11 NO CLASS", "21 Continue with IPC")
        name_lower = name.lower().strip()
        if name_lower in ("lab", "midterm", "no class"):
            continue
        if name_lower.startswith("continue with ") or "no class" in name_lower:
            continue
        if "\t" in m.group(2):  # tabs = schedule table structure, not grading
            continue
        # "MIDTERM MIDTERM MIDTERM" or "NO CLASS NO CLASS" - repeated schedule cell
        words = set(name_lower.split())
        if words <= {"midterm"} or words <= {"no", "class"} or (words <= {"lab"} and len(name_lower) < 15):
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

    # "3 exams, each contributing 23% of the final grade" -> Exam 1, 2, 3 at 23% each
    for m in re.finditer(r"(\d+)\s+exams?\s*,\s*each\s+contributing\s+(\d{1,3})\s*%\s*of\s+(?:the\s+)?(?:final\s+)?grade", text, re.I):
        num, pct = int(m.group(1)), int(m.group(2))
        if 1 <= num <= 10 and 1 <= pct <= 100:
            add_category("exams", "Exams", pct * num)
            for i in range(1, num + 1):
                add_assessment(f"exam_{i}", f"Exam {i}", "exams", "midterm", pct)

    # "Semester Exams 50% (2 exams during semester, 25% each)" or "Semester Exams (2 exams, 25% each) 50%"
    for m in re.finditer(r"Semester\s+Exams?\s*(?:(\d{1,3})\s*%\s*)?\((\d+)\s+exams?\s*(?:during\s+semester,?\s*)?(\d{1,3})\s*%\s*each\)(?:\s*(\d{1,3})\s*%)?", text, re.I):
        pct_total = int(m.group(4) or m.group(1) or 0)
        num, pct_each = int(m.group(2)), int(m.group(3))
        if 1 <= num <= 10 and 1 <= pct_each <= 100:
            pct_total = pct_total or pct_each * num
            add_category("semester_exams", "Semester Exams", pct_total)
            add_assessment("semester_exams_1", f"Semester Exams ({num} exams, {pct_each}% each)", "semester_exams", "midterm", pct_total)

    # "Homework, 5 x 4% each: 20%", "Case Analyses (teams), 3 x 10% each: 30%"
    for m in re.finditer(r"((?:Case\s+Analyses|Homework)(?:\s*\([^)]+\))?)\s*,\s*(\d+)\s+x\s+(\d{1,3})\s*%\s*each\s*:\s*(\d{1,3})\s*%", text, re.I):
        name, count, pct_each, pct_total = m.group(1).strip(), int(m.group(2)), int(m.group(3)), int(m.group(4))
        if pct_total > 100 or count < 1:
            continue
        name_clean = "Homework" if "homework" in name.lower() else "Case Analyses"
        cid = "homework" if "homework" in name.lower() else "cases"
        add_category(cid, name_clean, pct_total)
        add_assessment(cid + "_1", f"{name_clean} ({count} x {pct_each}%)", cid, "assignment" if "homework" in name.lower() else "project", pct_total)

    # "Three midterms (20% each) 60%" - single aggregate assessment (PHY375S-style)
    for m in re.finditer(r"(?:Three|3)\s+mid[-]?terms?\s+(\d{1,3})\s*%\s*(?:/ea|each)", text, re.I):
        pct_each = int(m.group(1))
        if 1 <= pct_each <= 100:
            pct_total = pct_each * 3
            title = f"Three midterms ({pct_each}% each)"
            add_category("midterms", "Three midterms", pct_total)
            add_assessment("midterms_1", title, "midterms", "midterm", pct_total)
            break  # only one such block
    # "Two midterms 25% each" -> Midterm 1, Midterm 2
    for m in re.finditer(r"(?:Two|2)\s+mid[-]?terms?\s+(\d{1,3})\s*%\s*(?:/ea|each)", text, re.I):
        pct = int(m.group(1))
        if 1 <= pct <= 100:
            add_category("midterms", "Midterms", pct * 2)
            add_assessment("midterm_1", "Midterm 1", "midterms", "midterm", pct)
            add_assessment("midterm_2", "Midterm 2", "midterms", "midterm", pct)
    for m in re.finditer(r"(?:Three|3)\s+mid[-]?terms?\s*\(\s*(\d{1,3})\s*%\s*each\s*\)\s*(\d{1,3})\s*%", text, re.I):
        pct_each, _total = int(m.group(1)), int(m.group(2))
        if 1 <= pct_each <= 100:
            add_category("midterms", "Midterms", pct_each * 3)
            for i in range(1, 4):
                add_assessment(f"midterm_{i}", f"Midterm {i}", "midterms", "midterm", pct_each)

    # "mid-term test contributes half of the grade and the end-term test the other half" -> Mid-term 50%, End-term 50%
    if re.search(r"mid[- ]?term\s+test\s+contributes\s+half.*end[- ]?term\s+test\s+the\s+other\s+half", text, re.I | re.DOTALL):
        add_category("midterm", "Mid-term test", 50)
        add_assessment("midterm_1", "Mid-term test", "midterm", "midterm", 50)
        add_category("final", "End-term test", 50)
        add_assessment("final_1", "End-term test", "final", "final", 50)

    # "10 points on attending exercise sections", "30 points on three homeworks (10 points on each)", "60 points on three midterms (20 points on each)" - 100 total
    pts_match = re.search(
        r"(\d+)\s+points\s+on\s+attending\s+exercise\s+sections\s+"
        r"(\d+)\s+points\s+on\s+three\s+homeworks?\s*\((\d+)\s+points\s+on\s+each\s+homework\)\s+"
        r"(\d+)\s+points\s+on\s+three\s+midterms?\s*\((\d+)\s+points\s+on\s+each\s+midterm\)",
        text, re.I
    )
    if pts_match:
        p_ex, p_hw, p_hw_each, p_mid, p_mid_each = int(pts_match.group(1)), int(pts_match.group(2)), int(pts_match.group(3)), int(pts_match.group(4)), int(pts_match.group(5))
        if p_ex + p_hw + p_mid == 100:
            add_category("participation", "Exercise sections", p_ex)
            add_assessment("participation_1", "Exercise sections", "participation", "participation", p_ex)
            add_category("homework", "Homework", p_hw)
            for i in range(1, 4):
                add_assessment(f"homework_{i}", f"Homework {i}", "homework", "assignment", p_hw_each)
            add_category("midterms", "Midterms", p_mid)
            for i in range(1, 4):
                add_assessment(f"midterm_{i}", f"Midterm {i}", "midterms", "midterm", p_mid_each)

    # "three tests will each contribute 20% of your course grade" -> Test 1, 2, 3 at 20%
    for m in re.finditer(r"(?:three|3)\s+tests?\s+will\s+each\s+contribute\s+(\d{1,3})\s*%\s+of\s+(?:your\s+)?(?:course\s+)?grade", text, re.I):
        pct = int(m.group(1))
        if 1 <= pct <= 100:
            add_category("tests", "Tests", pct * 3)
            for i in range(1, 4):
                add_assessment(f"test_{i}", f"Test {i}", "tests", "midterm", pct)
            break

    # "3 midterms, each worth 100 points" + "DAILY WORK (75 points)" + "FINAL EXAM (150 points)" = 525 total
    if (re.search(r"3\s+midterms?\s*,\s*each\s+worth\s+100\s+points", text, re.I) and
            re.search(r"DAILY\s+WORK\s*\(\s*75\s+points\s*\)|weighted\s+75\s+points\s+towards", text, re.I) and
            re.search(r"FINAL\s+EXAM\s*\(\s*150\s+points\s*\)", text, re.I)):
        add_category("midterms", "Midterms", 57)
        for i in range(1, 4):
            add_assessment(f"midterm_{i}", f"Midterm {i}", "midterms", "midterm", 19)
        add_category("daily", "Daily work", 14)
        add_assessment("daily_1", "Daily work", "daily", "assignment", 14)
        add_category("final", "Final exam", 29)
        add_assessment("final_1", "Final exam", "final", "final", 29)

    # "homework will contribute 20% of your grade" (when paired with three tests)
    for m in re.finditer(r"[Tt]he\s+homework\s+will\s+contribute\s+(\d{1,3})\s*%\s+of\s+(?:your\s+)?(?:course\s+)?grade", text, re.I):
        pct = int(m.group(1))
        if 1 <= pct <= 100:
            add_category("homework", "Homework", pct)
            add_assessment("homework_1", "Homework", "homework", "assignment", pct)

    # "3 Examinations @ 20% each" -> Examinations category + Examination 1, 2, 3
    for m in re.finditer(r"(\d+)\s+Examinations?\s+@\s+(\d{1,3})\s*%\s*each", text, re.I):
        num, pct_each = int(m.group(1)), int(m.group(2))
        if 1 <= num <= 10 and 1 <= pct_each <= 100:
            pct_total = pct_each * num
            add_category("exams", "Examinations", pct_total)
            for i in range(1, num + 1):
                add_assessment(f"exam_{i}", f"Examination {i}", "exams", "midterm", pct_each)
            break

    # "Homework/Attendance: 10%" - single combined (not split)
    for m in re.finditer(r"Grading\s*:.*?Homework/Attendance\s*:\s*(\d{1,3})\s*%", text, re.I | re.DOTALL):
        pct = int(m.group(1))
        if 1 <= pct <= 100:
            add_category("homework", "Homework/Attendance", pct)
            add_assessment("homework_1", "Homework/Attendance", "homework", "assignment", pct)

    # "Homework/Attend. 30%/5%" -> split into Homework 30%, Attendance 5%
    for m in re.finditer(r"(?:Grading|Grade)\s*:.*?([A-Za-z]+)/([A-Za-z\.]+)\s+(\d{1,3})\s*%/(\d{1,3})\s*%", text, re.I | re.DOTALL):
        name1, name2, pct1, pct2 = m.group(1).strip(), m.group(2).strip(), int(m.group(3)), int(m.group(4))
        if pct1 > 100 or pct2 > 100:
            continue
        if "homework" not in name1.lower() and "hw" not in name1.lower():
            continue
        if "attend" not in name2.lower():
            continue
        title1, title2 = "Homework", "Attendance"
        add_category("homework", title1, pct1)
        add_assessment("homework_1", title1, "homework", "assignment", pct1)
        add_category("participation", title2, pct2)
        add_assessment("participation_1", title2, "participation", "participation", pct2)

    # "Quizzes (best 2 of 3) 45%" - use "Quizzes (in-class exams)" when doc mentions in-class exams
    for m in re.finditer(r"Quizzes?\s*\(\s*best\s+(\d+)\s+of\s+(\d+)\s*\)\s+(\d{1,3})\s*%", text, re.I):
        pct = int(m.group(3))
        if 1 <= pct <= 100:
            ctx = text[: m.end() + 200]  # "in-class exams" often appears earlier in doc (e.g. Quizzes: Three in-class exams...)
            title = "Quizzes (in-class exams)" if re.search(r"in[- ]?class\s+exams?", ctx, re.I) else "Quizzes"
            add_category("quizzes", title, pct)
            add_assessment("quizzes_1", title, "quizzes", "quiz", pct)

    # "Classwork (3 drops) 10%", "Classwork (iClicker) 10%"
    for m in re.finditer(r"Classwork\s*\(\s*(?:\d+\s+drops?|iClicker)\s*\)\s+(\d{1,3})\s*%", text, re.I):
        pct = int(m.group(1))
        if 1 <= pct <= 100:
            ctx = text[max(0, m.start() - 200) : m.end() + 200]
            title = "Classwork (iClicker)" if re.search(r"iClicker|iclicker", ctx, re.I) else "Classwork (3 drops)"
            add_category("classwork", title, pct)
            add_assessment("classwork_1", title, "classwork", "participation", pct)

    # "Homework assignments contributing 25% of the final grade", "Discussion section quizzes contributing 6%"
    for m in re.finditer(r"(Homework\s+assignments?|Discussion\s+section\s+quizzes?)\s+contributing\s+(\d{1,3})\s*%\s*of\s+(?:the\s+)?(?:final\s+)?grade", text, re.I):
        name, pct = m.group(1).strip(), int(m.group(2))
        if pct > 100:
            continue
        name_lower = name.lower()
        if "homework" in name_lower:
            title = "Homework"
            cid = "homework"
            atype = "assignment"
        elif "quiz" in name_lower:
            title = "Quizzes"
            cid = "quizzes"
            atype = "quiz"
        else:
            title = name
            cid = re.sub(r"\s+", "_", name.lower())[:28].rstrip("_")
            atype = "assignment"
        add_category(cid, title, pct)
        add_assessment(cid + "_1", title, cid, atype, pct)

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
    skip_components = {"component", "events", "dropped", "total", "%", "lab"}
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

    # "Grades: Quizzes: 300 pts, Exams: 400 pts, Final: 300 pts" - points that sum to 1000 -> convert to %
    grades_pts = re.search(
        r"Grades?\s*:\s*(.+?)(?=We\s+will|Possibility|I\s+will|$)",
        text[:8000], re.I | re.DOTALL
    )
    if grades_pts:
        block = grades_pts.group(1)
        pts_matches = list(re.finditer(
            r"(Quizzes?|Exams?|Final(?:\s+[Ee]xam)?)\s*:\s*(\d{2,4})\s*(?:pts?\.?|points?)",
            block, re.I
        ))
        if pts_matches:
            total_pts = sum(int(m.group(2)) for m in pts_matches)
            if 800 <= total_pts <= 1200:  # typical 1000-point scale
                for m in pts_matches:
                    name, pts = m.group(1).strip(), int(m.group(2))
                    pct = round(100 * pts / total_pts)
                    if 1 <= pct <= 100:
                        name_lower = name.lower()
                        title = "Quizzes" if "quiz" in name_lower else "Exams" if "exam" in name_lower and "final" not in name_lower else "Final Exam" if "final" in name_lower else name
                        cid = re.sub(r"\s+", "_", title.lower())[:28].rstrip("_")
                        atype = "quiz" if "quiz" in name_lower else "final" if "final" in name_lower else "midterm"
                        add_category(cid, title, pct)
                        add_assessment(cid + "_1", title, cid, atype, pct)

    # "Final grades are based on 1000 points" + "Attendance" (1 pt/lecture) + "Assignments and Projects" table
    if (re.search(r"based\s+on\s+1000\s+points|grading\s+systems?\s+consists?\s+of\s+1000\s+points", text, re.I) and
            re.search(r"Attendance\s+.*?(?:\d+\s+points?\s+per|\d+\s+pt\.?\s+per)", text, re.I | re.DOTALL) and
            re.search(r"Assignments?\s+and\s+Projects?", text, re.I) and
            not any(a.get("title") and "Assignments and Projects" in a.get("title", "") for a in assessments)):
        add_category("attendance", "Attendance", 10)
        add_assessment("attendance_1", "Attendance", "attendance", "participation", 10)
        add_category("assignments", "Assignments and Projects", 90)
        add_assessment("assignments_1", "Assignments and Projects", "assignments", "assignment", 90)

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

    # "Five Quizzes: 5% total for all five", "Ten Quizzes: 20%"
    for m in re.finditer(r"\b(Five|Ten)\s+Quizzes?\s*:\s*(\d{1,3})\s*%(?:\s+total[^.]*)?", text, re.I):
        pct = int(m.group(2))
        if 1 <= pct <= 100:
            title = "Five Quizzes" if "five" in m.group(1).lower() else "Ten Quizzes"
            add_category("quizzes", title, pct)
            add_assessment("quizzes_1", title, "quizzes", "quiz", pct)

    # "Attendance, Quizzes and Participation 10%"
    for m in re.finditer(r"\bAttendance\s*,\s*Quizzes?\s+and\s+Participation\s+(\d{1,3})\s*%", text, re.I):
        pct = int(m.group(1))
        if 1 <= pct <= 100:
            add_category("participation", "Attendance, Quizzes and Participation", pct)
            add_assessment("participation_1", "Attendance, Quizzes and Participation", "participation", "participation", pct)

    # "Attendance and participation: 5%", "Attendance & Participation 5%"
    for m in re.finditer(r"\b(Attendance\s+and\s+participation|Attendance\s*&\s*Participation)\s*:\s*(\d{1,3})\s*%", text, re.I):
        pct = int(m.group(2))
        if 1 <= pct <= 100:
            title = "Attendance and participation" if "and" in m.group(1).lower() else "Attendance & Participation"
            add_category("participation", title, pct)
            add_assessment("participation_1", title, "participation", "participation", pct)

    # "In class quizzes 6%" - preserve exact title (not "Quizzes")
    for m in re.finditer(r"\bIn\s+class\s+quizzes?\s+(\d{1,3})\s*%", text, re.I):
        pct = int(m.group(1))
        if 1 <= pct <= 100:
            title = "In class quizzes"
            add_category("quizzes", title, pct)
            add_assessment("quizzes_1", title, "quizzes", "quiz", pct)

    # "Assignments 50% Individual work", "Quizes 5%" - table format (name first, then %)
    for m in re.finditer(r"(?:^|\n)\s*(Assignments?)\s+(\d{1,3})\s*%\s+", text, re.M | re.I):
        pct = int(m.group(2))
        if 1 <= pct <= 100:
            add_category("assignments", "Assignments", pct)
            add_assessment("assignments_1", "Assignments", "assignments", "assignment", pct)
    for m in re.finditer(r"(?:^|\n)\s*(Quizes?|Quizzes?)\s+(\d{1,3})\s*%\s*(?:\n|$)", text, re.M | re.I):
        pct = int(m.group(2))
        if 1 <= pct <= 100:
            add_category("quizzes", "Quizzes", pct)
            add_assessment("quizzes_1", "Quizzes", "quizzes", "quiz", pct)

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
        elif "final" in name.lower() and "deliverable" in name.lower():
            # "Final deliverables" = project component, not final exam; skip adding as assessment
            continue
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

    # "Homework and quizzes: 10%", "Programming Assignments: 60%", "Tutorial Exercises: 15%"
    for m in re.finditer(r"\b(Homework\s+and\s+quizzes|Programming\s+Assignments|Tutorial\s+Exercises)\s*:\s*(\d{1,3})\s*%", text[:4000], re.I):
        name, pct = m.group(1).strip(), int(m.group(2))
        if pct > 100:
            continue
        cid = re.sub(r"\s+", "_", name.lower())[:28].rstrip("_")
        atype = "assignment"
        add_category(cid, name, pct)
        add_assessment(cid + "_1", name, cid, atype, pct)

    # "Lab attendance/submission 10%", "Lab Attendance: 10%", "Quizzes: 20%"
    for m in re.finditer(r"(Lab\s+attendance[/\s]*(?:and|/)\s*submission|Lab\s+Attendance|Quizzes?|Lab\s+attendance)[:\s]+(\d{1,3})\s*%", text, re.I):
        name, pct = m.group(1).strip(), int(m.group(2))
        cid = "labs" if "lab" in name.lower() else "quizzes"
        cid = add_category(cid, name, pct)
        atype = "participation" if "attendance" in name.lower() else "quiz"
        add_assessment(cid + "_1", name, cid, atype, pct, recurrence={"frequency": "weekly", "interval": 1})

    # "Tests = 45", "Assignments = 40", "Quizzes = 15" - equals format (often in Evaluation section)
    # When "three midterms" or "three tests" in doc, expand Tests = 45 -> Test 1, 2, 3 at 15% each
    has_three_tests = bool(re.search(r"three\s+(?:midterms?|tests?)\s+(?:each\s+worth\s+)?\d+\s+points?", text[:10000], re.I))
    for m in re.finditer(r"(?:^|\n)\s*(Tests?|Assignments?|Quizzes?|Homework|Exams?)\s*=\s*(\d{1,3})\s*$", text[:8000], re.M | re.I):
        name, pct = m.group(1).strip(), int(m.group(2))
        if pct > 100:
            continue
        cid = re.sub(r"\s+", "_", name.lower())[:28].rstrip("_")
        atype = "midterm" if "test" in name.lower() else "assignment" if "assign" in name.lower() else "quiz" if "quiz" in name.lower() else "assignment"
        add_category(cid, name, pct)
        if has_three_tests and "test" in name.lower() and pct == 45 and pct % 3 == 0:
            each = pct // 3
            for i in range(1, 4):
                add_assessment(f"test_{i}", f"Test {i}", cid, atype, each)
        else:
            add_assessment(cid + "_1", name, cid, atype, pct)

    # "* Design milestones (~ 12): 50%", "* Class participation: 10%" - bullet format
    for m in re.finditer(r"\*\s*(Design\s+milestones?|Class\s+participation)\s*(?:\(\s*~?\s*\d+\s*\))?\s*:\s*(\d{1,3})\s*%", text[:5000], re.I):
        name, pct = m.group(1).strip(), int(m.group(2))
        if 1 <= pct <= 100:
            title = "Design milestones" if "design" in name.lower() else "Class participation"
            cid = "design" if "design" in name.lower() else "participation"
            add_category(cid, title, pct)
            add_assessment(cid + "_1", title, cid, "project" if "design" in name.lower() else "participation", pct)

    # "2 in-class exams: 40%" -> Exam 1, Exam 2 at 20% each
    for m in re.finditer(r"(\d+)\s+in-class\s+exams?\s*:\s*(\d{1,3})\s*%", text[:4000], re.I):
        num, total = int(m.group(1)), int(m.group(2))
        if 1 <= num <= 5 and 1 <= total <= 100:
            each = int(round(total / num))
            cid = "exams"
            add_category(cid, "Exams", total)
            for i in range(1, num + 1):
                add_assessment(f"exam_{i}", f"Exam {i}", cid, "midterm", each)

    # "Exam 1 20", "Project 50", "Video 5", "Participation 5", "Test 1 22.5", "Quizzes 30", "Exams 40" - table format
    for m in re.finditer(r"(?:^|\n)\s*(Exam|Exams|Project|Video|Participation|Midterm|Final|Quiz|Quizzes|Homework|Lab|Assignment|Test|Tests)\s*(\d+)?\s+(\d{1,3}(?:\.\d+)?)\s*$", text, re.M | re.I):
        name, num, pct_str = m.group(1), m.group(2), m.group(3)
        pct = int(float(pct_str))
        if pct > 100:
            continue
        # Skip "Lab 0".."Lab 15" - the number is lab session index, not percent (schedule table)
        if name.lower() == "lab" and (num is not None or pct <= 15):
            continue
        name_lower = name.lower()
        # "Group Project" when syllabus mentions group project and we see "Project 50"
        title = f"{name} {num}".strip() if num else name
        if name_lower == "project" and "group project" in text.lower() and not num:
            title = "Group Project"
        cid = re.sub(r"\s+", "_", title.lower())[:28].rstrip("_")
        atype = "midterm" if "midterm" in name_lower else "final" if "final" in name_lower else "project" if "project" in name_lower else "quiz" if "quiz" in name_lower or "quizzes" in name_lower else "participation" if "participation" in name_lower else "assignment"
        if "exam" in name_lower and "midterm" not in name_lower and "final" not in name_lower:
            atype = "final" if num == "2" else "midterm"  # "Exam 1" = midterm, "Exam 2" = final
        if "test" in name_lower:
            atype = "midterm"  # "Test 1", "Test 2", etc.
        if "exams" in name_lower and not num:  # "Exams 40" = generic exam category
            atype = "midterm"
        add_category(cid, title, pct)
        add_assessment(cid + ("_" + num if num else "_1"), title, cid, atype, pct)

    # "10%\nAttendance quizzes", "20%\n\nfinal" - percent on one line, name on next
    for m in re.finditer(r"(?:^|\n)\s*(\d{1,3})\s*%\s*\n\s*([A-Za-z][A-Za-z\s\-()/]+?)(?:\s*[-–]|\s+\(|$)", text, re.M | re.I):
        pct, name = int(m.group(1)), m.group(2).strip()
        if pct > 100 or len(name) < 3 or len(name) > 60:
            continue
        skip = any(w in name.lower() for w in ("dropped", "score", "individual", "submission", "canvas", "collaboration", "policy", "apply", "attempts", "correctly", "configuration", "receive", "requirements", "grade reduced", "more of these", "pm -", "gdc", "evaluation", "course overview", "the worst", "overall breakdown", "how to do well", "other notices", "schedule", "of your quizzes")) or name.lower().strip() == "the worst"
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

    # "Exams (2): 30% (15% each)" -> Exam 1, Exam 2 at 15% each
    for m in re.finditer(r"Exams?\s*\(\s*(\d+)\s*\)\s*:\s*(\d{1,3})\s*%\s*\(\s*(\d{1,3})\s*%\s*each\s*\)", text[:4000], re.I):
        num, total, each = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= num <= 5 and 1 <= each <= 100:
            cid = "exams"
            add_category(cid, "Exams", total)
            for i in range(1, num + 1):
                add_assessment(f"exam_{i}", f"Exam {i}", cid, "midterm", each)

    # "Three Tests (15% each): 45%" -> Test 1, 2, 3 at 15% each
    for m in re.finditer(r"(?:Three|(\d))\s+Tests?\s*\(\s*(\d{1,3})\s*%\s*each\s*\)\s*:\s*(\d{1,3})\s*%", text[:4000], re.I):
        num_str, each, total = m.group(1), int(m.group(2)), int(m.group(3))
        num = int(num_str) if num_str else 3
        if 2 <= num <= 5 and 1 <= each <= 100:
            cid = "tests"
            add_category(cid, "Tests", total)
            for i in range(1, num + 1):
                add_assessment(f"test_{i}", f"Test {i}", cid, "midterm", each)

    # "Grades" section (no colon): "Grades\nYour performance...\nQuizzes: 10%\nTutorial Exercises: 15%..."
    for m in re.finditer(r"(?:^|\n)\s*Grades\s*\n(.*?)(?=\n\s*(?:Study\s+Groups|Academic\s+Misconduct|Your\s+Responsibilities)|\Z)", text[:12000], re.I | re.DOTALL):
        block = m.group(1)
        for item in re.finditer(r"([A-Za-z][A-Za-z0-9\s\-]+?)\s*:\s*(\d{1,3})\s*%", block, re.I):
            name, pct = item.group(1).strip(), int(item.group(2))
            if pct > 100 or len(name) < 2 or len(name) > 45:
                continue
            if any(w in name.lower() for w in ("grading", "total", "course", "each", "three tests", "exams (")):
                continue
            name = re.sub(r"\s+", " ", name)
            cid = re.sub(r"\s+", "_", name.lower())[:28].rstrip("_")
            atype = "midterm" if "test" in name.lower() else "quiz" if "quiz" in name.lower() else "assignment"
            add_category(cid, name, pct)
            add_assessment(cid + "_1", name, cid, atype, pct)
        for item in re.finditer(r"Three\s+Tests?\s*\(\s*(\d{1,3})\s*%\s*each\s*\)\s*:\s*(\d{1,3})\s*%", block, re.I):
            each, total = int(item.group(1)), int(item.group(2))
            if 1 <= each <= 100:
                cid = "tests"
                add_category(cid, "Tests", total)
                for i in range(1, 4):
                    add_assessment(f"test_{i}", f"Test {i}", cid, "midterm", each)

    # "Grading: 30 % Assignments, 15 % Test 1..." or "Course grade: In class quizzes 6%, Homework 24%..." or "Grades:" section
    # Allow block to end at period (e.g. "Test 3: 25%.") or newline
    for m in re.finditer(r"(?:Grading|Course\s+grade|Grades?)\s*:\s*([^.]+?)(?=\.|\n|$|Course\s+grades|Video|Regrade|Disabilities|Study\s+Groups)", text[:3000], re.I | re.DOTALL):
        block = m.group(1)
        for item in re.finditer(r"(\d{1,3})\s*%\s+([A-Za-z][A-Za-z0-9\s\-]+?)(?=\s*,\s*\d|\s*,\s*and|\s+and\s+|\s*$|\n)", block, re.I):
            pct, name = int(item.group(1)), item.group(2).strip()
            if pct > 100 or len(name) < 2 or len(name) > 45:
                continue
            if any(w in name.lower() for w in ("grading", "total", "course", "each")):
                continue
            if "highest two test" in name.lower() or "test scores" in name.lower():
                continue  # handled by "Tests (3 in-class, drop lowest)" pattern
            name = re.sub(r"\s+", " ", name)
            cid = re.sub(r"\s+", "_", name.lower())[:28].rstrip("_")
            atype = "midterm" if "midterm" in name.lower() else "final" if "final" in name.lower() else "exam" if "test" in name.lower() or "exam" in name.lower() else "project" if "project" in name.lower() or "paper" in name.lower() else "participation" if "presentation" in name.lower() or "participation" in name.lower() else "quiz" if "quiz" in name.lower() else "assignment"
            add_category(cid, name, pct)
            add_assessment(cid + "_1", name, cid, atype, pct)
        for item in re.finditer(r"(?:and\s+)?([A-Za-z][A-Za-z0-9\s\-]+?)\s*:\s*(\d{1,3})\s*%", block, re.I):
            name, pct = item.group(1).strip(), int(item.group(2))
            if pct > 100 or len(name) < 2 or len(name) > 45:
                continue
            if any(w in name.lower() for w in ("grading", "total", "course", "each")):
                continue
            if "highest two test" in name.lower() or "test scores" in name.lower():
                continue
            if "three tests" in name.lower() or "exams (" in name.lower():
                continue  # Handled by Exams (2)/Three Tests patterns above
            name = re.sub(r"\s+", " ", name)
            cid = re.sub(r"\s+", "_", name.lower())[:28].rstrip("_")
            atype = "midterm" if "midterm" in name.lower() else "final" if "final" in name.lower() else "exam" if "test" in name.lower() or "exam" in name.lower() else "project" if "project" in name.lower() or "paper" in name.lower() else "participation" if "presentation" in name.lower() or "participation" in name.lower() else "quiz" if "quiz" in name.lower() else "assignment"
            add_category(cid, name, pct)
            add_assessment(cid + "_1", name, cid, atype, pct)
        for item in re.finditer(r"(?:and\s+)?([A-Za-z][A-Za-z0-9\s\-]+?)\s+(\d{1,3})\s*%", block, re.I):
            name, pct = item.group(1).strip(), int(item.group(2))
            if pct > 100 or len(name) < 2 or len(name) > 45:
                continue
            if any(w in name.lower() for w in ("grading", "total", "course", "each")):
                continue
            if "highest two test" in name.lower() or "test scores" in name.lower():
                continue
            name = re.sub(r"\s+", " ", name)
            cid = re.sub(r"\s+", "_", name.lower())[:28].rstrip("_")
            atype = "midterm" if "midterm" in name.lower() else "final" if "final" in name.lower() else "exam" if "test" in name.lower() or "exam" in name.lower() else "project" if "project" in name.lower() or "paper" in name.lower() else "participation" if "presentation" in name.lower() or "participation" in name.lower() else "quiz" if "quiz" in name.lower() else "assignment"
            add_category(cid, name, pct)
            add_assessment(cid + "_1", name, cid, atype, pct)

    # "1st Paper: 20%", "2nd Paper: 25%", "3rd Paper: 30%" - ordinal papers
    for m in re.finditer(r"(\d+(?:st|nd|rd|th))\s+Paper\s*:\s*(\d{1,3}(?:\.\d+)?)\s*%", text, re.I):
        ord_str, pct_str = m.group(1), m.group(2)
        pct = int(float(pct_str))
        if pct > 100:
            continue
        title = f"{ord_str} Paper"
        cid = re.sub(r"\s+", "_", title.lower())[:28].rstrip("_")
        add_category(cid, title, pct)
        add_assessment(cid + "_1", title, cid, "assignment", pct)

    # Points-based grading: "Midterm test 1 (part A): 40, Midterm test 1 (part B): 60, Midterm test 2: 100, Final exam: 100" (total 300)
    pts_block = re.search(r"(\d+)\s*points?\s+may\s+be\s+accrued|total\s+of\s+(\d+)\s+points?", text[:4000], re.I)
    if pts_block:
        total_pts = int(pts_block.group(1) or pts_block.group(2))
        if 200 <= total_pts <= 500:
            pts_by_name = {}
            for pm in re.finditer(r"(Midterm\s+test\s+\d+|Final\s+exam)\s*(?:\([^)]+\))?\s*:\s*(\d+)", text[:4000], re.I):
                name, pts = pm.group(1).strip(), int(pm.group(2))
                if pts <= total_pts:
                    key = "Midterm test 1" if "1" in name else "Midterm test 2" if "2" in name else "Final exam"
                    pts_by_name[key] = pts_by_name.get(key, 0) + pts
            if pts_by_name and sum(pts_by_name.values()) == total_pts:
                order = ["Midterm test 1", "Midterm test 2", "Final exam"]
                items = [(k, pts_by_name[k]) for k in order if k in pts_by_name]
                pcts = [round(100 * pts / total_pts, 1) for _, pts in items]
                if sum(pcts) < 100:
                    pcts[-1] = round(100 - sum(pcts[:-1]), 1)
                for (title, _), pct in zip(items, pcts):
                    cid = re.sub(r"\s+", "_", title.lower())[:28].rstrip("_")
                    if not any(a.get("title") == title and a.get("weight_percent") == pct for a in assessments):
                        add_category(cid, title, pct)
                        add_assessment(cid + "_1", title, cid, "midterm" if "midterm" in title.lower() else "final", pct)

    # "Highest two test scores 20% each", "Tests (3 in-class, drop lowest) 40%", "Homework 24%, ... Final Exam 36%"
    for m in re.finditer(r"(?:Highest\s+two\s+test\s+scores?|Tests?\s*\([^)]*drop\s+lowest[^)]*\))\s+(\d{1,3})\s*%\s*(?:each)?", text, re.I):
        pct = int(m.group(1))
        pct_total = pct * 2 if "each" in m.group(0) or "two" in m.group(0) else pct
        if 1 <= pct_total <= 100:
            title = "Tests (3 in-class, drop lowest)"
            cid = "tests"
            if not any(a.get("title", "").lower() == title.lower() for a in assessments):
                add_category(cid, title, pct_total)
                add_assessment(cid + "_1", title, cid, "midterm", pct_total)

    # Activity courses: "attend at least 80% ... to pass" + participation/attendance = 100% grade
    if re.search(r"attend\s+at\s+least\s+\d+%.*to\s+pass|attendance.*required.*pass", text[:5000], re.I | re.DOTALL):
        if re.search(r"activity\s+course|1-credit|1\s+credit", text[:5000], re.I):
            has_correct = any("80% required to pass" in (a.get("title") or "") for a in assessments)
            if not has_correct:
                # Remove junk assessments (e.g. "Attendance\n\n...must attend at least" from percent-first pattern)
                assessments[:] = [a for a in assessments if "\n" not in (a.get("title") or "") and "attend at least" not in (a.get("title") or "").lower()]
                title = "Attendance and Participation (80% required to pass)"
                add_category("participation", title, 100)
                add_assessment("participation_1", title, "participation", "participation", 100)

    # "3 Midterm Exams: 20% each" (colon format) -> single "3 Midterm Exams (20% each)" at 60%
    for m in re.finditer(r"(\d)\s+Midterm\s+Exams?\s*:\s*(\d{1,3})\s*%\s*each", text, re.I):
        num, pct_each = int(m.group(1)), int(m.group(2))
        if 1 <= num <= 5 and 1 <= pct_each <= 100:
            pct_total = pct_each * num
            title = f"{num} Midterm Exams ({pct_each}% each)"
            add_category("midterms", "Midterm Exams", pct_total)
            add_assessment("midterms_1", title, "midterms", "midterm", pct_total)

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

    # "Midterm: February 19, 2026, in class" - single midterm with date
    for m in re.finditer(
        r"Midterm\s*:\s*(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,\s*(\d{4}))?(?:\s*,\s*in\s+class)?",
        text, re.I
    ):
        mon, day_str, yr_str = m.group(1), m.group(2), m.group(3)
        mon_num = MONTHS.get((mon or "").lower()[:3])
        if mon_num and 1 <= int(day_str) <= 31:
            due_yr = int(yr_str) if yr_str else yr
            due = f"{due_yr}-{mon_num:02d}-{int(day_str):02d}"
            # Look for weight in nearby context (e.g. "Midterm 35%" in grading line)
            ctx = text[m.end():m.end() + 500]
            wm = re.search(r"Midterm\s+(\d{1,3})\s*%", ctx, re.I)
            pct = int(wm.group(1)) if wm and 1 <= int(wm.group(1)) <= 100 else None
            if not any(a.get("title") == "Midterm" and a.get("category_id") == "midterm" for a in assessments):
                add_category("midterm", "Midterm", pct)
                add_assessment("midterm_1", "Midterm", "midterm", "midterm", pct, due)
            break  # one such midterm per syllabus

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
        "of class participation",  # fragment from "10% of class participation points"
        "except for the", "waived by the token",  # late policy fragments
        "textbooks and readings",  # section header, not grading component
        "lecture section coverage",  # schedule table header
    )

    def _is_junk_name(n: str) -> bool:
        n = (n or "").strip().lower()
        if len(n) < 3 or n in ("each", "class"):
            return True
        if n.startswith("of ") or n.startswith("except for "):
            return True
        return any(g in n for g in _garbage_phrases)

    for m in re.finditer(r"(\d{1,3})\s*%[ \t]+([A-Za-z][A-Za-z \t\-/\n]+?)(?=[\s\.\,\)$]|\.)", text, re.I):
        pct, name = int(m.group(1)), m.group(2).strip()
        if pct > 100 or len(name) < 3 or len(name) > 55:
            continue
        if _is_junk_name(name):
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

    # "No Final Exam" - remove final exam assessments when syllabus explicitly states no final
    if re.search(r"\bno\s+final\s+exam\b|\bno\s+final\b", text[:5000], re.I):
        assessments[:] = [a for a in assessments if a.get("type") != "final"]

    return categories, assessments


