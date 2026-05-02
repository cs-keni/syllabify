# PHASES.md — Syllabify Portfolio Readiness

Tracking everything needed to take Syllabify from "school project that works" to "portfolio piece that impresses." Phases are ordered by priority; earlier phases are blockers for the ones after them.

> **Previous bugs/fixes** are tracked in `FIXES.md`. This document picks up where that leaves off — focusing exclusively on polish, portfolio presentation, and remaining feature gaps.

---

## Phase 1 — Embarrassments (fix before anyone sees the code)

These are red flags that a recruiter, engineer, or professor will notice immediately.

- [x] **Remove `test_placeholder.py`**
  `backend/tests/test_placeholder.py`
  Deleted.

- [x] **Replace the empty frontend test script**
  Installed Vitest + @testing-library/react. `npm test` now runs 7 passing tests across `homepage.test.jsx` and `syllabusUpload.test.jsx`. `vite.config.js` configured with jsdom environment.

- [x] **Add the `LICENSE` body**
  Already filled in (MIT, Copyright 2026 Kenny Nguyen).

- [x] **Audit and kill stale commented-out `console.log` calls**
  Only one `console.warn` remains (legitimate failure logging in Schedule.jsx:99). No debug-only logs found.

- [ ] **Verify no `.env` with real secrets is committed**
  Run `git log --all --full-history -- "*.env"` and confirm no real keys appear in history. The `.env.example` is fine; a committed `.env` with actual API keys is not.

---

## Phase 2 — UI/UX Polish (things users will immediately notice)

These come directly from FIXES.md Phase 6 — unchecked items that affect everyday use.

- [x] **Study block popover doesn't show which assignment it's for**
  Backend `GET /api/schedule/study-times` now JOINs `Assignments` and returns `assignment_name`. Both the click popover and hover preview in `Schedule.jsx` display it below the course name.

- [x] **No visual distinction between past and future study blocks**
  `AppCalendar.jsx` now adds `past-block` class to events whose `end_time < now`. `AppCalendar.css` applies `opacity: 0.45; filter: saturate(0.6)` to those events.

- [x] **LLM parse mode defaults to `"rule"` — users never get AI results**
  `parseSyllabus` in `client.js` now defaults to `mode: 'llm'`. `SyllabusUpload.jsx` has a "Quick parse (rule-based, faster)" checkbox to opt back to rule mode.

- [x] **No loading skeleton on Course page — content pops in abruptly**
  Already implemented — `Course.jsx` shows 5 shimmer rows while `loading === true`.

- [x] **Empty state on Schedule page gives no guidance**
  When `studyTimes.length === 0 && calendarEvents.length === 0`, a dashed-border card renders above the calendar with a "Go to Dashboard" CTA link.

- [ ] **Keyboard shortcuts for core actions (`G` / `C` / `E`)**
  `ShortcutsOverlay` component exists but core scheduling actions may not be wired up.
  **Fix:** add `useEffect` keydown listeners for: `G` → trigger generate study times, `C` → clear/confirm modal, `E` → open export menu. Document them in the overlay.

- [x] **Upload step stepper allows jumping to future steps**
  Already implemented — `Upload.jsx` has `disabled={i > step || step === 2}` on step buttons.

---

## Phase 3 — Homepage & Demo Experience (first impressions)

The homepage is the front door for portfolio reviewers. Currently three text cards on white — nothing shows what the app actually does.

- [x] **Hero section with real visuals**
  Homepage now has a two-column hero: headline + CTA on the left, a CSS-rendered calendar mockup (colored study blocks, now-indicator, day headers) on the right. No image file needed.

- [x] **Feature comparison or "how it works" section**
  Three numbered step cards (01/02/03) with emoji icons and descriptions replace the plain text cards. A four-item feature grid below covers AI parsing, scheduling algorithm, Google Calendar sync, and live calendar.

- [ ] **"Try the demo" CTA with pre-loaded sample data**
  New users who don't want to upload a real syllabus have no way to see the app. Create a demo account (or seed a guest session) with a pre-loaded sample term, courses, and generated schedule.
  **Fix:** add a `POST /api/auth/demo-login` endpoint that creates (or logs into) a read-only demo user with seeded data. The homepage CTA skips registration and drops users directly into a live calendar view.

- [ ] **Onboarding tooltip sequence after first login**
  New registered users land on an empty Dashboard with no hints. Activation rate near zero.
  **Fix:** track `has_seen_onboarding` in `UserPreferences`. After first login, show a 3-step tooltip overlay: (1) "Create a course," (2) "Upload a syllabus," (3) "View your schedule." Use a lightweight library like `intro.js` or a custom tooltip chain.

- [ ] **Add screenshots or GIF to README**
  The README describes the app well but has no visuals. GitHub profile visitors won't read 200 lines of text — a single annotated screenshot of the schedule page makes this instantly understandable.

---

## Phase 4 — Mobile (at minimum, make it not broken)

The app is essentially unusable on phones. This doesn't need to be perfect, but a recruiter checking it on mobile shouldn't see a broken layout.

- [x] **Default to `listWeek` or `timeGridDay` on narrow screens**
  `AppCalendar.jsx` now detects `window.innerWidth < 768` at module load. On mobile, `initialView` is `'listWeek'` and `editable`/`selectable` are both `false` (disabling drag).

- [ ] **Navigation drawer on mobile**
  The sidebar nav likely doesn't collapse on small screens. Add a hamburger menu that opens a slide-over drawer on mobile.

