# Google OAuth: Sign-In & Calendar Import

This document explains what Google OAuth is capable of, how we will use it for **Google Sign-In** and **Calendar Import**, and what needs to be implemented. It is a planning document—implementation happens after you understand and approve this workflow.

**Setup instructions:** See **[GOOGLE-OAUTH-SETUP.md](./GOOGLE-OAUTH-SETUP.md)** for step-by-step deployment (Google Cloud, Render, Vercel, Railway).

---

## 1. What Is Google OAuth?

**Google OAuth 2.0** is Google’s authorization framework that lets third-party apps:

1. **Authenticate users** (“Sign in with Google”) without handling passwords
2. **Request access** to Google APIs (e.g., Calendar) with user consent
3. **Receive tokens** (ID token for identity, access token for API calls, refresh token for long-term access)

### 1.1 Core Capabilities

| Capability                    | Description                                                                                                                                                                         |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Sign-in with Google**       | User clicks “Sign in with Google” → redirects to Google → user signs in → app receives an ID token with user identity (email, name, picture, unique Google ID). No password needed. |
| **User profile**              | With `openid`, `email`, `profile` scopes: access to `sub` (Google user ID), `email`, `name`, `picture`, etc.                                                                        |
| **Access Google APIs**        | With additional scopes (e.g., Calendar): receive access tokens to call Google APIs on behalf of the user.                                                                           |
| **Incremental authorization** | Request minimal scopes first (sign-in only), then request more scopes (e.g., Calendar) only when the user uses a feature that needs them.                                           |

### 1.2 OpenID Connect

Google OAuth implements **OpenID Connect (OIDC)**. When a user signs in, the app gets an **ID token** (JWT) containing:

- `sub` — unique Google user ID (stable across sessions)
- `email` — user’s Google email
- `name`, `picture` — profile info (if requested)

The backend validates this ID token and can create or link a user account without ever handling a password.

---

## 2. Google Sign-In: How It Will Work

### 2.1 Current Auth vs. Google Sign-In

| Current (manual)                              | With Google Sign-In                                                              |
| --------------------------------------------- | -------------------------------------------------------------------------------- |
| User creates account with username + password | User clicks “Sign in with Google”                                                |
| Password stored as bcrypt hash                | No password stored for Google users                                              |
| Username chosen by user                       | Username derived from email (e.g., `user@gmail.com` → `user`) or stored as email |
| Security setup (Q&A) required                 | Security setup **skipped** for Google users (we trust Google’s authentication)   |

### 2.2 Sign-In Flow (High Level)

```
┌─────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  User   │     │  Frontend   │     │   Google    │     │   Backend   │
└────┬────┘     └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
     │                 │                   │                   │
     │  Click "Sign in │                   │                   │
     │  with Google"  │                   │                   │
     │────────────────>                   │                   │
     │                 │  Redirect to       │                   │
     │                 │  Google consent    │                   │
     │                 │──────────────────>│                   │
     │                 │                   │                   │
     │                 │  User signs in    │                   │
     │                 │  & consents        │                   │
     │                 │<──────────────────│                   │
     │                 │  (ID token /      │                   │
     │                 │   auth code)      │                   │
     │                 │                   │                   │
     │                 │  POST /api/auth/google  (ID token)   │
     │                 │─────────────────────────────────────>│
     │                 │                   │                   │
     │                 │                   │  Validate token   │
     │                 │                   │  Create/link user │
     │                 │                   │  Return JWT       │
     │                 │<─────────────────────────────────────│
     │                 │                   │                   │
     │  Redirect to    │                   │                   │
     │  dashboard      │                   │                   │
     │<────────────────                   │                   │
```

### 2.3 Implementation Options for Sign-In

**Option A: Authorization Code Flow (recommended for backend)**

1. Frontend redirects user to Google’s authorization URL with `client_id`, `redirect_uri`, `scope=openid email profile`.
2. User signs in on Google; Google redirects back with an `authorization_code`.
3. Frontend sends the code to backend; backend exchanges it for ID token + access token.
4. Backend validates ID token, creates/links user, returns our JWT.

