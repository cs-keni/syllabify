# Admin Capabilities & Roadmap

What admins can do today, and ideas for future admin features.

**Status: In progress.** Current + **High Priority** + **Medium** (bulk, user creation, maintenance) + **Lower** (export, system stats) are **complete**. Audit log and remaining Lower items (impersonate, rate limit, feature flags) are **not yet implemented**. Use checkboxes below to track: `[x]` = done, `[ ]` = todo.

---

## Current Admin Functionality ✅ (Complete)

Admins access the **Admin** page (`/app/admin`) from the nav bar. The Admin UI uses a distinct control-panel aesthetic (slate/indigo) separate from the client-facing green theme.

### What Admins Can Do (That Clients Cannot)

| Action | Description | API |
|--------|-------------|-----|
| **List all users** | View every user: id, username, email, security setup status, admin status, disabled status | `GET /api/admin/users` |
| **Disable / Enable account** | Disable a user so they cannot log in; re-enable when needed | `PUT /api/admin/users/:id/disable` |
| **Grant / revoke admin** | Promote a client to admin, or demote an admin to client. Cannot change your own status. | `PUT /api/admin/users/:id/set-admin` |
| **Reset security setup** | Clear a user's security Q&A; they must redo security setup on next login | `PUT /api/admin/users/:id/reset-security` |

### What Clients Can Do (Same as Admins)

- Register, login, change password in Preferences
- Upload syllabi, create courses, manage assignments
- Use schedule, preferences, and all other app features

Admins are regular users with extra permissions; they can use the full app plus the Admin page.

### Access Control

- **Admin page**: Only visible in nav when `user.is_admin === true`
- **Admin API**: All `/api/admin/*` routes return `403 Forbidden` for non-admins
- **Admin designation**: Via `Users.is_admin` in DB or `ADMIN_USERNAMES` env var (comma-separated usernames, always treated as admin)

---

## Future Admin Ideas

Prioritized by impact and effort. Add new ideas here as we discover them. `[x]` = implemented, `[ ]` = todo.

### High Priority

| Status | Idea | Description | Effort |
|--------|------|-------------|--------|
| [x] | **Search / filter users** | Search by username or email; filter by admin/disabled/security status | Medium |
| [x] | **View user details** | Expand row or modal: when user registered, last login (if we track it), their terms/courses count | Medium |
| [x] | **Admin password reset** | Allow admin to set a temporary password for a user (e.g. after account recovery) | Low |

### Medium Priority

| Status | Idea | Description | Effort |
|--------|------|-------------|--------|
| [x] | **Bulk actions** | Select multiple users → disable all, reset security for all | Medium |
| [ ] | **Audit log** | Log admin actions (who disabled whom, when; who promoted whom) for accountability | High |
| [x] | **Maintenance mode** | Toggle "maintenance" so only admins can access the app; show message to clients | Medium |
| [x] | **User creation** | Create a new user (e.g. for class roster) with temp password; user must change on first login | Low |

### Lower Priority

| Status | Idea | Description | Effort |
|--------|------|-------------|--------|
| [x] | **System stats dashboard** | Total users, new signups this week, active courses, storage usage | Medium |
| [x] | **Export users** | CSV/JSON export of user list for reporting | Low |
| [ ] | **Impersonate user** | Admin logs in as another user to debug issues (with clear UI indicator) | High (security-sensitive) |
| [ ] | **Rate limit / abuse view** | See failed login attempts, flag suspicious activity | High |
| [ ] | **Feature flags** | Toggle features per user or globally (e.g. beta parser, new schedule UI) | High |

### From SRS / MVP (Reference)

- **SRS Use Case 7**: Search, filter, sort users; view details; disable; reset security ✅ (partial)
- **SRS Use Case 8**: Maintenance mode; display maintenance message to students
- **MVP Phase 5**: List, disable, reset security ✅ (complete; set-admin added later)
- **final-progress-report**: Maintenance mode (future)

---

## Brainstorm — More Ideas

Raw brainstorm. No prioritization—add whatever sparks interest. **All items below: not implemented.**

### User & Account Management

- **Delete user** — Permanently remove a user and their data (terms, courses, assignments). Require confirmation + "type DELETE to confirm".
- **Merge accounts** — Combine two accounts (e.g. duplicate signups); pick primary, migrate data, optionally disable secondary.
- **Lock account** — Temporary lock (e.g. 24h) vs permanent disable. Auto-unlock after duration.
- **Email verification toggle** — Require verified email before full access; admins can mark "verified" manually.
- **Force password change** — Flag user so they must change password on next login (e.g. after breach).
- **Ban by email domain** — Block signups from certain domains (e.g. disposable email providers).
- **Invite-only mode** — Only users with invite codes can register; admins generate and revoke codes.
- **Bulk import users** — CSV upload: username, email, temp password. Auto-create accounts for a class roster.
- **Account age / inactivity** — Show "created 3 months ago", "last active 2 weeks ago". Option to auto-disable after N months inactive.
- **Custom roles** — Beyond admin/client: e.g. "moderator" (can view users, no disable), "support" (limited actions).

### Security & Auth

