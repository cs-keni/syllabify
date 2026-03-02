# Syllabify MVP — Implementation Plan

This document defines **what we implement ourselves** (without touching the scheduling engine or calendar export/import) and in what order. It is written so that an implementer can follow it step-by-step.

---

## 1. Scope and Exclusions

### 1.1 In Scope (This MVP)

- User registration (signup)
- Login against real users in database (not hardcoded dev user)
- Profile/settings: email (display name deferred)
- Admin interface: list users, disable account, reset security setup
- Preferences persistence (work hours, preferred days, max hours/day)
- Fix: Update existing course when re-uploading syllabus (avoid duplicates)
- **Course Dashboard** (enhanced Course page): view parsed syllabus content, add/remove/edit assignments, paste additional assignment text → AI parse → add to course
- Database schema updates for all of the above

### 1.2 Explicitly Excluded (Teammates' Work)

- **Scheduling engine** — Saint George. We do not modify `scheduling_service.py` or add `POST /api/schedule/generate`.
- **Calendar export** — Leon. We do not implement ICS generation or Google Calendar.
- **Calendar import** — Leon. Not in scope.
- **Google OAuth login** — Deferred until we have a solid username/password login system. Add later.

### 1.3 Dependencies

```
DB Schema → Registration → Login Refactor → Profile/Settings → Admin
                ↓                                    ↓
         (registration creates users)        (admin needs users)
```

---

## 2. Implementation Phases (Order)

| Phase | Description | Blocks |
|-------|-------------|--------|
| **1** | Database schema | Users (email, is_admin), UserPreferences |
| **2** | User registration | Backend + Frontend |
| **3** | Login refactor | Validate against DB; remove hardcoded dev user |
| **4** | Profile / settings | Email; GET/PUT /api/users/me |
| **5** | Admin interface | Admin API + Admin page (protected) |
| **6** | Preferences persistence | Backend + wire Preferences UI |
| **7** | Fix update-course flow | Upload from Course page → update, not create |
| **8** | Course Dashboard | Assignment CRUD, paste + parse snippet, enhanced Course page |

---

## 3. Phase 1: Database Schema

### 3.1 Goal

Add columns and tables needed for registration, profile, admin, and preferences. All changes must be additive or backward-compatible so existing data and code continue to work.

### 3.2 How to Run Migrations

Run SQL against your Railway MySQL (Query tab, MySQL Workbench, or `mysql` CLI). Execute each statement. If you see "Duplicate column name" or "Duplicate key", that column/table already exists—skip that statement. Run migrations in order: 003, then 004.

### 3.3 Changes

#### 3.3.1 Users table

Add columns via migration (do not drop/recreate):

```sql
-- Migration: docker/migrations/003_user_registration.sql
ALTER TABLE Users ADD COLUMN email VARCHAR(255) NULL UNIQUE;
ALTER TABLE Users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;
ALTER TABLE Users ADD COLUMN is_disabled BOOLEAN DEFAULT FALSE;
```

- `email`: Optional at registration. User can add/edit in settings. UNIQUE so we can use it for password recovery later.
- `is_admin`: For protecting admin routes. Default FALSE.
- `is_disabled`: Admin can disable accounts; disabled users cannot log in. Default FALSE.

**Validation:** Email format (basic regex) if provided. Max 255 chars.

#### 3.3.2 UserPreferences table

```sql
CREATE TABLE IF NOT EXISTS UserPreferences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    work_start VARCHAR(5) NOT NULL DEFAULT '09:00',
    work_end VARCHAR(5) NOT NULL DEFAULT '17:00',
    preferred_days VARCHAR(50) NOT NULL DEFAULT 'MO,TU,WE,TH,FR',
    max_hours_per_day INT NOT NULL DEFAULT 8,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
);
```

- `preferred_days`: Comma-separated iCal codes (MO,TU,WE,TH,FR,SA,SU).
- `work_start`, `work_end`: "HH:MM" format.
- One row per user. Create on first fetch if missing.

