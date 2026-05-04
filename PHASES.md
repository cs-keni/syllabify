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

- [x] **Keyboard shortcuts for core actions (`G` / `C` / `E`)**
  `Schedule.jsx` has `useEffect` keydown listener using `shortcutHandlersRef` (avoids stale closures). `G` triggers generate, `E` opens export. Documented in `ShortcutsOverlay` with a `SCHEDULE_SHORTCUTS` section.

- [x] **Upload step stepper allows jumping to future steps**
  Already implemented — `Upload.jsx` has `disabled={i > step || step === 2}` on step buttons.

---

## Phase 3 — Homepage & Demo Experience (first impressions)

The homepage is the front door for portfolio reviewers. Currently three text cards on white — nothing shows what the app actually does.

- [x] **Hero section with real visuals**
  Homepage now has a two-column hero: headline + CTA on the left, a CSS-rendered calendar mockup (colored study blocks, now-indicator, day headers) on the right. No image file needed.

- [x] **Feature comparison or "how it works" section**
  Three numbered step cards (01/02/03) with emoji icons and descriptions replace the plain text cards. A four-item feature grid below covers AI parsing, scheduling algorithm, Google Calendar sync, and live calendar.

- [x] **"Try the demo" CTA with pre-loaded sample data**
  `POST /api/auth/demo-login` creates/reuses a `demo` user and seeds 3 courses (CS 422, MATH 341, ENGL 202), 16 assignments, and meeting times. Homepage hero and bottom CTA both have "Try the demo →" buttons wired through `AuthContext.loginWithToken`.

- [x] **Onboarding tooltip sequence after first login**
  `OnboardingTooltip.jsx` — 3-step overlay (Welcome, Upload syllabus, Generate schedule) with progress dots, skip, and CTA buttons. State persisted to `localStorage` under `syllabify_onboarding_done`. Shows with 800ms delay after Dashboard mounts.

- [ ] **Add screenshots or GIF to README**
  The README describes the app well but has no visuals. GitHub profile visitors won't read 200 lines of text — a single annotated screenshot of the schedule page makes this instantly understandable.

---

## Phase 4 — Mobile (at minimum, make it not broken)

The app is essentially unusable on phones. This doesn't need to be perfect, but a recruiter checking it on mobile shouldn't see a broken layout.

- [x] **Default to `listWeek` or `timeGridDay` on narrow screens**
  `AppCalendar.jsx` now detects `window.innerWidth < 768` at module load. On mobile, `initialView` is `'listWeek'` and `editable`/`selectable` are both `false` (disabling drag).

- [x] **Navigation drawer on mobile**
  `Layout.jsx` — hamburger button visible `< md`, toggles `mobileMenuOpen`. Full slide-over drawer with nav links, profile, settings, logout. Closes on route change (pathname useEffect) and Escape key. `animate-slide-right` animation via custom Tailwind keyframe.

- [x] **Touch-friendly event interaction on mobile**
  `editable={!isMobile}` and `selectable={!isMobile}` are now passed to FullCalendar. Individual study events also have `editable: !isMobile` set.

---

## Phase 5 — High-Impact Features (separate "school project" from "real product")

Pick 1–2 of these to implement before the portfolio deadline. Each one alone is worth highlighting.

### 5a. Workload Burndown Chart

- [x] **Weekly study hours bar chart on Schedule page**
  `ScheduleSidebar.jsx` — bar chart using CSS/inline styles, grouped by ISO Monday week. Past weeks rendered dimmed (`opacity: 0.35`), future weeks in accent color. Tooltip shows week label and hours. `weeklyHours` computed in `Schedule.jsx` via `useMemo` and passed as props.

### 5b. Smart Rescheduling on Drag

- [x] **After dragging a study block, offer "Reschedule remaining blocks?"**
  `handleStudyTimeMove` in `Schedule.jsx` shows a 6-second `react-hot-toast` with "Block pinned. Re-optimize remaining?" button that calls `shortcutHandlersRef.current.generate()`.

### 5c. LLM Parse Mode Toggle + Feedback

- [x] **Show parse confidence in the review step**
  `ParsedDataReview.jsx` — low-confidence fields show an amber `⚠ Verify` badge inline. Triggered by `assignment.confidence < 0.7 || assignment.low_confidence === true`.

### 5d. Due-Date Email Reminders

- [x] **3-day and 1-day advance reminders for assignments**
  `backend/app/services/email_service.py` — SMTP-based send via `smtplib` with `SMTP_HOST/USER/PASS/FROM` env vars. `backend/app/api/reminders.py` — `POST /api/reminders/send` (cron-auth via `X-Cron-Secret` or admin JWT) queries due-soon assignments and sends per-user email summaries. Registered in `main.py`; `/api/auth/demo-login` bypasses maintenance mode.

---

## Phase 6 — Code Quality (impresses engineers who read the code)

These matter less for demos but significantly for recruiters who inspect the repo.

- [x] **Break up `Schedule.jsx` into components**
  Extracted to `frontend/src/components/schedule/`: `ScheduleToolbar`, `ScheduleSidebar` (pie chart + burndown + sources), `StudyBlockPopover`, `GenerateModal`, `ExportModal`. `Schedule.jsx` reduced from ~1,079 to 794 lines.

- [x] **Break up `calendar.py` into a service layer**
  `backend/app/services/google_calendar_service.py` — extracts `get_google_credentials`, `store_google_tokens`, `build_google_service`, `fetch_events_paginated`, `parse_google_event`, `upsert_google_event`, `sync_google_source`. `calendar.py` drops from 1,042 to 781 lines; no duplicate event-parse logic.

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

- [x] **Filter study times API by calendar view window**
  `Schedule.jsx` tracks `viewWindow` state via `onDatesSet` from `AppCalendar`. `fetchData` passes `viewWindow.start/end` as `startDate`/`endDate` to `getStudyTimes`. Reduces payload to the currently visible calendar window.

- [x] **Cap concurrent ICS sync to sequential**
  Auto-sync loop in `Schedule.jsx` replaced `Promise.all` with a sequential `for...of` loop. Each source awaits before the next fires — prevents thundering herd on page load.

- [x] **Database connection pooling in API routes**
  `backend/app/db/connection.py` — `MySQLConnectionPool` (pool_size via `MYSQL_POOL_SIZE` env var, default 5) with double-checked locking singleton. Falls back to direct connect if pool exhausted. `.env.example` documents `MYSQL_POOL_SIZE`.

---

## Completion Checklist Summary

| Phase | Items | Status |
|-------|-------|--------|
| Phase 1 — Embarrassments | 5 items | 4/5 done |
| Phase 2 — UI/UX Polish | 7 items | 7/7 done ✅ |
| Phase 3 — Homepage & Demo | 5 items | 4/5 done |
| Phase 4 — Mobile | 3 items | 3/3 done ✅ |
| Phase 5 — High-Impact Features | 4 items | 4/4 done ✅ |
| Phase 6 — Code Quality | 6 items | 6/6 done ✅ |
| Phase 7 — Performance | 3 items | 3/3 done ✅ |

**Remaining**: Phase 1 git-history `.env` audit (manual), Phase 3 README screenshots (in progress).
**Status**: All implementable items are complete. Only manual/asset tasks remain.
