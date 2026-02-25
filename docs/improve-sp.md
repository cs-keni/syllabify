# Syllabus Parser (SP) Improvement Guide

**Purpose:** This is the master instructions file for incrementally improving the syllabus parser. Work on the parser is ongoing and iterative—not one-off fixes. Read this before making parser changes.

---

## 1. Context and Scope

### What This Is
- **Syllabus parser (SP):** Rule-based extractor that turns syllabus text (from PDFs, DOCX, TXT) into structured JSON.
- **Incremental work:** We improve the parser over time by adding patterns, fixing edge cases, and refactoring. Each session may fix a handful of courses; that's expected.
- **Ground truth:** We have 177+ fixture syllabi with `parsed.json` (expected output). Tests compare parser output to ground truth. Many tests currently fail because the parser doesn't yet extract what we want—that's the improvement target.

### Goal
- **Ideal:** A parser that reliably reads any syllabus (including future ones).
- **Realistic:** Every syllabus is different. Layouts, formats, and noise vary widely. Aim for:
  - **Breadth:** Handle as many syllabus formats as possible (tables, prose, bullet lists, mixed).
  - **Minimum bar:** Extract enough for the **scheduling engine** to work: course code/title, meeting times, assessments (with due dates and weights), term, timezone, late policy when present.

### Code Quality
- **Refactoring and modularization are encouraged.** If the code becomes hard to maintain or extend, refactor. Split large modules, extract patterns to constants, add small helper functions. The goal is maintainable, scalable code.

---

## 2. Parser Architecture

**Location:** `backend/app/services/syllabus_parser/`

| Module | Responsibility |
|--------|-----------------|
| `__init__.py` | Orchestrates parsing; calls all sub-parsers; builds final JSON |
| `course.py` | Course code, title, term, instructors |
| `meeting_times.py` | Class meeting times (day, start, end, location, type) |
| `assessments.py` | Assessment categories and individual assessments (title, type, weight, due date) |
| `late_policy.py` | Late pass / extension policy |
| `constants.py` | Shared constants, patterns |

**Entry point:** `parse_syllabus_text(text, course_id, source_type)` in `__init__.py`.

**Downstream:** Output feeds `parsing_service.py` → API (`POST /api/syllabus/parse`) → user review → DB (Courses, Assignments) → scheduling engine.

---

## 3. What the Scheduling Engine Needs

From `docs/parser-schedule-integration.md` and `docs/SCHEDULING_ENGINE_DATA.md`:

| Data | Why |
|------|-----|
| **meeting_times** | Fixed blocks (lectures, labs); engine doesn't schedule into these |
| **assessments** | Work items with `due_datetime`, `type`, `weight_percent`; engine allocates study blocks before due dates |
| **course.term** | Bounds the schedule (e.g., Fall 2025 → Sept–Dec) |
| **course.timezone** | For datetime handling |
| **assignment_type** | `assignment` \| `midterm` \| `final` \| `quiz` \| `project` \| `participation` — used for workload heuristics (exam → ~2 hrs, project → ~4 hrs, etc.) |
| **weight_percent** | Optional proxy for study time; heavier % → more blocks |
| **late_pass_policy** | Optional; can inform scheduling rules |

If the parser produces these, the scheduling engine can work. Extra fields (instructors, location, grading structure) are nice-to-have but not blocking.

---

## 4. Fixture Structure and Ground Truth

**Paths:**
- `backend/tests/fixtures/syllabus-data/extracted/{course_id}.txt` — Raw text extracted from PDF/DOCX
- `backend/tests/fixtures/syllabus-data/syllabus/{course_id}/parsed.json` — Expected output (ground truth)
- `backend/tests/fixtures/syllabus-data/syllabus/{course_id}/*.pdf` — Original PDF (when present)

**Tests:** `backend/tests/test_syllabus_parser.py` parametrizes over all courses with both `extracted/{id}.txt` and `parsed.json`. For each:
1. Load extracted text
2. Run `parse_syllabus_text(text, course_id, "txt")`
3. Compare result to `parsed.json` on: course_code, course_title, meeting_times, assessments, late_pass_policy
4. Fail if key fields don't match

**Running tests:**
```bash
cd backend
pytest tests/test_syllabus_parser.py -v                    # All 177 ground-truth tests
pytest tests/test_syllabus_parser.py -v -k "CS314"        # Single course
pytest tests/test_parsing_service.py tests/test_syllabus_api.py -v  # Parsing service + API (no ground truth)
```

---

## 5. Common Failure Patterns

From current test failures, the parser often:

1. **Returns folder name instead of course title** — When it can't find a real title, it falls back to `course_id`. Improve `parse_course_title` to avoid picking up prereqs, section IDs, or garbage.