**Option B: Frontend-only (Implicit / Token Model)**

1. Frontend uses Google Identity Services (GIS) JS library.
2. User signs in; frontend receives ID token directly.
3. Frontend sends ID token to backend; backend validates it and returns our JWT.

**Recommendation:** Option B is simpler for sign-in only. Option A is better if we want the backend to hold refresh tokens for Calendar API (server-side API calls).

### 2.4 Account Linking (Decided)

- **New user:** Create a `Users` row with `google_id`, `email`, `username` (from email), `password_hash = NULL`, `auth_provider = 'google'`.
- **Existing user (same email):** **Auto-link** — add `google_id` to the existing account. The user now has multiple ways to sign in (password or Google).
- **Existing user (different email):** Treat as a new account (different identity).

**Policy:** If the Google sign-in email matches an existing Syllabify account email, we automatically link the Google account. The user can then sign in with either username/password or Google.

**Implementation:** When auto-linking, set `google_id` on the existing user. When creating a new Google user, set `security_setup_done = TRUE` so they skip the security setup page (we trust Google). For auto-linked users who already have `security_setup_done`, leave it as-is.

### 2.5 Username for Google Users

For new users signing in with Google, we need a unique `username`. Options:

- Use `email` as username (e.g. `user@gmail.com`).
- Derive from email (e.g. `user` from `user@gmail.com`); if collision, append suffix (e.g. `user_abc123`).

**Recommendation:** Use email as username for simplicity and uniqueness. **Note:** Current `username` validation allows only `[a-zA-Z0-9_-]`. Email contains `@` and `.`, so we must either: (a) relax validation for Google users, or (b) derive a valid username (e.g. `user` from `user@gmail.com`, handle collisions with suffix). Prefer (b) to avoid breaking existing validation.

---

## 3. Calendar Import: How It Will Work

### 3.1 What “Import” Means Here

**Import** = read events **from** the user’s Google Calendar into Syllabify. This is the opposite of **export** (which pushes our schedule to their calendar).

We use the **Calendar API `events.list`** endpoint to fetch events. The `events.import` endpoint is for adding events _to_ a calendar, not reading from it.

### 3.2 Why Import?

- **Conflict avoidance:** User has class times, meetings, or other blocks in Google Calendar. When generating study times, we should avoid scheduling during those.
- **Pre-fill:** Optionally show existing commitments in the schedule view.
- **Single source of truth:** User keeps their calendar in Google; we read it to inform our scheduling.

### 3.3 Calendar API Scopes

| Scope                                                            | Purpose                                                                                          |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `https://www.googleapis.com/auth/calendar.readonly`              | See and download any calendar the user can access; required for **calendar list** and **events** |
| `https://www.googleapis.com/auth/calendar.events.readonly`       | View events on all calendars                                                                     |
| `https://www.googleapis.com/auth/calendar.events.owned.readonly` | View events on calendars the user owns (most restrictive)                                        |
| `https://www.googleapis.com/auth/calendar.calendarlist.readonly` | List the user’s calendars (for multi-calendar selection)                                         |

**For multi-calendar selection:** We need `calendar.readonly` (or `calendar.calendarlist.readonly` + `calendar.events.readonly`) so we can:

1. Call `calendarList.list` to show the user their calendars.
2. Call `events.list` for each selected calendar.

### 3.4 Multi-Calendar Selection (Decided)

**Policy:** If the user has multiple calendars, they **choose which calendars to import**. We do not import all calendars by default.

**Flow:**

1. User clicks “Import from Google Calendar.”
2. Backend calls `calendarList.list` to fetch the user’s calendars.
3. Frontend displays a list (e.g. checkboxes) with calendar names.
4. User selects one or more calendars.
5. User selects date range (or we use active term dates).
6. Backend calls `events.list` for each selected calendar ID.
7. Events are stored with a reference to the source calendar (for sync).

### 3.5 Calendar Import Flow

