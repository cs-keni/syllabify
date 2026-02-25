# Hybrid Syllabus Parser: LLM + Heuristics Architecture

## Overview

Modern document automation systems (contract analyzers, invoice parsers, tax form processors) use a **hybrid model**: deterministic extraction + LLM interpretation + validation + human review. Syllabify will follow the same pattern. The goal is **80–90% correct parsing**, easy UI correction, and fast editing workflow—because even perfect parsing won't eliminate human correction.

**Key insight:** The app doesn't need 100% correct parsing. It needs high-quality defaults that the user can quickly fix. Use the `confidence` field to surface uncertain items.

---

## Before You Begin

### What You Need To Do (Your Side)

| Task | Details | When |
|------|---------|------|
| **Choose LLM API** | OpenAI recommended (GPT-4o-mini for cost); alternatively Claude/Anthropic. | Before Phase 2 |
| **Create API key** | See detailed walkthrough below. | Before Phase 2 |
| **Add `OPENAI_API_KEY`** | In Render dashboard: Environment → Add variable → `OPENAI_API_KEY` = your key (mark as Secret). Also add to local `.env` for dev. | Phase 2 start |
| **Ensure billing / credits** | OpenAI requires payment method for API access. GPT-4o-mini is ~$0.01–0.03 per syllabus. | Phase 2 start |
| **Review parse endpoint timeout** | Render default may be 30s. LLM calls can take 3–8s. Extend if needed. | Phase 3 |

---

### OpenAI API Key: Step-by-Step Walkthrough

When you're on the [OpenAI API Keys page](https://platform.openai.com/api-keys) and click **Create new secret key**, you'll see a form. Here’s what to choose:

#### 1. **Ownership: "Me" vs "Service account"**

| Option | Use this when |
|--------|----------------|
| **Me** | You're the developer, solo or small team, dev/testing, or first production deploy. Key is tied to your account. |
| **Service account** | You want a separate identity for CI/CD, production servers, or team automation. Requires more setup. |

**Recommendation:** Choose **Me**. For Syllabify, a personal key is fine. You can create a service account later for production if needed.

---

#### 2. **Name**

Use something descriptive so you can tell keys apart later:

- `syllabify-dev` — for local / dev environment
- `syllabify-production` — for Render (use a separate key for prod if you prefer)

You can create multiple keys (one for local, one for Render). Naming is just for your reference.

---

#### 3. **Project**

- If you have one project: use the default.
- If you have multiple: pick the project you’re using for Syllabify (or create one like “Syllabify”).
- The key will be associated with that project’s usage and billing.

---

#### 4. **Permissions: All, Restricted, or Read only**

| Option | What it does | Use for Syllabify? |
|--------|---------------|-------------------|
| **All** | Full access to all endpoints. Default. | ✅ **Yes** — simplest, works for Chat Completions. |
| **Restricted** | Fine-grained Read/Write per endpoint. You must enable access for each API. | Optional — use if you want to limit scope. Need to enable Chat Completions (and possibly Completions). |
| **Read only** | Read-only for all endpoints. | ❌ No — Chat Completions needs to send requests (POST) and get responses, which is not read-only. |

**Recommendation:** Choose **All** to get started. If you later want to lock it down, use **Restricted** and enable only the Chat Completions API.

---

#### 5. **After creating the key**

- **Copy the key immediately.** OpenAI shows it only once. It looks like `sk-proj-...` or `sk-...`.
- Store it securely:
  - In your local `.env`: `OPENAI_API_KEY=sk-proj-xxxx`
  - In Render: Environment variables → Add → `OPENAI_API_KEY` → paste → mark as **Secret**
- Do **not** commit it to git. Ensure `.env` is in `.gitignore`.

---

#### 6. **Billing**