### 3.3 Acceptance Criteria

- [ ] Migration runs without error on existing DB.
- [ ] Existing Users rows still valid (new columns nullable/default).
- [ ] `UserPreferences` created; no rows yet (created lazily).

---

## 4. Phase 2: User Registration

### 4.1 Goal

Users can create an account with username and password. No email required at signup; they can add it later in settings.

### 4.2 Backend

#### 4.2.1 New endpoint: `POST /api/auth/register`

**Request body (JSON):**

```json
{
  "username": "alice",
  "password": "securePassword123"
}
```

**Validation:**

- `username`: Required. 3–50 chars. Alphanumeric + underscore only (regex: `^[a-zA-Z0-9_]{3,50}$`). Trim whitespace.
- `password`: Required. Min 8 chars. (No complexity rules for MVP; add later if needed.)
- Check `username` is unique (query `Users`).

**On success:**

1. Hash password with bcrypt (reuse `hash_password` from auth.py).
2. Insert: `INSERT INTO Users (username, password_hash, security_setup_done, email, is_admin, is_disabled) VALUES (%s, %s, FALSE, NULL, FALSE, FALSE)`. (Omit is_disabled if column has DEFAULT; it will default to FALSE.)
3. Return: `{"id": 123, "username": "alice", "security_setup_done": false}`.
4. Do **not** auto-login. User must go to login page.

**On failure:**

- 400: `{"error": "username already taken"}` or `{"error": "invalid username"}` / `{"error": "password must be at least 8 characters"}`.
- 409 for duplicate username if you prefer that status.

#### 4.2.2 Files to touch

- `backend/app/api/auth.py`: Add `register` route.
- Reuse `get_db`, `hash_password` from same file.

### 4.3 Frontend

#### 4.3.1 Registration page

- **Route:** `/register` (new).
- **Form fields:** Username, Password, Confirm Password (client-side match).
- **Link:** From Login page: "Don't have an account? Sign up" → `/register`.
- **On submit:** `POST /api/auth/register` with `{ username, password }`. On success: show "Account created. Log in." and redirect to `/login` (or auto-navigate).
- **On error:** Display server error message (e.g. "Username already taken").

#### 4.3.2 Files to touch

- `frontend/src/pages/Register.jsx` (new).
- `frontend/src/App.jsx`: Add route for `/register`.
- `frontend/src/api/client.js`: Add `register(username, password)`.
- `frontend/src/pages/Login.jsx`: Replace "create an account later" text with link to `/register`.

### 4.4 Seed admin user (manual or migration)

After registration works, we need at least one admin. Options:

- **Option A:** Run a one-off SQL: `UPDATE Users SET is_admin = TRUE WHERE username = 'syllabify-client';` (if dev user still exists).
- **Option B:** Add a seed script or migration that inserts an admin user if none exists.
- **Option C:** First registered user becomes admin (simplest for demo; not for production).

Recommendation: Option A for dev; document in MVP that "promote to admin" can be done via SQL or future admin UI.

### 4.5 Acceptance Criteria

- [ ] `POST /api/auth/register` creates user in DB.
- [ ] Duplicate username returns 400 with clear message.
- [ ] Invalid username/password returns 400.
- [ ] Frontend: Register page works; success → redirect to login.
- [ ] New user can log in with username/password after registration.

---

## 5. Phase 3: Login Refactor

### 5.1 Goal

Login validates against the `Users` table (username + password_hash), not the hardcoded dev user. The dev user can remain in DB for backward compatibility but is no longer special-cased.

### 5.2 Backend

#### 5.2.1 Modify `POST /api/auth/login`

**Current behavior:** Only accepts `syllabify-client` / `ineedtocutmytoenails422`; ensures dev user exists.

**New behavior:**