```
┌─────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  User   │     │  Frontend   │     │   Backend   │     │   Google    │
└────┬────┘     └──────┬──────┘     └──────┬──────┘     │  Calendar   │
     │                 │                   │            │    API      │
     │  Click "Import  │                   │            │             │
     │  from Google"   │                   │            │             │
     │────────────────>                   │            │             │
     │                 │  If no token:     │            │             │
     │                 │  OAuth for        │            │             │
     │                 │  calendar scope   │            │             │
     │                 │────────────────────────────────────────────>│
     │                 │<────────────────────────────────────────────│
     │                 │                   │            │             │
     │                 │  GET /api/calendar/list       │             │
     │                 │──────────────────>│ calendarList.list       │
     │                 │                   │─────────────────────────>│
     │                 │                   │<─────────────────────────│
     │  Show calendar  │<──────────────────│            │             │
     │  picker         │                   │            │             │
     │                 │                   │            │             │
     │  Select cals +  │                   │            │             │
     │  date range     │                   │            │             │
     │────────────────>                   │            │             │
     │                 │  POST /api/calendar/import    │             │
     │                 │  (calendar_ids[], date_range) │             │
     │                 │──────────────────>│ events.list per calendar│
     │                 │                   │─────────────────────────>│
     │                 │                   │<─────────────────────────│
     │                 │                   │  Store ExternalEvents   │
     │                 │<──────────────────│            │             │
     │  Show imported  │                   │            │             │
     │  events         │                   │            │             │
     │<────────────────                   │            │             │
```

### 3.6 Incremental Authorization

We split scopes so the initial consent is minimal:

1. **Sign-in:** `openid email profile` only.
2. **Calendar import:** When user clicks “Import from Google Calendar,” request `calendar.readonly` (or `calendar.calendarlist.readonly` + `calendar.events.readonly`).

### 3.7 Sync Button (Decided)

**Policy:** After importing, the user can press a **“Sync”** button to refresh the imported calendar data. This re-fetches events from the selected calendars and updates our stored copy (add new, update changed, optionally remove deleted).

**Implementation notes:**

- Track which calendars the user has imported (e.g. in `UserCalendarConnections` or similar).
- “Sync” calls the same `events.list` logic for those calendars and upserts into `ExternalEvents`.
- Use `syncToken` from Calendar API for incremental sync (optional optimization).

### 3.8 Data Model for Imported Events

**Chosen approach:** Add an `ExternalEvents` (or `UserCalendarEvents`) table so the schedule engine can treat imported events as fixed blocks when allocating study times.

| Table                                    | Purpose                                                                                                                                                                       |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **ExternalEvents**                       | `user_id`, `google_event_id`, `google_calendar_id`, `title`, `start_time`, `end_time`, `source` (`google`), `term_id` (optional). Used by schedule engine to avoid conflicts. |
| **UserCalendarConnections** (or similar) | `user_id`, `google_calendar_id`, `calendar_name`, `last_synced_at`. Tracks which calendars the user has imported so we know what to sync when they press “Sync.”              |

---

## 4. What Needs to Be Implemented

### 4.1 Google Cloud Setup (One-time)

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/).
2. Enable **Google Calendar API**.
3. Create **OAuth 2.0 credentials** (Web application).
4. Configure **Authorized redirect URIs** (e.g. `https://yourapp.com/api/auth/google/callback`, `http://localhost:5173/...` for dev).
5. Configure **OAuth consent screen** (app name, logo, scopes).
6. Store `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in environment variables.

### 4.2 Database Changes

| Change                                             | Purpose                                                                                                                                                                         |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Users.google_id` (VARCHAR, UNIQUE, nullable)      | Link user to Google account                                                                                                                                                     |
| `Users.auth_provider` (VARCHAR, default `'local'`) | `'local'` or `'google'`                                                                                                                                                         |
| `UserOAuthTokens`                                  | `user_id`, `provider` (`google`), `access_token`, `refresh_token`, `expires_at` — **required** for Calendar import/sync (backend needs refresh token for server-side API calls) |
| `ExternalEvents` (or `UserCalendarEvents`)         | Store imported calendar events for conflict avoidance                                                                                                                           |
| `UserCalendarConnections`                          | Track which calendars the user has imported (for Sync button)                                                                                                                   |

