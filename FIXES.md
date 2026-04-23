# FIXES.md

Tracking bugs, flaws, and the full upgrade roadmap for making Syllabify competitive.

---

## What This App Is

**Syllabify** is an academic planning web app for university students. Core flow:

1. Upload a course syllabus (PDF or pasted text).
2. Backend parses it — via rule-based heuristics or GPT-5 nano — extracting assignments, deadlines, meeting times, and workload estimates.
3. User reviews and edits parsed data.
4. A scheduling engine (min-cost max-flow) generates a balanced study schedule that avoids class meeting times and calendar conflicts.
5. Schedule renders on a FullCalendar view and exports to iCal / Google Calendar.

Stack: React + Tailwind · Flask + SQLAlchemy + MySQL · Docker · Vercel + Render.

---

## Competitive Landscape

Apps Syllabify competes with: **Motion** (AI calendar), **Reclaim.ai** (smart scheduling), **MyStudyLife**, **Notion** (manual), **Canvas** (source of truth, no scheduling).

Where Syllabify has a genuine edge: syllabus-to-schedule pipeline is unique. No other tool does LLM extraction → conflict-aware scheduling → FullCalendar in one flow. The gap is in polish, reliability, and features the other apps do well (completion tracking, mobile, notifications, onboarding).

---

## Phase 1 — Critical Bug Fixes (do first, nothing else matters)

- [x] **`stStart` is undefined — calendar never renders merged study blocks**
  `frontend/src/pages/Schedule.jsx:443`
  The `mergedStudyTimes` memo references `stStart` which is never declared. This is a live `ReferenceError` that fires on every schedule page load with study times present. The `mergedStudyTimes` array passed to `AppCalendar` will always be empty, so dragging and grouping never work.
  **Fixed:** inlined `new Date(st.start_time).getTime()` directly into the `adjacent` comparison.

- [x] **Per-course weekly study cap is computed but completely ignored by the scheduler**
  `backend/app/services/scheduling_service.py:628–634`
  `max_minutes_per_week_by_course` is built from `course.study_hours_per_week` then never referenced again anywhere in the file. The min-cost max-flow allocates slots without any weekly-hours-per-course constraint. The Course page setting for "max study hours per week" has zero effect.
  **Fixed:** post-flow trimming in `_generate_study_times_min_cost` — after flow extraction, slots are grouped by (course, ISO week) and trimmed to the cap. Earlier-due assignments keep their slots first. `max_minutes_per_week_by_course` is now passed from `generate_study_times`.

- [x] **Auto-generate on upload confirm is silent — user gets no feedback and failures are swallowed**
  `frontend/src/pages/Upload.jsx:195–204`
  After confirming parsed data, study times are auto-generated in a fire-and-forget `try/catch` that ignores errors. If generation fails (e.g. no term dates), the confirm screen falsely says "Study times have been generated." Users then go to the schedule page and see nothing.
  **Fixed:** outcome is tracked in `scheduleGenerated`/`scheduleGenError` state. Confirm step now shows a green success message or an explanatory error with a link to the Schedule page.

---

## Phase 2 — Security (block-ship issues)

- [x] **Hardcoded dev credentials committed to source**
  `backend/app/api/auth.py:21–22` and in the file's opening comment on line 2.
  `DEV_USERNAME = "syllabify-client"` and `DEV_PASSWORD = "ineedtocutmytoenails422"` are checked into git. `ensure_dev_user()` auto-creates this account in any database. This means a production DB will always have a known-credential backdoor account.
  **Fixed:** deleted `DEV_USERNAME`, `DEV_PASSWORD`, and `ensure_dev_user()` entirely.

- [x] **JWT tokens have no expiry**
  `backend/app/api/auth.py:76–83`
  `token_for_user()` never sets `exp`. A stolen or leaked token is permanently valid.
  **Fixed:** added `exp` claim using `JWT_EXPIRY_DAYS` env var (default 7 days). `decode_token` already handled `ExpiredSignatureError`.

- [x] **No rate limiting on auth endpoints**
  `/api/auth/login` and `/api/auth/register` accept unlimited requests. Brute-force password attacks and credential stuffing are trivially possible.
  **Fixed:** added `flask-limiter` (`extensions.py`), `limiter.init_app(app)` in `main.py`, and `@limiter.limit()` decorators: 10/min on login, 5/min on register, 5/min on Google sign-in.