1. Accept any username/password.
2. Query: `SELECT id, username, password_hash, security_setup_done, is_admin FROM Users WHERE username = %s AND (is_disabled = FALSE OR is_disabled IS NULL)`.
3. If no row: return 401 `{"error": "invalid credentials"}`.
4. If row found: `check_password(password, password_hash)`.
5. If password wrong: return 401.
6. If correct: return JWT + `{"token": "...", "username": "...", "security_setup_done": bool}`.
7. Remove `ensure_dev_user` from login flow. (Keep it only if you want to seed dev user on first deploy; optional.)

#### 5.2.2 Dev user handling

- Remove the hardcoded check (`if username != DEV_USERNAME or password != DEV_PASSWORD`). Login should work for any user in DB.
- **Optional:** Keep `ensure_dev_user` and call it only when login succeeds with `syllabify-client` / `ineedtocutmytoenails422` and no user exists yet—so first-time dev login still creates the user. Or: remove `ensure_dev_user` entirely and add a seed to migration 003 that inserts the dev user if not exists. Recommendation: Remove from login flow; document that for dev you can run `INSERT INTO Users (username, password_hash, security_setup_done) SELECT 'syllabify-client', ...` or use the Register page.

### 5.3 Frontend

- No change required. Login page already sends `username` and `password`; API contract stays the same (token, username, security_setup_done).
- Remove dev-specific placeholder text if any ("syllabify-client" in placeholder).

### 5.4 Acceptance Criteria

- [ ] Login with registered user works.
- [ ] Login with wrong password returns 401.
- [ ] Login with nonexistent username returns 401.
- [ ] JWT contains `sub` (user id) and `username`.
- [ ] Security setup redirect still works for new users.

---

## 6. Phase 4: Profile / Settings

### 6.1 Goal

Logged-in users can view and update their profile: email (optional). Stored in `Users`. Display name deferred.

### 6.2 Backend

**Blueprint:** Create `backend/app/api/users.py` with `bp = Blueprint("users", __name__, url_prefix="/api/users")`. Register in `main.py`: `app.register_blueprint(users_bp)`.

#### 6.2.1 New endpoint: `GET /api/users/me`

- **Auth:** Required (JWT).
- **Response:** `{"id": 1, "username": "alice", "email": "alice@example.com", "security_setup_done": true}`.
- **Logic:** `decode_token` → `SELECT id, username, email, security_setup_done FROM Users WHERE id = %s`.

#### 6.2.2 New endpoint: `PUT /api/users/me`

- **Auth:** Required.
- **Request body:** `{"email": "alice@example.com"}` or `{"email": null}` to clear.
- **Validation:** If email is non-null and non-empty: valid format (basic regex), max 255 chars, unique (check no other user has it: `SELECT id FROM Users WHERE email = %s AND id != %s`). If email is "" or null, set to NULL.
- **Logic:** `UPDATE Users SET email = %s WHERE id = %s`.
- **Response:** Same shape as `GET /api/users/me`.

#### 6.2.3 Files to touch

- `backend/app/api/users.py` (new blueprint).
- `main.py`: `from app.api.users import bp as users_bp` and `app.register_blueprint(users_bp)`.
- Import `decode_token, get_db` from `app.api.auth` in users.py.

### 6.3 Frontend

#### 6.3.1 Profile / Account settings

- **Option A:** New page `/app/profile` or `/app/settings` with Account section.
- **Option B:** Add an "Account" section to the existing Preferences page.

Recommendation: **Add "Account" section to Preferences** for MVP. Sections: Account (email), Study preferences (work hours, days) — the latter wired in Phase 6.

**Account section fields:**

- Email (optional, type="email", placeholder "you@example.com").
- Read from `GET /api/users/me` on load (or from `getProfile(token)`).
- "Save" button for Account section → `PUT /api/users/me` with `{ email }`.
- Show success toast ("Profile saved") or error toast on failure.

#### 6.3.2 Extend `GET /api/auth/me` (for Phase 5)

