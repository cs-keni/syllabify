# Syllabify Data Architecture

This document describes how data is structured, how ownership and multi-user isolation work, the root cause of duplicate courses, and a roadmap for accounts, email, and settings.

---

## 1. Ownership Model (per user)

**Each user has their own isolated data.** Courses are not shared globally; they belong to a user through the following chain:

```
Users (id, username, ...)
  └── Terms (user_id) — one user has many terms (e.g. Winter 2026, Spring 2025)
        └── Courses (term_id) — one term has many courses (e.g. CS 433, CS 422)
              ├── Assignments (course_id)
              └── Meetings (course_id)
```

- **Users** table: One row per account.
- **Terms** table: `user_id` FK → each term belongs to exactly one user.
- **Courses** table: `term_id` FK → each course belongs to a term (and thus to that term’s user).
- **Assignments** and **Meetings** table: `course_id` FK → each belongs to one course.

All API endpoints that touch courses/assignments/meetings verify ownership via `Terms.user_id` before returning or modifying data. User A cannot see or edit User B’s courses.

---

## 2. Table Layout (current schema)

| Table | Key columns | Purpose |
|-------|-------------|---------|
| **Users** | `id`, `username`, `password_hash`, `security_setup_done` | Auth. Username used for login (no email yet). |
| **UserSecurityAnswers** | `user_id`, `question_text`, `answer_hash` | Security Q&A for password recovery. |
| **Terms** | `id`, `user_id`, `term_name`, `start_date`, `end_date`, `is_active` | Semesters/quarters per user. |
| **Courses** | `id`, `course_name`, `term_id`, `study_hours_per_week` | Courses within a term. |
| **Assignments** | `id`, `assignment_name`, `work_load`, `due_date`, `assignment_type`, `course_id` | Assignments within a course. `work_load` = 15‑min units (4 per hour). |
| **Meetings** | `id`, `course_id`, `day_of_week`, `start_time_str`, `end_time_str`, `location`, `meeting_type` | Meeting times (lectures, office hours, etc.). |
| **Schedules** | *(empty for now)* | Future: generated study schedules. |

---

## 3. Root Cause of Duplicate Courses

When you upload a syllabus and click **Confirm**, the app always **creates a new course** instead of updating an existing one.

Flow today:

1. **Upload page** → parse syllabus → **Review** → **Confirm**.
2. On Confirm, `saveCourse(token, payload)` is called.
3. `saveCourse` always calls `createCourse(termId, courseName, ...)`, which inserts a new row into `Courses`.
4. It then adds assignments and meetings to that new course.

So every confirmation results in a new course, even if you:

- Came from a specific course page (e.g. to “update” CS 433), or
- Uploaded the same syllabus multiple times.

**Result:** Multiple “CS 433” rows for the same term (e.g. 9 rows). Only the latest one has assignments; earlier ones are empty shells.

**Intended behavior (to be implemented):**

- When **creating** a course: upload from Dashboard or “Upload another” → create new course.
- When **updating** a course: upload from a Course page (with `courseId` in state) → update that course and replace its assignments/meetings instead of creating a new one.

### Cleaning up duplicate courses

To remove empty duplicate courses and keep only the one with assignments (e.g. course id 9 in your case):

```sql
-- Inspect first: which courses have assignments?
SELECT c.id, c.course_name, c.term_id,
       (SELECT COUNT(*) FROM Assignments a WHERE a.course_id = c.id) AS assignment_count
FROM Courses c
WHERE c.term_id = 2  -- adjust term_id to your Winter 2026 term
ORDER BY c.id;

-- Delete empty duplicates (courses with 0 assignments and 0 meetings)
DELETE c FROM Courses c
LEFT JOIN Assignments a ON a.course_id = c.id
LEFT JOIN Meetings m ON m.course_id = c.id
WHERE a.id IS NULL AND m.id IS NULL
  AND c.term_id = 2;

-- Or, to keep only course 9 and delete the rest for that term:
DELETE FROM Courses WHERE term_id = 2 AND id != 9;
-- (Assignments/Meetings cascade-delete when you delete a course, so the target course's data stays)
```

**Caution:** Run the `SELECT` first to confirm which IDs to keep. Back up your DB before bulk deletes.

---

## 4. Inspecting Your Data

To see what’s in the database, run these in Railway’s Query tab, MySQL Workbench, or via `mysql` CLI:

```sql
SELECT * FROM Users;
SELECT * FROM UserSecurityAnswers;
SELECT * FROM Terms;
SELECT * FROM Courses;
SELECT * FROM Assignments;
SELECT * FROM Meetings;
```

Or from the command line (replace host/port/user/password/db with your Railway values):

```bash
mysql -h YOUR_HOST -u root -p --port YOUR_PORT --protocol=TCP railway -e "
SELECT * FROM Users;
SELECT * FROM Terms;
SELECT * FROM Courses;
SELECT * FROM Assignments;
SELECT * FROM Meetings;
SELECT * FROM UserSecurityAnswers;
"
```

---

## 5. Minor Data Notes

- **4 meeting times parsed vs 3 stored:** The backend skips meetings when `day_of_week` is missing or too short, or when `start_time` / `end_time` are missing. One parsed meeting likely failed those checks.
- **`work_load` in Assignments:** Stored as 15‑minute units (`hours × 4`). Midterm 2h → 8, Homework 3h → 12. The UI shows hours as `work_load / 4`.

---

## 6. Roadmap: Accounts, Email, Settings

### 6.1 User accounts (registration)

- **Today:** Single hardcoded dev user (`syllabify-client`). Login validates against that user only.
- **Planned:** Registration API that inserts into `Users` and uses `username` (and eventually email) as unique identifiers. JWT continues to encode `user_id` for ownership checks.

### 6.2 Email for login and password recovery

- **Today:** `Users` has `username`, no `email`.
- **Planned:**
  - Add `email VARCHAR(255) NULL UNIQUE` to `Users`.
  - Optionally use email as primary login identifier (or support both username and email).
  - “Forgot password” flow: verify identity via security questions (already in `UserSecurityAnswers`) or via email link. Email-based reset would require:
    - Email sending (e.g. SendGrid, Mailgun) or a similar service.
    - Tokens for reset links (e.g. new table `PasswordResetTokens` or `user_id`, `token`, `expires_at`).

### 6.3 Settings

- **Today:** No user-specific settings table.
- **Planned:** Add `UserSettings` or a `settings` JSON column on `Users` for preferences such as:
  - Default study hours per week
  - Notification preferences
  - Timezone
  - Theme (if applicable)

---

## 7. Summary

| Topic | Status | Notes |
|-------|--------|-------|
| Multi-user isolation | ✅ Implemented | Via `Users` → `Terms` → `Courses`. |
| Duplicate courses | ❌ Bug | Every syllabus confirm creates a new course. Fix: update existing when `courseId` provided. |
| User registration | 🔜 Planned | Need signup API and optional email field. |
| Email for password recovery | 🔜 Planned | Add `email` to `Users` and implement reset flow. |
| User settings | 🔜 Planned | Add `UserSettings` or `settings` column. |
