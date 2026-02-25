# Syllabus Parser: Supported Patterns

This document describes the assessment and grading formats the syllabus parser recognizes. Add new patterns in `assessments.py`, `course.py`, or `meeting_times.py` as needed.

---

## Assessment Patterns

### Grading / Course Grade Lines (comma-separated)

- **Format:** `Grading: 30 % Assignments, 15 % Test 1, 15 % Test 2, 20 % Test 3, 15% Term paper, 5% Class presentation`
- **Format:** `Course grade: In class quizzes 6%, Homework 24%, Highest two test scores 18% each, and Final Exam 34%`
- Supports both `N% Name` and `Name N%` order
- Skips "Highest two test scores N% each" (handled by Tests pattern)

### Ordinal Papers

- **Format:** `1st Paper: 20%`, `2nd Paper: 25%`, `3rd Paper: 30%`

### Points-Based Grading (convert to %)

- **Format:** `A total of 300 points may be accrued... Midterm test 1 (part A): 40, Midterm test 1 (part B): 60, Midterm test 2: 100, Final exam: 100`
- Converts points to percent when total is 200–500
- Aggregates parts (e.g., Midterm 1 part A + B)

### Tests with Drop Lowest

- **Format:** `Highest two test scores 20% each`, `Tests (3 in-class, drop lowest) 40%`
- Produces single assessment: "Tests (3 in-class, drop lowest)" at total %

### Activity Courses (100% attendance/participation)

- **Format:** `attend at least 80% ... to pass` + `1-credit` or `activity course`
- Produces: "Attendance and Participation (80% required to pass)" at 100%

### Three Midterms (aggregate)

- **Format:** `Three midterms 20%/ea`, `Three midterms (20% each) 60%`
- Produces single: "Three midterms (20% each)" at 60%

### N Midterm Exams (colon)

- **Format:** `3 Midterm Exams: 20% each`
- Produces: "3 Midterm Exams (20% each)" at 60%

### Table Format

- **Format:** `Exam 1 20`, `Test 1 22.5`, `Quizzes 30` (name, optional number, percent)
- **Format:** `Assignments 50% Individual work`, `Quizes 5%` (name first, then %)
- Supports decimal percentages

### Named Assessment Patterns

- `Five Quizzes: 5% total for all five` → Five Quizzes 5%
- `Ten Quizzes: 20%` → Ten Quizzes 20%
- `Attendance and participation: 5%` → Attendance and participation 5%
- `Attendance, Quizzes and Participation 10%` → Attendance, Quizzes and Participation 10%
- `In class quizzes 6%` → In class quizzes 6% (preserves exact title)
- `3 Examinations @ 20% each` → Examinations category + Examination 1, 2, 3 at 20% each
- `Homework/Attend. 30%/5%` → Homework 30%, Attendance 5% (split when in Grading block)
- `Quizzes (best 2 of 3) 45%` → Quizzes (in-class exams) when doc mentions "in-class exams"
- `Classwork (3 drops) 10%` or `Classwork (iClicker) 10%` → Classwork 10%

### Other Common Patterns

- `Name (N%)` — e.g. "Participation in Discussion Forums (25%)"
- `Name: N%` — e.g. "Participation: 5%", "Quizzes: 20%"
- `N% Name` — percent first, name on same or next line
- `Midterm: February 19, 2026, in class` — single midterm with date
- `No Final Exam` — removes final exam assessments when stated

---

## Course Code Patterns

- **Letter suffix:** Prefers `EE 382N` over `EE 382` when text has `EE 382 N` (space before suffix)
- **Lowercase prefix in number:** `Physics n303L` → `PHY 303L` (strips leading lowercase letter)
- **Folder-derived:** Uses course folder (e.g. `opt3-dist`) when text contains matching code

---

## Meeting Time Patterns

- **Section / Meets:** `Section: Unique #55895, Meets MWF, 2-3 PM, RLM 7.104` or `Meets MWF, 12-1 PM, RLM 7.104`
- **Time / Place:** `Time: TTh 11:00 - 12:30. Place: CAL 100`
- **Season Year:** `Spring 2015 TTH 12:30-2:00 CAL 100`
- **Date/Time/Location (pipe-separated):** `Date/Time/Location: MW / 10:30-11:45 AM / ECJ 1.306`
- **Hours + Location (multi-line):** `Hours: Monday & Wednesday` + next line `5:00 PM to 6:30 PM` + `Location: ECJ 1.214`
- **Information Time:** `Information Time: MW 9:30-11:00am` + `Location: GDC 5.302` (within ~150 chars)
- **Class time (semicolon):** `Class time: MWF 9-10am; Location: CLA 0.130` (supports T R, WF)
- **Hyphenated days:** `M-Tu-W-Th-F 10:00–11:15am – PAI 4.42` (MTWRF)
- **Slash-separated days:** `Monday / Wednesday / Friday, 9:00 am – 10:00 am, WEL 2.304`
- **Location cleanup:** Strips trailing "Lectures", "Instructor", "Office" (e.g. `ECJ 1.306\nInstructor` → `ECJ 1.306`)

---

## Junk Filtering

The parser skips or filters:

- "of class participation", "each", "lecture section coverage"
- Names starting with "of " or "except for "
- "Learning Outcomes", "Missed Exams", "Late Projects Late submissions will incur a"

---

## Adding New Patterns

1. Identify the format in extracted text (`extracted/{course}.txt`)
2. Add a regex in the appropriate module (`assessments.py`, `course.py`, `meeting_times.py`)
3. Run `pytest tests/test_syllabus_parser.py -v -k "course_id"` to verify
4. Update this document