- [x] **`PATCH /api/assignments/:id` has no field length validation**
  `backend/app/api/assignments.py:78–81`
  `assignment_name` is written to the DB without a length check. A name of 100,000 chars is accepted. The DB column likely has a varchar limit that will error silently rather than returning a clean 400.
  **Fixed:** returns 400 `"assignment_name too long (max 500 characters)"` when `len(name) > 500`.

---

## Phase 3 — Architecture & Code Quality

- [x] **`get_db()` is copy-pasted across three files**
  Defined identically in `auth.py`, as `get_db_connection()` in `main.py`, and as `_get_db()` in `schedule.py`. All three create MySQL connections from the same env vars. Any connection parameter change (SSL, pool size, timeout) needs updating in three places.
  **Fixed:** created `backend/app/db/connection.py::get_db()`; `auth.py`, `calendar.py`, and `schedule.py` now import from there. `main.py`'s `get_db_connection` removed; `term_utils.py` updated to import from `app.db.connection`.

- [x] **Misleading JSDoc on `updateCalendarSource`**
  `frontend/src/api/client.js:975`
  Comment says `DELETE /api/calendar/sources/:sourceId` but the function sends `PATCH`. Minor, causes real confusion.
  **Fixed:** corrected to `PATCH /api/calendar/sources/:sourceId. Updates color. Returns { ok }.`

- [x] **`_maintenance_check` calls `get_maintenance_status()` up to twice per blocked request**
  `backend/app/main.py:73–83`
  Calls `get_maintenance_status()` once to check and again inside the error `jsonify` on line 79. Two DB lookups for a single denied request.
  **Fixed:** destructure `enabled, message = get_maintenance_status()` once; `message` reused in both error returns.

- [x] **OpenAI client instantiated fresh on every LLM call**
  `backend/app/services/llm_parser.py:170–171` and `225–226`
  `OpenAI(api_key=api_key)` is called on every `parse_with_llm()` and `estimate_assignment_hours()` invocation. No connection reuse.
  **Fixed:** module-level `_openai_client` lazy singleton via `_get_openai_client()`; both call sites updated.

- [x] **`PATCH /api/schedule/study-times/:id` builds SQL with f-string**
  `backend/app/api/schedule.py:453–456`
  `f"UPDATE StudyTimes SET {', '.join(updates)} WHERE id = %s"` — the column names come from hardcoded strings so injection isn't possible here, but the pattern is risky and fails linters. Reads as insecure to any code reviewer.
  **Fixed:** replaced with `sql = "UPDATE StudyTimes SET " + ", ".join(updates) + " WHERE id = %s"` with a comment explaining the allowlist source.

- [x] **Timezone selector in Preferences only offers 5 US timezones + UTC**
  `frontend/src/pages/Preferences.jsx:432–455`
  International students (EU, Asia-Pacific, etc.) see no matching option and get silently stuck on "Browser default." When the browser default differs from their actual study location, all scheduling is shifted.
  **Fixed:** replaced hardcoded options with `Intl.supportedValuesOf('timeZone')` (with a sensible fallback list for older browsers), grouped into `<optgroup>` by continent/region.

- [x] **Saving account and saving preferences share the same `saving` boolean**
  `frontend/src/pages/Preferences.jsx:63,104–119,151–172`
  Both `handleSaveAccount` and `handleSavePreferences` set `setSaving(true/false)`. Submitting one form while the other is in flight produces garbled button states.
  **Fixed:** split into `savingAccount`/`setSavingAccount` and `savingPrefs`/`setSavingPrefs`; each handler and button uses its own state.

---

## Phase 4 — Feature Completeness (things users expect before recommending to friends)

- [x] **No "Forgot Password" flow — security Q&A is a dead-end**
  `UserSecurityAnswers` table and setup UI exist, but there is no `POST /api/auth/forgot-password` endpoint and no `/forgot-password` page. Users who forget their password have no recovery path.
  **Fixed:** added `GET /api/auth/security-questions`, `POST /api/auth/verify-security`, `POST /api/auth/reset-password` to `auth.py`. Reset token is a 15-min JWT that auto-invalidates when the password changes. Added `ForgotPassword.jsx` and `ResetPassword.jsx` pages, routes in `App.jsx`, and "Forgot password?" link on `Login.jsx`.