For Google-only users: `password_hash` can be `NULL`. **Security setup is skipped** — we trust Google’s authentication, so no security Q&A required.

### 4.3 Backend

| Component                                                   | Description                                                                                                                                         |
| ----------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `POST /api/auth/google` or `POST /api/auth/google/callback` | Accept ID token (or auth code), validate with Google, create/link user, return Syllabify JWT                                                        |
| `GET /api/auth/google/url`                                  | Return Google authorization URL for frontend redirect (if using code flow)                                                                          |
| `GET /api/calendar/auth-url`                                | Return Google OAuth URL for Calendar scope. Backend includes `state` to associate callback with current user.                                       |
| `GET /api/calendar/callback`                                | Handle OAuth redirect: exchange code for tokens, store in `UserOAuthTokens`.                                                                        |
| `GET /api/calendar/list`                                    | Return user’s calendars (from `calendarList.list`) for multi-calendar picker                                                                        |
| `POST /api/calendar/import`                                 | Accept `calendar_ids[]`, `date_range`; call `events.list` per calendar; persist to `ExternalEvents`; store connections in `UserCalendarConnections` |
| `POST /api/calendar/sync`                                   | Re-fetch events from connected calendars; upsert into `ExternalEvents` (Sync button)                                                                |
| `GET /api/calendar/events`                                  | Return stored external events for the current user/term                                                                                             |
| Token refresh logic                                         | Use refresh token to get new access token when expired                                                                                              |
| `google-auth` or `google-auth-oauthlib`                     | Python libraries for token validation and Calendar API                                                                                              |

### 4.4 Frontend

| Component                                                | Description                                                                       |
| -------------------------------------------------------- | --------------------------------------------------------------------------------- |
| “Sign in with Google” button on Login and Register pages | Triggers Google OAuth flow                                                        |
| Google Identity Services (GIS) script                    | Load `https://accounts.google.com/gsi/client`                                     |
| Handle redirect/callback                                 | Send ID token or auth code to backend                                             |
| “Import from Google Calendar” on Schedule page           | Triggers Calendar OAuth (if needed); fetches calendar list; shows calendar picker |
| Calendar picker (multi-select)                           | User selects which calendars to import                                            |
| Date range picker for import                             | User chooses which period to import (e.g. term dates)                             |
| “Sync” button                                            | Re-fetches events from connected calendars and updates stored data                |

### 4.5 Schedule Engine Integration (Deferred)

- **Status:** Saint George is still working on the schedule engine. Integration is **deferred** until the engine is ready.
- **When ready:** When building schedule input (e.g. in `schedule_input_builder.py` or equivalent), include `ExternalEvents` as fixed blocks. Scheduling heuristics should not place study blocks during these times. Format: pass `external_events` or `blocked_times` to the engine with `start_time`, `end_time` per block.
- **For now:** We implement storage (`ExternalEvents`), import/sync APIs, and UI. The schedule engine will consume this data when available.

### 4.6 Edge Cases & Implementation Notes

| Scenario                                          | Handling                                                                                                                                                                                                                           |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| User revokes Google Calendar access               | Token refresh fails; show “Reconnect Google Calendar” and prompt for re-auth.                                                                                                                                                      |
| User removes a calendar from their Google account | Sync may fail for that calendar; optionally remove from `UserCalendarConnections` or mark as disconnected.                                                                                                                         |
| Duplicate events (same `google_event_id`)         | With full-replace sync, duplicates are avoided by replacing all events per calendar.                                                                                                                                               |
| Sync strategy                                     | Full replace per calendar: for each connected calendar, delete our stored events in the date range, then insert freshly fetched events. Simpler than incremental; avoids orphaned deleted events.                                  |
| Sync date range                                   | Use active term dates, or the same range as the original import. Store `import_date_range_start`, `import_date_range_end` in `UserCalendarConnections` if we want to remember the user's choice; otherwise default to active term. |
| Timezone                                          | Store `start_time`/`end_time` in UTC or user’s timezone; align with `UserPreferences.timezone` if present.                                                                                                                         |
| All-day events                                    | Include in import; treat as blocking the full day (or full day within term dates).                                                                                                                                                 |
| Recurring events                                  | `events.list` with `singleEvents=true` expands them; we get individual instances.                                                                                                                                                  |