- Add `is_admin` to `me` response now so Layout can show admin link later. Query: `SELECT security_setup_done, is_admin FROM Users WHERE id = %s`. Return `{ username, security_setup_done, is_admin }`.
- **AuthContext:** Update `loadUser` so `setUser({ username: data.username, is_admin: data.is_admin })`. Update `login` callback similarly.

### 6.4 Acceptance Criteria

- [ ] `GET /api/users/me` returns current user's profile.
- [ ] `PUT /api/users/me` updates email.
- [ ] Duplicate email (another user) returns 400.
- [ ] Frontend: Email field in Preferences/Account; persists on save.

---

## 7. Phase 5: Admin Interface

### 7.1 Goal

Admins can list users, disable an account, and reset a user's security setup status. Admin routes are protected by `is_admin` check.

### 7.2 Backend

**Blueprint:** Create `backend/app/api/admin.py` with `bp = Blueprint("admin", __name__, url_prefix="/api/admin")`. Register in `main.py`.

#### 7.2.1 Helper: `require_admin`

```python
def require_admin():
    """Returns (user_id, username) or None. Use at start of each admin route."""
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return None
    user_id = int(payload.get("sub"))
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, username FROM Users WHERE id = %s AND is_admin = 1", (user_id,))
        row = cur.fetchone()
        return (row["id"], row["username"]) if row else None
    finally:
        conn.close()
```

- At start of each admin route: `admin_info = require_admin(); if not admin_info: return jsonify({"error": "forbidden"}), 403`.

#### 7.2.2 Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /api/admin/users | Admin | List all users. Return `{users: [{id, username, email, security_setup_done, is_admin, is_disabled}]}`. |
| PUT | /api/admin/users/:id/disable | Admin | Body: `{"disabled": true}` or `{"disabled": false}`. Set `is_disabled` for that user. |
| PUT | /api/admin/users/:id/reset-security | Admin | Set `security_setup_done = FALSE` for that user. Clear their UserSecurityAnswers. |

**Disable behavior:** If `is_disabled` is True, login should reject. Add check in login: `SELECT ... WHERE username = %s AND (is_disabled = FALSE OR is_disabled IS NULL)`.

(`is_disabled` is added in Phase 1 migration.)

#### 7.2.3 Files to touch

- `backend/app/api/admin.py` (new blueprint).
- `main.py`: Register admin blueprint.
- `auth.py`: Add `is_disabled` check in login.

### 7.3 Frontend

#### 7.3.1 Admin page

- **Route:** `/app/admin` (inside Layout, so requires auth).
- **Nav link:** Add "Admin" to nav items in `Layout.jsx`, but only render when `user?.is_admin === true`.
- **Page:** `frontend/src/pages/Admin.jsx`. Table: id, username, email, security_setup_done, is_disabled. Buttons: "Disable" / "Enable" (toggle), "Reset security".
- **App.jsx:** Add `<Route path="admin" element={<Admin />} />` under the `/app` Layout.

### 7.4 Acceptance Criteria

- [ ] Non-admin receives 403 on admin endpoints.
- [ ] Admin can list users.
- [ ] Admin can disable user; disabled user cannot log in.
- [ ] Admin can reset security setup; user must redo security Q&A on next login.
- [ ] Admin link only visible to admins.

---

## 8. Phase 6: Preferences Persistence

### 8.1 Goal

Work hours, preferred days, and max hours per day from Preferences page are stored in `UserPreferences` and loaded when the user opens Preferences.

### 8.2 Backend

#### 8.2.1 Endpoints (add to users blueprint)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /api/users/me/preferences | JWT | Return `{work_start, work_end, preferred_days, max_hours_per_day}`. If no row exists, INSERT default row and return it. |
| PUT | /api/users/me/preferences | JWT | Body: `{work_start?, work_end?, preferred_days?, max_hours_per_day?}`. Update row; create if none. |

**Preferred days:** Backend stores comma-separated iCal: "MO,TU,WE,TH,FR". Frontend can send `["MO","TU","WE","TH","FR"]` or "MO,TU,WE,TH,FR". Normalize to string for DB.