- [x] **No assignment completion status — can't mark assignments as done**
  The scheduling engine never learns that you finished an assignment. Done assignments still show study blocks on the calendar, still count in the pie chart, and still affect schedule generation.
  **Fixed:** migration `015_assignment_completion.sql` adds `is_completed` + `completed_at`. `PATCH /api/assignments/:id` accepts `is_completed`. `schedule_input_builder.py` filters out completed assignments. Course.jsx `AssignmentRow` has a persistent checkbox; completed rows get strikethrough + dimmed styling.

- [x] **No delete confirmation on Dashboard — single click destroys all data**
  `frontend/src/pages/Dashboard.jsx:54–62`
  `handleDeleteCourse` fires immediately. Deleting a course also cascades and deletes all its assignments, meetings, and study times — irreversible from the UI.
  **Fixed:** `pendingDelete` state triggers a modal with course name + assignment count; a red "Delete" button confirms; "Cancel" dismisses. `CourseCard` now renders a hover-visible trash icon that fires `onDelete`.

- [x] **Dashboard "Schedule" card is nearly empty**
  `frontend/src/pages/Dashboard.jsx:124–139`
  Left column just says "Generate study times from your courses, then view your weekly schedule" and links away. This is wasted real-estate that could show upcoming deadlines or study blocks.
  **Fixed:** new `GET /api/assignments/upcoming?term_id=X&limit=5` endpoint; Dashboard fetches and renders next 5 due dates with color dot, course label, and color-coded days-left countdown (red ≤2d, amber ≤7d).

- [x] **Proposed schedule modal dumps raw 15-minute blocks**
  `frontend/src/pages/Schedule.jsx:555–590`
  The preview list renders every individual 15-minute slot. For a term with 10 assignments × 2 hours each, this is 80 rows. Completely unreadable.
  **Fixed:** modal now merges adjacent same-course slots inline before rendering using the same algorithm as `mergedStudyTimes`. Block count reflects merged count.

- [x] **`recentCourses` localStorage list grows unboundedly**
  `frontend/src/pages/Dashboard.jsx:35–41`
  Entries are read from localStorage but never trimmed or evicted. Courses from deleted terms persist forever.
  **Fixed:** on read, entries are cross-referenced against the current `courses` list (when a term is selected) and filtered; write was already capped at 5 in `Course.jsx`.

- [x] **Pie chart legend silently cuts off after 5 courses**
  `frontend/src/pages/Schedule.jsx:911`
  `.slice(0, 5)` with no overflow indicator. Users with 6+ courses get an incomplete legend.
  **Fixed:** a `+ N more course(s)` row is shown below the 5 legend entries when `studyTimeByCourse.length > 5`.

- [x] **No step-back guard on Upload — backward navigation loses state**
  `frontend/src/pages/Upload.jsx:106–107`
  Clicking a past step button (e.g. going back from "Confirm" to "Upload") clears the step without warning. If a course was already saved in step 2, navigating back and re-confirming creates a duplicate course.
  **Fixed:** step buttons are `disabled` when `step === 2` (confirmed) or when targeting a future step. Clicking a past button only works before confirmation.

- [x] **LLM timezone fallback is `America/Los_Angeles`**
  `backend/app/services/llm_parser.py:273`
  When the LLM can't detect a timezone from the syllabus, it defaults to Pacific time. Every European or Asian user's deadlines are parsed 8–13 hours off without any indication.
  **Fixed:** fallback changed to `"UTC"`.

---

## Phase 5 — Competitive Upgrades (what separates "school project" from "real product")

### 5a. Assignment Completion & Progress Tracking

- [x] **Add `is_completed` + `completed_at` to Assignments table**
  Done in Phase 4 — migration `015_assignment_completion.sql`, `PATCH /api/assignments/:id`, `schedule_input_builder.py` filter, and checkbox UI in `Course.jsx`.

- [ ] **Workload burndown chart on the Schedule page**
  Show a mini chart of "total study hours scheduled" vs. "hours remaining" across the term. This is the killer feature for anxious students. Motion and Reclaim don't do term-level burndown.

- [ ] **Smart rescheduling: drag a study block → ask "reschedule remaining blocks?"**
  When you move a study block, offer to re-optimize the remaining unlocked blocks for that assignment. Currently moving a block is a one-off change; the rest of the schedule doesn't adapt.