---

## 5. Workflow Summary

### 5.1 Google Sign-In

1. User clicks “Sign in with Google” on Login or Register.
2. Frontend opens Google consent (or redirects).
3. User signs in; Google returns ID token (or auth code).
4. Frontend sends token/code to backend.
5. Backend validates, creates or **auto-links** user (if same email), returns Syllabify JWT.
6. User is logged in. **Security setup is skipped** for Google users — we trust Google’s authentication.

### 5.2 Calendar Import

1. User is logged in (via password or Google).
2. User goes to Schedule page and clicks “Import from Google Calendar.”
3. If no Calendar token: OAuth flow for `calendar.readonly` (incremental auth).
4. Backend fetches calendar list; frontend shows **calendar picker** (multi-select).
5. User selects one or more calendars and date range (or we use active term dates).
6. Backend calls `events.list` for each selected calendar; stores in `ExternalEvents`; records connections in `UserCalendarConnections`.
7. Schedule engine will use these when generating study times (once Saint George completes the engine).
8. User sees imported events in schedule view.

### 5.3 Calendar Sync

1. User has already imported one or more calendars.
2. User clicks **“Sync”** button on Schedule page.
3. Backend re-fetches events from connected calendars (from `UserCalendarConnections`).
4. Backend full-replaces events per calendar (delete stored, insert fresh).
5. User sees updated events.

---

## 6. Security Considerations

- **Validate ID tokens on the backend** — never trust tokens from the client without verification.
- **Use HTTPS** in production for all OAuth redirects.
- **Store refresh tokens securely** — encrypted at rest, never exposed to frontend.
- **Minimal scopes** — request Calendar only when the user explicitly uses import.
- **Token expiry** — access tokens are short-lived; use refresh tokens for Calendar API.

---

## 7. References

- [Google OAuth 2.0 for Web Server Apps](https://developers.google.com/identity/protocols/oauth2/web-server)
- [OpenID Connect with Google](https://developers.google.com/identity/openid-connect/openid-connect)
- [Sign in with Google (GIS)](https://developers.google.com/identity/gsi/web)
- [Google Calendar API – Events: list](https://developers.google.com/calendar/api/v3/reference/events/list)
- [Google Calendar API – CalendarList: list](https://developers.google.com/calendar/api/v3/reference/calendarList/list)
- [Calendar API Scopes](https://developers.google.com/workspace/calendar/api/auth)
- [Incremental Authorization](https://developers.google.com/identity/sign-in/web/incremental-auth)

---

## 8. Decided Policies (Summary)

| Topic                               | Decision                                                           |
| ----------------------------------- | ------------------------------------------------------------------ |
| **Account linking**                 | Auto-link if same email. User can sign in with password or Google. |
| **Security setup for Google users** | Skip. We trust Google’s authentication.                            |
| **Calendar selection**              | User chooses which calendars to import (multi-select).             |
| **Sync**                            | “Sync” button re-fetches from connected calendars on demand.       |

---

## 9. Implementation Checklist (Pre-Implementation Reference)

Before implementing, ensure:

- [ ] Google Cloud project created; Calendar API enabled; OAuth credentials configured
- [ ] `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` in env; redirect URIs set
- [ ] Migration: `Users.google_id`, `Users.auth_provider`
- [ ] Migration: `UserOAuthTokens` (for refresh tokens)
- [ ] Migration: `ExternalEvents`, `UserCalendarConnections`
- [ ] Backend: `POST /api/auth/google` (validate ID token, create/link user, return JWT)
- [ ] Backend: `GET /api/calendar/auth-url`, `GET /api/calendar/callback`, `GET /api/calendar/list`, `POST /api/calendar/import`, `POST /api/calendar/sync`
- [ ] Frontend: “Sign in with Google” button; calendar picker; Sync button
- [ ] Schedule engine: include `ExternalEvents` as fixed blocks when generating study times **(deferred until Saint George completes the engine)**