### 8.3 Frontend

- **Preferences.jsx:** On mount, call `getPreferences(token)`. Populate work_start, work_end, preferred_days (checkboxes), max_hours_per_day (slider).
- **Day mapping:** Mon→MO, Tue→TU, Wed→WE, Thu→TH, Fri→FR, Sat→SA, Sun→SU.
- **Checkboxes:** Store as array of iCal codes; join to "MO,TU,WE" for PUT.
- On "Save" (or form submit), call `updatePreferences(token, prefs)` and show toast.

### 8.4 Acceptance Criteria

- [ ] Preferences load from DB.
- [ ] Saving updates DB and persists across sessions.
- [ ] New user gets defaults until they change and save.

---

## 9. Phase 7: Fix Update-Course Flow

### 9.1 Goal

When the user navigates from a Course page to Upload (with `courseId` in `location.state`), the Confirm step should **update** that course (replace assignments and meetings) instead of creating a new course.

### 9.2 Current Behavior

- `ParsedDataReview` onConfirm always calls `saveCourse(token, payload)`, which calls `createCourse()` → new course every time.

### 9.3 New Behavior

- If `courseId` is present (from `state?.courseId`): Call `updateCourse(courseId, payload)` instead of `saveCourse(payload)`.
- `updateCourse` should: (1) Update course name/study_hours if changed; (2) Delete existing assignments for that course; (3) Delete existing meetings for that course; (4) Bulk-insert new assignments and meetings from payload.

### 9.4 Backend

#### 9.4.1 New or modified endpoint

**Option A:** `PUT /api/courses/:id` with body `{ course_name?, study_hours_per_week?, assignments, meeting_times }`.

- Replace assignments: DELETE existing, INSERT new (or use a bulk replace helper).
- Replace meetings: Already supported by `POST /api/courses/:id/meetings` (it deletes existing first per current code).

**Option B:** Reuse existing:
- `PUT` for course metadata if you add it.
- `POST /api/courses/:id/assignments` — currently appends. We need **replace** behavior. So either:
  - Add `replace=true` query param to delete first, or
  - Create `PUT /api/courses/:id/assignments` that replaces.

**Implementation:** Add `PUT /api/courses/:id` in `backend/app/api/courses.py`:

1. Verify ownership via `_owns_course(cur, course_id, user_id)`.
2. Parse body: `{ course_name?, study_hours_per_week?, assignments, meeting_times }`. assignments and meeting_times are required (arrays, can be empty).
3. Update course: `UPDATE Courses SET course_name = %s, study_hours_per_week = %s WHERE id = %s` (use payload values or keep existing).
4. Delete assignments: `DELETE FROM Assignments WHERE course_id = %s`.
5. Insert new assignments (same logic as `add_assignments`—work_load from hours*4, etc.).
6. Delete meetings: `DELETE FROM Meetings WHERE course_id = %s`.
7. Insert new meetings (same logic as `add_meetings`).
8. Return 200 with updated course info.

### 9.5 Frontend

- **Upload.jsx:** In `ParsedDataReview` onConfirm (around line 135), change the logic:
  - If `state?.courseId` is present (user came from Course page): call `updateCourse(token, state.courseId, payload)` instead of `saveCourse`. Still `setCreatedCourseId` is irrelevant when updating—we use existing courseId for "View course" navigation.
  - Else: call `saveCourse(token, payload)` as before.
- **Important:** `courseId` in the component comes from `state?.courseId ?? createdCourseId`. We branch on `state?.courseId` specifically, because after a new save, `createdCourseId` gets set and we don't want to "update" a freshly created course.

### 9.6 Acceptance Criteria

- [ ] Upload from Course page updates that course; no new course created.
- [ ] Upload from Dashboard ("Upload another") still creates new course.
- [ ] Assignments and meetings are replaced, not appended.

---

## 10. Phase 8: Course Dashboard

### 10.1 Goal