### 5b. Notifications & Reminders

- [ ] **Due-date email reminders**
  3-day and 1-day advance reminders for assignments. This alone increases retention dramatically — students come back because they get reminded. Use a simple SMTP send or a service like Resend.

- [ ] **Browser push notifications for study sessions**
  "Your CS 422 study block starts in 15 minutes." Requires a service worker. This is table-stakes for any calendar-adjacent app.

- [ ] **In-app notification center**
  A bell icon in the nav showing upcoming deadlines, overdue assignments, and schedule changes. Currently the app has zero notification surface area.

### 5c. Canvas / LMS Integration

- [ ] **Canvas LMS OAuth import**
  Canvas has a public API. Add `POST /api/integrations/canvas` that accepts a Canvas API token, pulls all courses and assignments from Canvas, and populates Syllabify automatically — no PDF upload required. This is the feature that would get this app featured by university IT departments.
  Priority: extremely high. This is the single biggest competitive differentiator.

- [ ] **Blackboard / Moodle parity**
  Lower priority than Canvas, but worth tracking.

### 5d. Mobile & PWA

- [ ] **Progressive Web App (PWA) manifest + service worker**
  Add `manifest.json`, a service worker for offline caching of the current week's schedule, and install prompts. Students primarily check their schedule on their phone. Without mobile, they'll keep using Google Calendar.

- [ ] **Mobile calendar view: day/agenda instead of week**
  FullCalendar's `timeGridWeek` is unusable on mobile. Default to `listWeek` or `timeGridDay` on narrow screens. The current app is essentially broken on phones.

### 5e. Study Session Intelligence

- [ ] **Built-in study timer (Pomodoro / stopwatch)**
  When you click a study block, offer "Start session" → starts a 25/50-min timer in a floating widget. Tracks actual time studied vs. scheduled. This data feeds back into workload estimates for future semesters.

- [ ] **AI workload calibration over time**
  After a few weeks, the app learns "you consistently underestimate quiz prep by 2×" and adjusts future estimates. Requires storing actual-vs-estimated time per assignment type.

- [ ] **"Catch me up" reschedule**
  If you fall behind (missed study blocks are detected after due date passes with no completion), offer a one-click "catch me up" that re-packs remaining work into the available schedule window.

### 5f. Collaboration & Social

- [ ] **Study group scheduling**
  Let multiple Syllabify users share availability for a course and find common free blocks. This requires a basic sharing model but is a strong viral feature — one user invites their study group.

- [ ] **Course-level public syllabi sharing**
  Let users share a parsed+cleaned syllabus with a read-only link. When a classmate uses that link, it pre-fills their upload step. Reduces AI parsing errors for the same course.

### 5g. Homepage & Onboarding

- [ ] **Homepage has no screenshots, demo, or social proof**
  `frontend/src/pages/Homepage.jsx`
  Three text cards on a white background. There's no visual evidence of what the app does. No screenshots, no animated demo, no "used by X students," no university logos.
  **Fix:** add a hero screenshot/video of the calendar with study blocks, a feature comparison table vs. doing this manually in Notion, and a "Try it free" CTA that goes directly to a demo term with pre-loaded sample data.

- [ ] **No onboarding tour after registration**
  New users land on an empty Dashboard with no guidance. No tooltip sequence, no sample data, no "start here" prompt. Activation rate will be near zero.
  **Fix:** after first login, auto-create a demo term with one pre-loaded sample syllabus. Walk users through the upload → review → schedule flow with a 3-step tooltip overlay.

- [ ] **No empty-state call to action on the Schedule page**
  When there are no study times and no calendar events, the calendar shows a blank grid with no explanation of what to do.
  **Fix:** add an overlay on the empty calendar: "No study blocks yet. Upload a syllabus on the Dashboard to get started." with a direct link.

### 5h. Performance & Scale

- [ ] **No pagination on study times API — entire term returned at once**
  `backend/app/api/schedule.py:154–167`
  For a heavy term, this is potentially thousands of 15-minute rows in a single query with no LIMIT. FullCalendar will receive and render all of them regardless of the current view.
  **Fix:** filter by the calendar's current view window (pass `start_date`/`end_date` from the frontend when fetching). The params already exist in the API; just use them from the frontend.