- [x] **Touch-friendly event interaction on mobile**
  `editable={!isMobile}` and `selectable={!isMobile}` are now passed to FullCalendar. Individual study events also have `editable: !isMobile` set.

---

## Phase 5 — High-Impact Features (separate "school project" from "real product")

Pick 1–2 of these to implement before the portfolio deadline. Each one alone is worth highlighting.

### 5a. Workload Burndown Chart

- [ ] **Term-level burndown visualization on Schedule page**
  A line chart showing "total study hours scheduled" vs. "hours remaining (past blocks)" across the term length. Shows at a glance whether you're ahead or behind.
  Stack: Recharts (already likely available via React ecosystem, or add via npm). Pull data from existing `StudyTimes` table grouped by week.

### 5b. Smart Rescheduling on Drag

- [ ] **After dragging a study block, offer "Reschedule remaining blocks?"**
  Currently dragging a block is a one-off update. The remaining schedule doesn't adapt. After a drag, show a small toast: "Block moved. Re-optimize remaining X blocks? [Yes] [No]"
  **Fix:** after `PATCH /api/schedule/study-times/:id` resolves, call the generate endpoint with a `lock_before` param to preserve already-moved blocks and re-run the flow for the rest.

### 5c. LLM Parse Mode Toggle + Feedback

- [ ] **Show parse confidence and allow user correction in the review step**
  When LLM parse mode is used, the backend already has confidence data. Surface it in the review UI: low-confidence fields highlighted in amber with "Suggested — please verify." This is a strong UX differentiator.

### 5d. Due-Date Email Reminders

- [ ] **3-day and 1-day advance reminders for assignments**
  Use Resend (free tier: 3,000 emails/month) or SendGrid. A daily cron job queries assignments due within 3 days and 1 day, cross-references user preferences, and sends a formatted email summary.
  High retention impact — students return to the app because it nudges them.

---

## Phase 6 — Code Quality (impresses engineers who read the code)

These matter less for demos but significantly for recruiters who inspect the repo.

- [ ] **Break up `Schedule.jsx` (1,079 lines) into components**
  Extract: `<ScheduleToolbar>`, `<ScheduleSidebar>` (pie chart + legend), `<StudyBlockPopover>`, `<GenerateModal>`, `<ExportMenu>`. Each should be under 200 lines and in `frontend/src/components/schedule/`.

- [ ] **Break up `calendar.py` (1,042 lines) into services**
  Extract: `GoogleCalendarService` (OAuth + sync), `ICSService` (parsing + import), `ExportService` (iCal generation), `CalendarEventService` (CRUD). Keep the Flask route file as a thin router.

- [x] **Add 5 frontend component tests (Vitest + React Testing Library)**
  Installed vitest@1.6, @testing-library/react@14, jsdom. `npm test` runs 7 passing tests:
  - `homepage.test.jsx`: headline renders, CTAs exist, 3 how-it-works steps render
  - `syllabusUpload.test.jsx`: tabs render, submit disabled without input, Quick parse checkbox exists, submit enables after pasting text
  `vite.config.js` has `test: { environment: 'jsdom', globals: true, setupFiles: './src/test/setup.js' }`.

- [x] **Rate-limit the syllabus parse endpoint**
  `@limiter.limit("3/minute")` added to `POST /api/syllabus/parse` in `syllabus.py`.

- [x] **Add pagination to admin user list**
  `GET /api/admin/users` now accepts `limit` (max 500, default 50) and `offset` params. Returns `{ users, total, limit, offset }`.

- [x] **Replace `except Exception: pass` silent swallows**
  Added `import logging` and `logger = logging.getLogger(__name__)` to `assignments.py`. Silent `except Exception: pass` replaced with `except Exception as e: logger.warning("Failed to set is_completed fields: %s", e)`.

---

## Phase 7 — Performance (nice for real traffic, not urgent for portfolio)

These are not blockers but show engineering maturity if implemented.

- [ ] **Filter study times API by calendar view window**
  `backend/app/api/schedule.py:154–167`
  Pass `start_date`/`end_date` from the frontend's current calendar view. The params exist — just wire them up. Reduces payload from potentially thousands of rows to ~50.

- [ ] **Cap concurrent ICS sync to 2 at a time**
  `frontend/src/pages/Schedule.jsx:109–124`
  `Promise.all` on all stale sources fires N simultaneous HTTP requests on page load. Replace with a sequential or batched sync (e.g., chunks of 2 with `p-limit`).

- [ ] **Database connection pooling in API routes**
  Scheduling service uses SQLAlchemy (has pooling). API routes use raw `mysql.connector.connect()` per request. Switch API routes to use the SQLAlchemy session (already configured in `db/session.py`) or add `MySQLConnectionPool`.

---

## Completion Checklist Summary

| Phase | Items | Status |
|-------|-------|--------|
| Phase 1 — Embarrassments | 5 items | 4/5 done |
| Phase 2 — UI/UX Polish | 7 items | 6/7 done |
| Phase 3 — Homepage & Demo | 5 items | 2/5 done |
| Phase 4 — Mobile | 3 items | 2/3 done |
| Phase 5 — High-Impact Features | 4 items | 0/4 done |
| Phase 6 — Code Quality | 6 items | 4/6 done |
| Phase 7 — Performance | 3 items | 0/3 done |

**Minimum viable portfolio**: ✅ Phases 1 + 2 core items + homepage redesign are done.
**Strong portfolio**: Add one Phase 5 feature (burndown chart or drag-reschedule) + Phase 3 demo CTA.