After a course is created, users open the **Course page** (serving as the "Course Dashboard") and see:
1. Parsed syllabus content (assignments, meetings) mapped to that course
2. Ability to **add, remove, edit** assignments (since syllabi often omit details)
3. A **"Paste additional assignment info"** section: user pastes text → AI parses → user reviews and adds parsed items to the course (or edits manually)

The Course page (`/app/courses/:courseId`) already exists and shows assignments. We enhance it with inline edit/remove, an "Add assignment" form, and the paste+parse section.

### 10.2 Backend

#### 10.2.1 New endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| PATCH | /api/assignments/:id | JWT | Update single assignment. Body: `{assignment_name?, due_date?, hours?, type?}` (hours → work_load as hours×4). Verify ownership via assignment → course → term → user. |
| DELETE | /api/assignments/:id | JWT | Delete single assignment. Verify ownership. |
| POST | /api/courses/:id/assignments | JWT | *(existing)* Bulk add. Reuse for "Add from parsed" and "Add single" (send array of 1). |

**Placement:** Add `backend/app/api/assignments.py` with `bp = Blueprint("assignments", __name__, url_prefix="/api/assignments")`. Register in `main.py`. Import `decode_token, get_db` from auth. Create helper `_owns_assignment(cur, assignment_id, user_id)` that does: `SELECT a.id FROM Assignments a JOIN Courses c ON c.id = a.course_id JOIN Terms t ON t.id = c.term_id WHERE a.id = %s AND t.user_id = %s`.

**PATCH /api/assignments/:id:** If not owned, 404. Update only provided fields. Accept `hours` in body; convert to `work_load` = hours × 4. Return updated assignment.

**DELETE /api/assignments/:id:** If not owned, 404. `DELETE FROM Assignments WHERE id = %s`. Return `{"ok": true}`.

#### 10.2.2 Parse for snippets

- Reuse existing `POST /api/syllabus/parse` with `{"text": "..."}`. It works on pasted text (full syllabus or snippet). No backend change.
- Frontend sends pasted text; receives `{assignments: [...], meeting_times: [...]}`. We only use `assignments` for the "add from parsed" flow.

### 10.3 Frontend

#### 10.3.1 Course page structure (Course.jsx → CourseDashboard.jsx or enhance in place)

**Sections:**
1. **Header** — Course name, term, "Upload syllabus", "Delete" (unchanged).
2. **Assignments** — List with **edit** and **remove** buttons per row. Inline edit or modal.
3. **Add assignment** — Small form or expandable: name, due date, hours, type. Submit → `POST /api/courses/:id/assignments` with `{assignments: [one item]}`.
4. **Paste & parse** — Collapsible section: textarea, "Parse" button, loading state, then show parsed assignments list. User can check which to add, edit any before adding, then "Add selected" → `POST /api/courses/:id/assignments`.

#### 10.3.2 Assignment row (editable)

- Display: name, due, hours, type.
- **Edit** — Click to toggle edit mode (inline fields) or open a small modal. Save → `PATCH /api/assignments/:id`.
- **Remove** — Trash icon. Confirm (or soft confirm). Delete → `DELETE /api/assignments/:id`. Refresh course data.

#### 10.3.3 Add assignment (manual)

- Fields: name (required), due date (optional, date input), hours (default 3), type (dropdown: assignment, midterm, final, quiz, project, participation).
- "Add" button → `addAssignments(courseId, [{name, due, hours, type}])`, then refresh course.

#### 10.3.4 Paste & parse section

- Heading: "Add from pasted text"
- Textarea: placeholder "Paste assignment details (e.g. 'Homework 3 due Mar 15, 4 hours')…"
- "Parse" button → `parseSyllabus(token, { text })`. Show loading.
- On success: Render parsed `assignments` in a list. Each item: checkbox (select to add), editable fields (name, due, hours, type).
- "Add selected" → Collect checked/edited items, `addAssignments(courseId, items)`, refresh, clear section.
- "Cancel" → Clear textarea and parsed results.