- Go to [Billing](https://platform.openai.com/account/billing) and add a payment method if you haven’t.
- Set a usage limit if you want (e.g. $5/month) to avoid surprises.
- GPT-4o-mini is low cost (~$0.15/1M input tokens); a few dozen syllabus parses will be under $1.

---

#### 7. **Enable the hybrid parser on Render**

After the hybrid parser code is deployed, add one more env var so the app actually uses it:

| Variable | Value | Where |
|----------|-------|-------|
| `USE_LLM_PARSER` | `true` | Render (syllabify-dev) — enable hybrid on dev first |
| `USE_LLM_PARSER` | `true` or `false` | Render (syllabify prod) — enable when confident |

**GPT-4o-mini:** You don't set the model in the OpenAI dashboard. We specify `model="gpt-4o-mini"` in our code when calling the API. Your API key works with any model; the code chooses which one to use.

**Testing without local .env:** If you only test on the dev Render deployment, you don't need `.env` locally. The API key and `USE_LLM_PARSER` live in Render's environment variables.

**Add `USE_LLM_PARSER` on Render:** After deploying the hybrid parser code, add `USE_LLM_PARSER=true` to your Render environment variables (syllabify-dev first). Without this, the app uses the heuristic parser only. You already have `OPENAI_API_KEY` set.

---

### What We Will Implement (Code Side)

- New extraction module, LLM parser, validation pipeline, feature flag, UI tweaks
- Reuse of existing parser as fallback and for parts of Step 1
- No DB schema change required; no migration from MySQL

### Prerequisites Checklist

- [ ] You have decided on LLM provider (OpenAI default)
- [ ] OpenAI API key created (see walkthrough above: **Me**, **All** permissions, copy key once)
- [ ] Billing / payment method added on OpenAI
- [ ] API key stored in local `.env` as `OPENAI_API_KEY=sk-...` (never commit)
- [ ] Render env vars ready for Phase 2 deploy (`OPENAI_API_KEY` as Secret)

---

## Reuse Strategy: What Stays, What Changes

**We do NOT remove the existing parser.** It becomes the fallback and provides reusable pieces.

### Keep As-Is (Reuse Directly)

| Component | Path | Use |
|-----------|------|-----|
| **document_utils** | `backend/app/utils/document_utils.py` | PDF/DOCX/TXT extraction. We *extend* it (add table extraction), not replace. |
| **date_utils** | `backend/app/utils/date_utils.py` | `parse_due_date()`, date normalization—use in validation. |
| **parsing_service API shape** | `backend/app/services/parsing_service.py` | Output format (`course_name`, `assignments`, `assessments`, `meeting_times`, `confidence`) stays same. Frontend expects it. |
| **syllabus API route** | `backend/app/api/syllabus.py` | `POST /parse` unchanged. We add internal routing (hybrid vs rule). |
| **Syllabus schema** | Same shape as `parsed.json` fixtures | `course`, `assessments`, `assessment_categories`, `meeting_times`, `late_pass_policy`. LLM must output this. |

### Refactor / Extend

| Component | Path | Change |
|-----------|------|--------|
| **document_utils** | `backend/app/utils/document_utils.py` | Add `extract_structured(file)` → returns `{sections, tables, raw_text, metadata}`. Keep `extract_text_from_file()` for backward compat. |
| **parsing_service** | `backend/app/services/parsing_service.py` | Add `parse_text(..., mode="hybrid")` path. When `USE_LLM_PARSER=true`, call hybrid flow; else call existing `_parse_with_syllabus_parser()`. Reuse `compute_parse_confidence()`, `_hours_from_assessment_type()`, `_is_junk_title()` for post-processing. |
| **syllabus.py** | `backend/app/api/syllabus.py` | Already supports `mode` query param. Add `mode=hybrid` when feature flag on. No route change. |

### New (Add, Don’t Replace)

| Component | Path | Purpose |
|-----------|------|---------|
| **Structured extractor** | `backend/app/services/extraction/extractor.py` or `document_utils` | Sections, tables, candidate_dates, candidate_percentages. |
| **LLM parser** | `backend/app/services/llm_parser.py` | OpenAI call, prompt, schema enforcement. |
| **Validator** | `backend/app/services/validation.py` or inside `llm_parser` | Schema check, date normalize, dedupe. |

### Existing Heuristic Parser Role

| Module | Path | Role in Hybrid |
|--------|------|----------------|
| **syllabus_parser** | `backend/app/services/syllabus_parser/` | **Fallback:** If LLM fails, times out, or returns empty → run `parse_syllabus_text()`. **Also:** Optionally run in parallel and merge (e.g. take LLM assessments + heuristic meeting times if LLM missed them). |
| **assessments.py** | `backend/app/services/syllabus_parser/assessments.py` | Can reuse regex for `candidate_percentages` in Step 1 (pre-extraction). Optional. |
| **meeting_times.py** | `backend/app/services/syllabus_parser/meeting_times.py` | Can reuse patterns for `candidate_meetings` in Step 1. Optional. |

---

## Four-Step Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Step 1: Raw Extraction (Deterministic)                                          │
│  PDF/DOCX/TXT → structured text, tables, headings, date-like strings             │
└─────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Step 2: LLM Structured Parsing                                                  │
│  Feed relevant sections to LLM with strict JSON schema → structured output      │
└─────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Step 3: Validate + Normalize                                                    │
│  Schema enforcement, date normalization, cross-field consistency, DB readiness   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Step 4: User Review / Confirm / Edit                                            │
│  UI already exists; confidence scores guide attention                            │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Step 1: Raw Structured Extraction (Deterministic)

**Goal:** Extract text, structure it lightly. Do **not** try to fully interpret it. Output a machine-readable intermediate format that the LLM (or fallback heuristics) can consume.

### 1.1 Document Extraction

| Format   | Tool              | Notes                                                   |
|----------|-------------------|---------------------------------------------------------|
| PDF      | **pdfplumber**    | Already used; preserve tables via `page.extract_tables()` |
| PDF      | **PyMuPDF (fitz)**| Optional: better layout, image handling if needed       |
| DOCX     | **python-docx**   | Already used; extract paragraphs + tables separately   |
| TXT      | Direct read       | UTF-8, handle BOM                                      |

### 1.2 Light Structure (Intermediate Format)

Produce a structured blob instead of raw concatenated text:

```json
{
  "sections": [
    {
      "heading": "Course Logistics",
      "content": "The LECTURE will be on Tuesday/Thursday...",
      "tables": [
        ["Week", "Date", "Topic", "Readings", "Assignments"],
        ["1", "Sept. 30", "lecture-0-welcome.pdf", "", "Lab 0"],
        ["2", "Oct. 7", "lecture-3-system-calls.pdf", "OSC: Ch 2", "Project 1 (out: Oct. 3)"]
      ],
      "candidate_dates": ["Sept. 30", "Oct. 3", "Oct. 7", "Oct. 24", "Nov. 4", "Dec. 11"],
      "candidate_percentages": [{"value": 20, "context": "Projects 20%"}, {"value": 20, "context": "Midterm 20%"}]
    }
  ],
  "raw_text": "...",
  "metadata": { "source_type": "pdf", "page_count": 5 }
}
```

### 1.3 Rule-Based Pre-Extraction (Token Reduction)

Use **rules** to:

1. **Detect date-like strings** — regex for `Oct. 24`, `November 4`, `12/11`, `Dec 11 12:30`, etc. Reuse `date_utils.parse_due_date` patterns.
2. **Detect percentage weights** — `(\d{1,3})\s*%` with ~30 chars context before/after.
3. **Extract candidate lines** — lines containing dates, percentages, or assessment keywords (`Project`, `Homework`, `Midterm`, `Final`, `Quiz`, `Lab`, `Assignment`, `Exam`).
4. **Section detection** — headers like "Grading", "Schedule", "Course Information", "Assignments", "Course Logistics", "Evaluation", "Assessment". Pattern: `^(?:#{1,3}\s*)?([A-Za-z][A-Za-z\s]+)[:\s]*$` or explicit list.
5. **Table extraction** — preserve table structure; pdfplumber `extract_tables()`, python-docx `doc.tables`.

**Section keywords (case-insensitive):**

- Grading, Grade, Evaluation, Assessment, Weights
- Schedule, Calendar, Syllabus (as header)
- Course Information, Course Logistics, Course Overview
- Assignments, Homework, Projects, Exams

**Token reduction:** Feed the LLM only these sections/blocks, not the entire syllabus. A 20-page syllabus might shrink to 3–5 relevant blocks. This cuts tokens by 60–80%.

---

## Step 2: LLM Structured Parsing

**Goal:** Use an LLM to interpret pre-extracted content into our exact JSON schema. The LLM is good at date context, grading weight inference, recurrence detection, and mapping items to categories—things regex struggles with.

### 2.1 API Choice (OpenAI)

- **Recommended:** OpenAI API (GPT-4o or GPT-4o-mini for cost/speed)
- **Structured output:** Use **JSON schema mode** or **function calling** to force valid JSON
- **Fallback:** Claude / Anthropic if needed; same structured-output pattern

### 2.2 JSON Schema (Foolproof and Detailed)

The schema must be **explicit** so the LLM cannot invent fields or omit required ones. Define in code (Pydantic or JSON Schema) and pass to the API.

```json
{
  "course": {
    "course_code": "string | null",
    "course_title": "string | null",
    "term": "string | null",
    "timezone": "string (default: America/Los_Angeles)",
    "instructors": [{"id": "string", "name": "string | null", "email": "string | null"}],
    "meeting_times": [{
      "day_of_week": "MO|TU|WE|TH|FR|SA|SU",
      "start_time": "HH:MM | null",
      "end_time": "HH:MM | null",
      "location": "string | null",
      "type": "lecture|lab|discussion|other"
    }]
  },
  "assessment_categories": [{"id": "string", "name": "string", "weight_percent": "number | null"}],
  "assessments": [{
    "id": "string",
    "title": "string",
    "category_id": "string",
    "type": "assignment|midterm|final|quiz|project|participation",
    "due_datetime": "ISO8601 | null",
    "all_day": "boolean",
    "weight_percent": "number | null",
    "recurrence": {"frequency": "weekly", "interval": 1, "by_day": ["TU"], "until": "date | null", "count": "number | null"} | null,
    "confidence": "number 0-1",
    "source_excerpt": "string (quote from syllabus)"
  }],
  "late_pass_policy": {"total_allowed": "number | null", "extension_days": "number | null"}
}
```

### 2.3 Confidence Scoring

Each assessment (and optionally each meeting time) gets a `confidence` score (0–1):

- **0.9+**: Clear evidence (date + weight in grading table)
- **0.6–0.9**: Inferred from context (date in schedule, weight elsewhere)
- **0.3–0.6**: Uncertain (no date, ambiguous type)
- **< 0.3**: Guess; highlight for user

**Prompt instruction:**  
*"Assign confidence 0.0–1.0 for each assessment based on how clearly the syllabus states it. Use 0.9+ only when you see explicit due date and/or weight. Use 0.5–0.7 when inferring from schedule context."*

### 2.4 LLM Prompt Design

**System prompt (concise):**

```
You are a syllabus parser. Extract course info, meeting times, and assessments from the provided syllabus sections.
Output strictly valid JSON matching the schema. Use ISO 8601 for dates (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS).
Infer academic year from term (e.g. Fall 2025 → 2025). Assign confidence 0–1 per assessment.
If unclear, use null. Do not invent data.
```

**User prompt (per call):**

```
Parse this syllabus section into the schema:

[SECTION: Grading]
Projects 20%, Midterm 20%, Final 20%, Labs 20%, Participation 20%

[SECTION: Schedule]
Project 1 (due: Oct. 24)
Project 2 (due: Nov. 19)
Nov. 4 MIDTERM
Dec. 11 12:30–14:30 FINAL

[COURSE INFO]
CS 415 Operating Systems, Fall 2025
Lecture: Tu/Th 16:00–17:20, 125 McKenzie Hall
LAB: Thursday, B026 Klamath
```

**Chunking:** If sections are large, split into multiple calls (grading + schedule + course info) and merge results.

### 2.5 Structured Output Mode (OpenAI)

- **response_format: { type: "json_schema", json_schema: {...} }** — forces valid JSON
- Or **tools / function calling** with a function that accepts the schema as parameters

---

## Step 3: Validate + Normalize

**Goal:** Turn LLM output into DB-ready, scheduler-ready data. Catch schema violations and logical errors.

### 3.1 Validation Pipeline

| Step            | Action |
|-----------------|--------|
| Schema validate | Ensure all required fields, correct types, allowed enums |
| Date normalize  | Convert `Oct. 24` → `2025-10-24`; handle academic year |
| Dedupe          | Merge duplicate assessments (same title + type) |
| Consistency     | `category_id` must exist; `weight_percent` sum ≤ 110% |
| IDs             | Generate stable `id` for each assessment/meeting |
| Fallback fill   | If LLM returns empty, run heuristic parser and merge |

### 3.2 Normalization Rules

- **day_of_week:** Normalize `Tuesday` → `TU`, `Th` → `TH`
- **time:** `4:00 PM` → `16:00`, `12:30-2:30` → `12:30`, `14:30`
- **term:** Infer year from context; default to current year
- **location:** Abbreviate if desired (e.g. `125 McKenzie Hall` → `125 MCK`)

### 3.3 DB Conversion

Map schema to existing tables:

- `course` → `Courses` (course_name, term_id)
- `assessments` → `Assignments` (assignment_name, work_load, due_date, assignment_type, course_id)
- `meeting_times` → `Meetings` (start_time, end_time, course_id)

`work_load` = hours × 4 (15-min increments). Default if absent.

---

## Step 4: User Review / Confirm / Edit

- UI already supports editable cells, drag-and-drop, add/remove rows
- Use `confidence` to **highlight low-confidence rows** (e.g. yellow background, tooltip)
- Optional: "Suggest edits" for low-confidence items (e.g. "Did you mean Project 1 due Oct 24?")
- On confirm → persist to DB

---

## Token Cost Reduction

| Strategy                    | Effect |
|----------------------------|--------|
| Rule-based section extraction | Send only grading + schedule + course info; skip policies, readings, etc. |
| Candidate line filtering   | Send lines containing dates, %, or assessment keywords |
| Chunked calls              | One call for grading, one for schedule; smaller inputs |
| Use GPT-4o-mini            | ~10× cheaper than GPT-4o; often sufficient for structured extraction |
| Caching                    | Same syllabus re-parsed → cache by hash; skip LLM |
| Fallback heuristic        | If heuristic parser gets high confidence, skip LLM for that upload |

**Rough estimate:** ~2–5K input tokens + ~1–2K output tokens per syllabus → ~$0.01–0.03 per parse with GPT-4o-mini.

---

## Architecture with Railway

### Current Setup

- **Frontend:** Vercel
- **Backend:** Render (Flask)
- **Database:** Railway MySQL

### Hybrid Parser Placement

1. **Backend (Render):** Add LLM parsing service
   - New module: `app/services/llm_parser.py` (or `hybrid_parser.py`)
   - Call OpenAI from backend (server-side only; never expose API key to client)
   - Environment variable: `OPENAI_API_KEY` (set in Render dashboard, marked secret)

2. **Flow:**
   - User uploads → `document_utils.extract_text_from_file` (existing)
   - New: `extract_structured_sections()` → intermediate format
   - New: `llm_parse_to_schema(intermediate)` → LLM call
   - New: `validate_and_normalize(llm_output)` → DB-ready
   - Existing: `parsing_service` API shape for UI

3. **Feature flag:**  
   - `USE_LLM_PARSER=true` → hybrid path  
   - `USE_LLM_PARSER=false` → current heuristic-only path (for testing or cost control)

### Railway Considerations

- **Compute:** LLM calls add 2–5s latency. Render free tier may sleep; consider paid tier for faster cold starts.
- **Secrets:** Store `OPENAI_API_KEY` in Render env vars. Never commit.
- **Timeouts:** Set request timeout to 30s for parse endpoint (LLM can be slow).

---

## MySQL vs Supabase / PostgreSQL

### Current: MySQL on Railway

**Pros:**
- Already deployed; schema and migrations in place
- Railway MySQL free tier available
- Backend uses `mysql.connector` / PyMySQL; no migration needed

**Cons:**
- Railway MySQL can be flaky (see DEPLOYMENT.md: "Lost connection" issues)
- JSON columns: MySQL has `JSON` type but less ergonomic than PostgreSQL for nested JSON
- No built-in realtime; no auth integration (Syllabify has its own auth)

### Alternative: Supabase (PostgreSQL)

**Pros:**
- PostgreSQL: excellent `JSONB`, full-text search, array types
- Supabase: auth, storage, realtime, Edge Functions—if you want them later
- Often more stable than Railway MySQL on free tier

**Cons:**
- **Migration cost:** New schema, new connection, update all queries
- Syllabify already has auth; Supabase auth is redundant unless you replace it
- More moving parts for a project that may not need them

### Alternative: Neon / PlanetScale (PostgreSQL / MySQL)

- **Neon:** PostgreSQL, serverless, good free tier
- **PlanetScale:** MySQL-compatible, branching, often more reliable than Railway MySQL

### Recommendation for Syllabify

- **Stay with MySQL on Railway** for now. The hybrid parser does not require PostgreSQL features. JSON is stored as `TEXT` or `JSON` in MySQL and parsed in Python—works fine.
- **If Railway MySQL proves unreliable:** Migrate to **PlanetScale** (minimal code change) or **Neon** (if you want PostgreSQL). Avoid a big migration until it’s justified.
- **Supabase:** Consider only if you plan to adopt Supabase auth, storage, or realtime. For parser-only changes, it’s unnecessary.

---

## Implementation Roadmap

### Phase 0: Prep (Do First)

| Step | Owner | Action |
|------|-------|--------|
| 0.1 | You | Create OpenAI account, add payment, create API key |
| 0.2 | You | Add `OPENAI_API_KEY` to `.env` (local) and Render (prod) |
| 0.3 | We | Add `openai` to `backend/requirements.txt` |
| 0.4 | We | Add `USE_LLM_PARSER=false` to `.env.example` and document it |

---

### Phase 1: Structured Extraction (1–2 weeks)

**Goal:** Produce `{ sections, tables, candidate_dates, candidate_percentages }` from PDF/DOCX/TXT. No LLM yet.

| Step | File | Action |
|------|------|--------|
| 1.1 | `backend/app/utils/document_utils.py` | Add `extract_structured_from_file(file)` → dict. Keep `extract_text_from_file()` unchanged. |
| 1.2 | `document_utils.py` | For PDF: use `pdfplumber` `page.extract_tables()`; return `tables` per page/section. Already have `page.extract_text()`. |
| 1.3 | `document_utils.py` | For DOCX: extract tables separately (python-docx `doc.tables`); return structure similar to PDF. |
| 1.4 | New or `document_utils` | Add `detect_sections(raw_text)` — regex for headings like "Grading", "Schedule", "Course Information", "Assignments", "Syllabus". Split text into `{heading, content}`. |
| 1.5 | New or `document_utils` | Add `extract_candidate_dates(text)` — reuse patterns from `date_utils` + syllabus_parser. Return list of `{raw, normalized?, context}`. |
| 1.6 | New or `document_utils` | Add `extract_candidate_percentages(text)` — regex `(\d{1,3})\s*%` with ~20 chars context. Return list of `{value, context}`. |
| 1.7 | Tests | Add `tests/test_document_utils.py` cases for `extract_structured_from_file` using CS415 fixture. |
| 1.8 | Integration | Wire `extract_structured_from_file` into a temp endpoint or script to verify output. No parser change yet. |

**Deliverable:** `extract_structured_from_file(file)` returns the intermediate JSON. Token reduction ready for Phase 2.

---

### Phase 2: LLM Parser (2–3 weeks)

**Goal:** Call OpenAI with structured output. Input = intermediate from Phase 1; output = schema-matched JSON.

| Step | File | Action |
|------|------|--------|
| 2.1 | `backend/requirements.txt` | Add `openai>=1.0.0` (or version you choose). |
| 2.2 | New: `backend/app/services/llm_parser.py` | Create module. Define schema (Pydantic models or dict) matching `parsed.json` shape. |
| 2.3 | `llm_parser.py` | Implement `parse_with_llm(intermediate: dict) -> dict`. Build prompt from `intermediate["sections"]`, `candidate_dates`, `candidate_percentages`. |
| 2.4 | `llm_parser.py` | Use OpenAI `client.chat.completions.create()` with `response_format={"type": "json_schema", "json_schema": {...}}` or function calling. |
| 2.5 | `llm_parser.py` | Add system prompt (see §2.4). Add user prompt template with `[SECTION: X]` blocks. |
| 2.6 | `llm_parser.py` | Add confidence instructions. Ensure each assessment has `confidence` 0–1. |
| 2.7 | `llm_parser.py` | Handle errors: timeout, rate limit, invalid JSON. Return `None` or raise; caller will fallback to heuristic. |
| 2.8 | Tests | Add `tests/test_llm_parser.py` with mocked OpenAI (no real API calls in CI). Use fixture intermediate from Phase 1. |
| 2.9 | Manual test | Run locally with real API key against CS415 extracted content. Verify output shape. |

**Deliverable:** `parse_with_llm(intermediate)` returns schema-valid dict or None.

---

### Phase 3: Validation + Integration (1–2 weeks)

**Goal:** Validate LLM output, normalize, map to API shape, add feature flag and fallback.

| Step | File | Action |
|------|------|--------|
| 3.1 | New or `llm_parser.py` | Add `validate_and_normalize(llm_output)`. Schema check (required fields, enums). Use `date_utils.parse_due_date` for any remaining date strings. |
| 3.2 | Validator | Dedupe assessments (same title+type). Ensure `category_id` exists. Cap `weight_percent` sum at 110. |
| 3.3 | Validator | Generate stable IDs (`project_1`, `midterm_1`, etc.) if missing. |
| 3.4 | `parsing_service.py` | Add `_parse_hybrid(file)` or `_parse_hybrid_text(text)`. Flow: `extract_structured_from_file` → `parse_with_llm` → `validate_and_normalize` → map to `{course_name, assignments, assessments, meeting_times, confidence}`. |
| 3.5 | `parsing_service.py` | In `parse_text()` / `parse_file()`: if `os.getenv("USE_LLM_PARSER") == "true"` and `mode in ("hybrid", "rule")`, try hybrid first. On failure/empty, fall back to `_parse_with_syllabus_parser()`. |
| 3.6 | `parsing_service.py` | Map LLM result to same shape as heuristic: `assignments` = `[{name, due_date, hours, type}]` derived from `assessments`. Reuse `_hours_from_assessment_type`, `_is_junk_title` if needed. |
| 3.7 | `syllabus.py` | Add `?mode=hybrid` support (may already exist). When `USE_LLM_PARSER=true`, default `mode` to `hybrid` or accept both. |
| 3.8 | `.env.example` | Document `USE_LLM_PARSER`, `OPENAI_API_KEY`. |
| 3.9 | Render | Set `USE_LLM_PARSER=true`, `OPENAI_API_KEY=<secret>` in Render env. |
| 3.10 | Tests | End-to-end: `POST /parse` with file, `USE_LLM_PARSER=true`, mocked LLM. Assert response shape. |

**Deliverable:** Hybrid parser wired end-to-end. Feature flag controls it. Fallback works.

---

### Phase 4: UI + Polish (1 week)

**Goal:** Surface confidence, optional re-parse, monitor costs.

| Step | File | Action |
|------|------|--------|
| 4.1 | Frontend | Pass `confidence` from assessments to UI. Each assignment row: if `confidence < 0.6`, add visual cue (yellow background, icon, tooltip "Parsed with low confidence—please verify"). |
| 4.2 | Frontend | Optionally add "Re-parse" or "Parse with AI" button that re-calls `POST /parse?mode=hybrid`. |
| 4.3 | Backend | Optional: log token usage for monitoring. Add simple counter or log `usage` from OpenAI response. |
| 4.4 | Docs | Update `hybrid-parser.md` with any learnings. Document cost per parse. |

**Deliverable:** User sees which items need review. Optional re-parse. Basic observability.

---

### Order of Implementation (Dependencies)

```
Phase 0 (prep) ──┐
                 │
Phase 1 ─────────┼──► Phase 2 ──► Phase 3 ──► Phase 4
                 │
(no dependency on 0 for Phase 1)
```

- Phase 1 can start immediately (no API key needed).
- Phase 2 needs API key and Phase 1’s `extract_structured_from_file`.
- Phase 3 needs Phase 2’s `parse_with_llm`.
- Phase 4 needs Phase 3 deployed.

---

## First Implementation Session (When We Begin)

**Suggested order for Day 1:**

1. **Phase 0.3–0.4** — Add `openai` to requirements, add `USE_LLM_PARSER` to `.env.example`. (5 min)
2. **Phase 1.1–1.2** — Implement `extract_structured_from_file()` in `document_utils.py`. Start with PDF: `extract_text()` + `extract_tables()`. Return `{raw_text, tables, metadata}`. (1–2 hrs)
3. **Phase 1.4–1.6** — Add section detection and candidate date/percentage extraction. These can be separate helper functions. (1–2 hrs)
4. **Phase 1.7** — Add a test using CS415 or another fixture. Verify intermediate format. (30 min)

By end of Day 1 we have: structured extraction working, no LLM yet, existing parser untouched.

---

## Merge Strategy (LLM + Heuristic)

When both LLM and heuristic produce results, options:

- **A. LLM-primary:** Use LLM output. If LLM returns empty for a subset (e.g. no meeting_times), fill from heuristic for that subset only.
- **B. Heuristic fallback only:** Use LLM. If LLM fails entirely (timeout, error, empty), use full heuristic output.
- **C. Merge by confidence:** Use LLM items with confidence ≥ 0.5; for missing types (e.g. no projects), add heuristic items. Dedupe by (title, type).

**Recommendation:** Start with **B** (simple fallback). Add **A** (partial fill) in a later iteration if needed.

---

## References

- [OpenAI Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- Contract analyzers: LLM + schema enforcement (e.g. Kira, Luminance)
- Invoice parsers: LLM + rule validation (e.g. Rossum, DocuSign)
- Syllabify: `backend/app/services/syllabus_parser/`, `parsing_service.py`, `docs/patterns.md`, `docs/SCHEDULING_ENGINE_DATA.md`

---

## Quick Reference: Key Files

| Purpose | Path |
|---------|------|
| Document extraction (PDF/DOCX/TXT) | `backend/app/utils/document_utils.py` |
| Date parsing | `backend/app/utils/date_utils.py` |
| Heuristic syllabus parser | `backend/app/services/syllabus_parser/` |
| Parsing API layer | `backend/app/services/parsing_service.py` |
| Syllabus API route | `backend/app/api/syllabus.py` |
| Schema reference | `backend/tests/fixtures/syllabus-data/syllabus/CS415/parsed.json` |
| New: structured extractor | Extend `document_utils` or `backend/app/services/extraction/` |
| New: LLM parser | `backend/app/services/llm_parser.py` |
| New: validator | `backend/app/services/validation.py` or inside `llm_parser` |

**Note:** `parsing_service.parse_text()` already supports `mode="hybrid"` and `mode="ai"` (looks for `ai_parser`). We will implement the hybrid path there; the `ai_parser` import can be replaced or the logic consolidated.