2. **Misses course code suffixes** — e.g., extracts "CS 303" instead of "CS 303E", "PHY 396" instead of "PHY 396K". Check patterns in `course.py` for letter suffixes.

3. **Misses meeting times** — Many syllabi use "TuTh 2-3:30pm" or "MWF 10-10:50" or tables. Add patterns in `meeting_times.py` for:
   - Abbreviated day combos (TuTh, MWF, TTh)
   - Time ranges with/without colons
   - Location in same line or nearby

4. **Misses assessments** — Grading sections use tables, bullet lists, or prose. Common formats:
   - "Exam 1: 25%" or "25% Exam 1"
   - "Homework 20%, Midterms 30%, Final 50%"
   - Table with Assessment | Weight columns
   - "Drop lowest 2 quizzes"
   Add patterns in `assessments.py` and handle multiple formats.

5. **Picks wrong field** — e.g., grabs "or 311H, 314" (prereqs) as course title. Add negative filters, context checks, and `course_title_keywords` to avoid noise.

6. **Misses late policy** — "2 free late days" or "10% per day" — add phrases in `late_policy.py`.

---

## 6. Workflow for Improving the Parser

1. **Pick a failing course** — Run `pytest tests/test_syllabus_parser.py -v -k "COURSE_ID"` to see the failure.
2. **Read the extracted text** — `backend/tests/fixtures/syllabus-data/extracted/COURSE_ID.txt`
3. **Read the ground truth** — `backend/tests/fixtures/syllabus-data/syllabus/COURSE_ID/parsed.json`
4. **Identify the gap** — What is in parsed.json that the parser didn't extract? What pattern is in the text?
5. **Add or adjust a pattern** — In the relevant module (course, meeting_times, assessments, late_policy).
6. **Re-run the test** — Ensure that course passes.
7. **Run broader tests** — `pytest tests/test_syllabus_parser.py -v` to ensure you didn't regress other courses. Fix regressions if needed.
8. **Iterate** — Move to the next failing course or batch similar formats together.

---

## 7. Scripts and Utilities

| Script | Purpose |
|--------|---------|
| `backend/scripts/audit_parsed.py` | Audit all parsed.json for schema issues, empty fields, weight sums |
| `backend/scripts/verify_ground_truth.py` | Check parsed.json vs extracted text (e.g., timezone by institution) |
| `backend/scripts/fix_timezones.py` | Fix timezone in parsed.json based on institution |
| `backend/scripts/process_new_syllabi.py` | Process PDFs from new-syllabus/ → extracted/, syllabus/ (when new-syllabus exists) |
| `backend/tests/validate_parsed_schema.py` | Validate all parsed.json against the schema template |

**Audit report:** `backend/tests/fixtures/syllabus-data/AUDIT_REPORT.md` summarizes fixes and remaining issues.

---

## 8. Output Schema

Parser returns JSON with top-level keys:
- `course` — id, course_code, course_title, term, timezone, instructors, meeting_times, location
- `assessment_categories` — Groups (e.g., "Exams", "Projects")
- `assessments` — List of { id, title, type, weight_percent, due_datetime, category_id, ... }
- `grading_structure` — flat \| bucketed
- `late_pass_policy` — total_allowed, extension_days, etc.
- `schedule` — Usually empty; week-by-week if parsed
- `metadata` — source_type, schema_version

See `backend/tests/fixtures/syllabus-data/syllabus-schema-template.json` for full shape.

---

## 9. Tips for Adding Patterns

1. **Normalize text first** — Unicode hyphens/dashes are normalized in `__init__.py`. Use consistent casing (e.g., `.lower()` for matching when order doesn't matter).

2. **Prefer specific over generic** — A pattern that matches "Exam 1: 25%" is better than one that matches any "X: N%".

3. **Avoid over-matching** — If a pattern grabs prereqs or section numbers, add exclusions or require context (e.g., "must be near 'grading' or 'assessment'").

4. **Test locally** — After a change, run `pytest tests/test_syllabus_parser.py -v` and check pass/fail counts. Aim to increase passes without breaking previously passing courses.

5. **Modularize** — If `assessments.py` or `meeting_times.py` gets large, split into sub-modules (e.g., `assessments_table.py`, `assessments_prose.py`) and import in the main module.

---

## 10. References

- `docs/parser-schedule-integration.md` — Parser ↔ scheduling engine flow
- `docs/SCHEDULING_ENGINE_DATA.md` — DB schema, assignment types, flow
- `backend/tests/fixtures/syllabus-data/AUDIT_REPORT.md` — Recent fixes and remaining issues
- `backend/app/services/parsing_service.py` — Wraps syllabus_parser; maps to API shape; computes parse confidence
