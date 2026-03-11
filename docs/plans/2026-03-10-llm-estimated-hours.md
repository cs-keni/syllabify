# LLM Estimated Hours for Assignments

> **Goal:** Use the LLM (GPT-4o-mini) to estimate study hours per assignment during syllabus parsing, instead of type-based defaults. The scheduling engine already uses these hours as the target allocation.

**Context:** Currently, the LLM parser extracts assessments with `type` (assignment, midterm, quiz, etc.) but not hours. Hours are assigned by `_hours_from_assessment_type()` — fixed defaults (midterm=2, quiz=1, project=4, assignment=3). The LLM sees the full syllabus and can infer better estimates from title, weight, and workload language.

---

## Phases

### Phase 1: Add `estimated_hours` to LLM schema

**Files:** `backend/app/services/llm_parser.py`

**Tasks:**
1. Add `estimated_hours` to the assessment schema in `SYLLABUS_JSON_SCHEMA`:
   - Type: `number` or `integer`, nullable
   - Range: 1–20 (hours **per assignment**, e.g. "Homework 3" ~3h, "Final Project" ~15h)
2. Update `SYSTEM_PROMPT` to instruct the LLM:
   - For each assessment, estimate `estimated_hours` (1–20): total hours a typical student might spend on that single assignment
   - Use syllabus hints (e.g. "4–6 hours per week", "projects take 10–15 hours"), type, weight, and title
   - Use `null` if completely unclear
3. Ensure `_validate_and_normalize` passes through `estimated_hours` on each assessment

**Acceptance:** LLM response includes `estimated_hours` per assessment when it can infer one.

---

### Phase 2: Use estimated hours in parsing service

**Files:** `backend/app/services/parsing_service.py`

**Tasks:**
1. In `_map_llm_to_assignments` (or the LLM output mapping path), when building each assignment:
   - Read `estimated_hours` from the LLM assessment
   - If valid (1 ≤ value ≤ 20), use it for `hours`
   - Otherwise fall back to `_hours_from_assessment_type(atype)`
2. Ensure the heuristic/syllabus_parser path is unchanged (still uses type-based defaults)

**Acceptance:** Parsed assignments from LLM path use LLM-estimated hours when available; type fallback otherwise.

---

### Phase 3: Testing

**Tasks:**
1. Add or extend unit tests for the LLM mapping path:
   - When `estimated_hours` is present and valid → use it
   - When `estimated_hours` is null or out of range → use type default
2. Manual smoke test: Parse a syllabus with `USE_LLM_PARSER=true`, verify hours look reasonable in ParsedDataReview
3. End-to-end: Save course, generate study times, confirm blocks align with estimated hours

**Acceptance:** Tests pass; manual parse produces sensible hour estimates.

---

### Phase 4: AI estimate for manual add

**Files:** `backend/app/services/llm_parser.py`, `backend/app/api/assignments.py`, `frontend/src/api/client.js`, `frontend/src/pages/Course.jsx`

**Tasks:**
1. Add `estimate_assignment_hours(name, type)` in llm_parser.py — simple LLM call returning 1–20
2. Add POST `/api/assignments/estimate-hours` — body `{ name, type }`, returns `{ hours }`
3. Add `estimateAssignmentHours(token, name, type)` to API client
4. Add "Estimate with AI" button next to Hours input in AddAssignmentForm — calls API, populates hours

**Acceptance:** User can click "Estimate with AI" when adding an assignment manually; hours field updates with LLM estimate.

---

## Checklist

- [x] Phase 1: LLM schema + prompt
- [x] Phase 2: Parsing service integration
- [x] Phase 3: Tests + smoke test
- [x] Phase 4: AI estimate for manual add

---

### Phase 5: Seamless upload → schedule flow (2026-03-10)

**Goal:** Upload syllabus → Confirm → See schedule with minimal/no manual edits.

**Changes:**
- **Hours cap 50** — Term-long projects (e.g. "Project work 50") now supported
- **Workload tables** — LLM uses "Credit Hours and Student Workload" sections; maps "Project work 50" to Group Project
- **Date inference** — When due dates not stated, LLM infers from term (midterm ~midpoint, final ~end)
- **study_hours_per_week** — Parsed from syllabus, pre-fills course setting
- **Auto-generate** — After confirm, study times are generated automatically
- **View schedule** — Primary CTA on confirm step; user goes straight to schedule

---

## Notes

- **1–50 hours** = per assignment (e.g. "Homework 3" ~3h, "Group Project" ~50h for term-long), not per week.
- The scheduling engine uses `work_load = hours * 4` (15-min blocks). No changes needed there.
- Heuristic parser path stays as-is; only LLM path gets estimated hours.
- User can always override hours in ParsedDataReview or AddAssignmentForm before saving.