#### 10.3.5 Meetings (optional for Phase 8)

- Course page may show meeting times. Edit/remove for meetings can be a follow-up. Focus on assignments first.

### 10.4 API client additions

```javascript
// Phase 8
export async function updateAssignment(token, assignmentId, { assignment_name, due_date, hours, type }) { ... }
export async function deleteAssignment(token, assignmentId) { ... }
// addAssignments already exists
// parseSyllabus already exists (used for paste+parse)
```

### 10.5 Files to touch

- `backend/app/api/courses.py` — Add routes for assignments by id. Or create `backend/app/api/assignments.py` with PATCH/DELETE for `/api/assignments/:id`. Simpler: add in courses.py as `/api/courses/:course_id/assignments/:assignment_id` for PATCH/DELETE, so ownership is clear. Actually, assignment id is global—we need to verify assignment belongs to a course the user owns. So route `PATCH /api/assignments/:id` is fine; we look up assignment, get course_id, then verify term ownership.
- `frontend/src/pages/Course.jsx` — Enhance with edit, remove, add, paste+parse UI.
- `frontend/src/api/client.js` — Add `updateAssignment`, `deleteAssignment`.

### 10.6 Acceptance Criteria

- [ ] User can edit an assignment (name, due, hours, type) inline or via modal.
- [ ] User can remove an assignment.
- [ ] User can add a new assignment manually.
- [ ] User can paste text, click Parse, see parsed assignments, edit them, and add selected ones to the course.
- [ ] Course page reflects all changes after each operation.

---

## 11. API Client Additions (Summary)

Add to `frontend/src/api/client.js`:

```javascript
// Phase 2
export async function register(username, password) { ... }

// Phase 4
export async function getProfile(token) { ... }
export async function updateProfile(token, { email }) { ... }

// Phase 5
export async function getAdminUsers(token) { ... }
export async function disableUser(token, userId) { ... }
export async function resetUserSecurity(token, userId) { ... }

// Phase 6
export async function getPreferences(token) { ... }
export async function updatePreferences(token, prefs) { ... }

// Phase 7
export async function updateCourse(token, courseId, payload) { ... }

// Phase 8
export async function updateAssignment(token, assignmentId, { assignment_name, due_date, hours, type }) { ... }
export async function deleteAssignment(token, assignmentId) { ... }
```

---

## 12. Migration Files Summary

| File | Purpose |
|------|---------|
| `docker/migrations/003_user_registration.sql` | Users: email, is_admin, is_disabled |
| `docker/migrations/004_user_preferences.sql` | Create UserPreferences table |

---

## 13. Routing Summary

| Path | Auth | Description |
|------|------|--------------|
| /register | No | Registration form |
| /login | No | Login form |
| /app | Yes | Main app layout |
| /app/courses/:courseId | Yes | Course Dashboard (assignments, edit, paste+parse) |
| /app/preferences | Yes | Preferences + Account (email) |
| /app/admin | Yes (admin) | Admin user management |

---

## 14. Suggested Implementation Order

1. **Phase 1** — Run migrations. Verify DB.
2. **Phase 2** — Registration (backend + frontend). Manual test: create account.
3. **Phase 3** — Login refactor. Remove dev hardcoding. Test with new user.
4. **Phase 4** — Profile/settings (email). Test update.
5. **Phase 5** — Admin. Seed one admin; test admin flow.
6. **Phase 6** — Preferences persistence.
7. **Phase 7** — Update-course flow.
8. **Phase 8** — Course Dashboard (assignment CRUD, paste + parse).

Each phase is independently testable. Phase 8 can start after Phase 7 (or in parallel with 4–6). Do not skip Phase 1; all others depend on schema.

---

## 15. Out of Scope (Deferred)

- Google OAuth login
- Email verification
- Password reset (via email)
- Password change (user-initiated)
- Admin: bulk operations, search/filter
- Maintenance mode toggle