- [ ] **Auto-sync fires all stale sources simultaneously**
  `frontend/src/pages/Schedule.jsx:109–124`
  `Promise.all(staleSources.map(...syncSource...))` with no concurrency cap. 10 ICS feeds = 10 simultaneous outbound HTTP requests, all on page load.
  **Fix:** use a sequential or batched sync (max 2 concurrent), with a brief delay between to avoid hammering external servers.

- [ ] **No database connection pooling**
  The app creates a new `mysql.connector.connect()` call per request, every time. At moderate traffic this exhausts MySQL's connection limit fast.
  **Fix:** use `mysql.connector.pooling.MySQLConnectionPool` (or switch to SQLAlchemy's connection pool, which is already used in the scheduling service but not the API routes).

- [ ] **Admin user list has no pagination**
  `backend/app/api/admin.py` (GET /api/admin/users)
  All users returned in one response. At 1000+ users this becomes a problem.
  **Fix:** add `limit`/`offset` params matching the audit log endpoint pattern.

---

## Phase 7 — MySQL → PostgreSQL / Supabase Migration

**Why:** Railway dropped its free tier. Supabase offers a free PostgreSQL instance with no credit card required.

### What's already done (code-level)

- [x] `backend/app/db/pg_compat.py` created — thin wrapper that makes psycopg2 behave like mysql.connector (`cursor(dictionary=True)` → `RealDictCursor`, `lastrowid` → auto-inject `RETURNING id`)
- [x] `backend/app/db/connection.py` updated — `get_db()` auto-detects `DATABASE_URL` env var; uses psycopg2 for `postgres[ql]://` URLs, mysql.connector otherwise
- [x] `backend/app/db/session.py` updated — SQLAlchemy engine prefers `DATABASE_URL`; rewrites `postgres://` → `postgresql+psycopg2://` for SQLAlchemy compatibility
- [x] `backend/requirements.txt` — added `psycopg2-binary>=2.9.0`
- [x] `docker/supabase-schema.sql` created — full PostgreSQL schema (all tables, all migrations including 015, `updated_at` triggers, indexes)
- [x] `CURDATE()` → `CURRENT_DATE` in `assignments.py` (both primary + fallback queries)
- [x] `ON DUPLICATE KEY UPDATE` → `ON CONFLICT ... DO UPDATE SET` in `admin_settings.py`, `maintenance.py`, `admin.py` (UserAdminNotes), `users.py` (UserPreferences)
- [x] MySQL `BOOLEAN DEFAULT 0/1` → `BOOLEAN DEFAULT FALSE/TRUE`, `JSON` → `JSONB`, inline `INDEX` → `CREATE INDEX` in schema

### ~~Remaining manual step — `calendar.py` upserts~~ ✅ Done

`backend/app/api/calendar.py` has 5 upsert patterns that still use `ON DUPLICATE KEY UPDATE`. These need to be converted before the app works on PostgreSQL:

| Table | Conflict columns | Lines (approx) |
|---|---|---|
| `UserOAuthTokens` | `(user_id, provider)` | ~102–103 |
| `ExternalEvents` (allday) | `(user_id, google_calendar_id, google_event_id)` | ~487 |
| `ExternalEvents` (timed) | `(user_id, google_calendar_id, google_event_id)` | ~507 |
| `CalendarEvents` (allday) | `(source_id, external_uid, instance_key)` | ~754 |
| `CalendarEvents` (timed) | `(source_id, external_uid, instance_key)` | ~771 |
| `CalendarEvents` (ICS allday) | `(source_id, external_uid, instance_key)` | ~1009 |
| `CalendarEvents` (ICS timed) | `(source_id, external_uid, instance_key)` | ~1025 |

Pattern to apply for each:
```sql
-- MySQL:
ON DUPLICATE KEY UPDATE col1 = VALUES(col1), col2 = VALUES(col2)
-- PostgreSQL:
ON CONFLICT (conflict_col1, conflict_col2) DO UPDATE SET col1 = EXCLUDED.col1, col2 = EXCLUDED.col2
```

Also: `updated_at = NOW()` in the `UserOAuthTokens` upsert (~line 103) is fine — PostgreSQL supports `NOW()`.

### Step-by-step migration guide

**1. Create a Supabase project**
- Go to [supabase.com](https://supabase.com) → New project → choose a region close to your users
- After creation: Project Settings → Database → copy the **Connection string (URI)** (starts with `postgresql://...`)

**2. Run the schema**
- Supabase Dashboard → SQL Editor → paste `docker/supabase-schema.sql` → Run
- Verify: Table Editor should show all tables

**3. Migrate existing data (optional)**
- Export from Railway MySQL: `mysqldump -h HOST -u USER -p DB_NAME --no-tablespaces > syllabify_export.sql`
- The dump won't run on PostgreSQL as-is. Use [pgloader](https://pgloader.io/) for automated MySQL→PG data migration:
  ```
  pgloader mysql://USER:PASS@RAILWAY_HOST/DB_NAME postgresql://USER:PASS@SUPABASE_HOST/postgres
  ```
- Or manually: export each table to CSV from MySQL Workbench, import via Supabase Dashboard → Table Editor → Import CSV

**4. Set environment variables**
- On Render (or wherever your Flask backend is deployed):
  - Add `DATABASE_URL` = the Supabase connection URI (e.g. `postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres`)
  - Remove or leave `DB_HOST`, `DB_USER`, etc. — they're ignored when `DATABASE_URL` is set
- For local development: add `DATABASE_URL=postgresql://...` to your `.env` file

**5. Fix `calendar.py` upserts** (see table above)

**6. Deploy and smoke-test**
- Register a new user, upload a syllabus, generate a schedule, check the calendar
- Verify admin settings (maintenance toggle, announcement banner) round-trip correctly

**7. Decommission Railway MySQL**
- Once Supabase is confirmed working, delete the Railway MySQL service to stop any charges

---

## Phase 6 — Polish (what makes the difference between "nice app" and "app people show friends")

- [ ] **No keyboard shortcut to generate study times**
  Power users want `G` → generate, `C` → clear, `S` → view schedule. The `ShortcutsOverlay` component exists but keyboard shortcuts for core actions may be missing.

- [ ] **Study block popover doesn't show which assignment it's for**
  `frontend/src/pages/Schedule.jsx:750–790`
  Clicking a study block shows course name and lock status, but not which specific assignment this block is studying for. For a course with 5 assignments you can't tell what you should be working on.
  **Fix:** show `assignment_name` from `st.assignment_id` (requires joining or passing assignment name in the study time payload).

- [ ] **No visual distinction between "past" and "future" study blocks on the calendar**
  Study blocks that are in the past should be visually dimmed or marked with a ✓ if completed. Currently past and future blocks look identical.

- [ ] **Course color picker on the Course page is not accessible**
  Color-only swatches have no label. Screen readers get no information about which color is selected.
  **Fix:** add `aria-label={color name}` and a text label below the selected color.

- [ ] **Upload step stepper allows jumping to "Confirm" before data is parsed**
  `frontend/src/pages/Upload.jsx:106–114`
  Step buttons are always clickable. A user can jump directly from step 0 ("Upload") to step 2 ("Confirm") by clicking the button, landing on a screen that says "You've confirmed 0 assignments."
  **Fix:** disable forward step buttons until that step's data is ready (`step > i` to enable backward, `step >= i` to enable current, future steps disabled).

- [ ] **`parseSyllabus` in `client.js` always defaults `mode` to `"rule"`**
  `frontend/src/api/client.js:109`
  The LLM mode (`"llm"`) requires an explicit opt-in but users never see an option to choose. LLM mode produces dramatically better results for most syllabi and should be the default (with rule as fallback).
  **Fix:** change the default `mode` to `"llm"` and show a "Quick parse (rule-based)" fallback option in `SyllabusUpload` for users on slow connections.

- [ ] **No loading skeleton on the Course page — content pops in**
  When navigating to `/app/courses/:id`, the page shows nothing while assignments load. Add a skeleton loader matching the assignment row layout.

---

## Already Done (Model Upgrade)

- [x] **Replaced GPT-4o-mini with GPT-5 nano** — `backend/app/services/llm_parser.py`
  Updated `LLM_MODEL` from `"gpt-4o-mini"` to `"gpt-5-nano"`. GPT-5 class quality at $0.05/$0.40 per 1M tokens — 4× cheaper input than GPT-4.1 nano, with better instruction following and structured output support.