- **Session management** — View or revoke a user's active sessions / tokens. Force logout everywhere.
- **2FA enforcement** — Require 2FA for admins, or for all users. Show who has 2FA enabled.
- **IP allowlist / blocklist** — Restrict admin login to certain IPs; block abusive IPs globally.
- **Login attempt history** — Per-user: failed logins, IP, timestamp. Detect brute-force.
- **Security alerts** — Email admins on suspicious activity (many failed logins, new admin granted, etc.).
- **API key management** — If we add API access: admins create/revoke keys; view usage per key.
- **OAuth / SSO config** — If we add Google/GitHub login: admins toggle providers, set allowed domains.

### Content & Data

- **View user's courses** — Drill into a user: see their terms, courses, assignment counts. Read-only.
- **Anonymized data export** — Export aggregate stats (no PII) for research or reporting.
- **Data retention policy** — Auto-delete users/courses older than N months. Admins set policy.
- **Restore deleted** — Soft-delete with restore window (e.g. 30 days). Admin can restore.
- **Parse logs** — View parse attempts, success/fail rates, which syllabi triggered errors.
- **Storage quota** — Per-user limits on uploaded files. Admins set or override quota.
- **Clear user data** — Wipe a user's courses/assignments but keep account (GDPR-style right to erase data).

### System & Operations

- **Health check dashboard** — DB latency, API response times, disk usage, memory. Green/yellow/red.
- **Scheduled maintenance window** — Set "maintenance from 2am–4am Saturday"; show banner to users.
- **Kill switch** — Emergency: disable all non-admin logins instantly (e.g. during incident).
- **Read-only mode** — Users can view but not edit (e.g. during deploy). Admins still full access.
- **Env var viewer** — Safely show which env vars are set (mask secrets). Help debug config.
- **Database backup status** — Last backup time, size. Trigger manual backup (if applicable).
- **Cache purge** — Clear CDN/cache if we add caching. Or "refresh all schedules".
- **Log viewer** — Tail application logs (errors, requests). Filter by user, endpoint, level.
- **Version / deploy info** — Show current app version, last deploy time. "New version available" for admins.

### Communication & Notifications

- **Announcement banner** — Admin sets a site-wide banner (e.g. "Syllabify will be down Saturday 2–4am").
- **Broadcast email** — Send email to all users or a segment (e.g. "users who signed up this term").
- **In-app announcements** — Dismissible notice that shows to all users until expiry.
- **Contact users** — Form to email a specific user (e.g. support reply). Log that admin contacted them.

### Parser & Upload

- **Parser config** — Tweak parsing thresholds, date formats, assignment type mappings. A/B test.
- **Blocklist certain files** — Reject uploads matching pattern (e.g. .exe, huge files).
- **Upload limits** — Max file size, max files per user. Admins override per user if needed.
- **Re-parse queue** — Queue failed or low-confidence parses for manual or batch re-parse.
- **Ground truth / test suite** — Admin uploads known syllabi; run parser, compare output. Quality tracking.

### Analytics & Reporting

- **Signup funnel** — Registrations over time, drop-off at security setup, completion rate.
- **Active users** — DAU/WAU/MAU. Retention curves.
- **Course/assignment counts** — Total courses, assignments, avg per user. Growth over time.
- **Parse success rate** — % of uploads that parse successfully. By file type, by time.
- **Error rate dashboard** — 4xx/5xx by endpoint. Spike detection.
- **Export report** — Scheduled or on-demand: user list, activity summary, etc. Email to admin.

### UX & Feature Control

- **Feature flags** — Toggle features globally or per user: "new schedule UI", "beta parser", "dark mode default".
- **A/B test assignment** — Assign users to experiment groups; track conversion.
- **Disable registration** — Close signups. Show "invite only" or "contact admin".
- **Beta tester list** — Mark users as beta; they see experimental features first.
- **Custom onboarding** — Different first-time flows per segment (e.g. instructors vs students).
- **Hide nav items** — Per deployment: hide "Upload" or "Schedule" if not ready yet.

### Compliance & Legal

- **GDPR export** — One-click "export all my data" for a user. Admin triggers on behalf of user.
- **Account deletion requests** — Queue of users who requested deletion. Admin approves/executes.
- **Data processing log** — Who accessed what data, when. For compliance audits.
- **Cookie / consent** — If we add tracking: admins configure consent banners, required vs optional.

### Nice-to-Haves

- **Admin activity feed** — "Kenny disabled user X at 2:34pm". Real-time or recent.
- **Admin notes on user** — Freeform note (e.g. "Contacted about duplicate account"). Only admins see.
- **Tags / labels** — Tag users: "VIP", "beta", "issue reported". Filter by tag.
- **Quick actions** — Keyboard shortcuts in admin (e.g. `d` to disable selected user).
- **Admin dark mode only** — Force admin UI to dark theme for consistency.
- **Multi-admin coordination** — "Admin X is viewing this user" to avoid conflicting edits.
- **Undo** — Undo last admin action (disable, etc.) within N seconds.
- **Scheduled actions** — "Disable user X at end of semester" (cron or queue).
- **Approve registrations** — New users pending until admin approves; or auto-approve with optional manual review queue.
- **Usage quotas** — Limit parses or API calls per user per day; admins view/override.
- **Deprecation notices** — Admin sets "Feature X will be removed on DATE" banner; users see notice until removal.

---

## Implementation Notes

- Admin routes live in `backend/app/api/admin.py`
- Frontend: `frontend/src/pages/Admin.jsx`
- Admin check: `require_admin()` reads JWT and verifies `is_admin` or `ADMIN_USERNAMES`
- Add new admin endpoints under `/api/admin/` and protect with `require_admin()`
