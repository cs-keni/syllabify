# Frontend Structure

This document explains the frontend folder structure, why each file exists, and how components connect to make Syllabify work. It is intended for developers new to React/full-stack projects.

---

## Root Layout

```
frontend/
├── src/                    # Source code (React app)
├── public/                 # Static assets
├── index.html              # HTML shell (entry for Vite)
├── vite.config.js          # Build tool config (dev server, API proxy)
├── tailwind.config.js      # Tailwind CSS theme and utilities
├── postcss.config.js       # PostCSS (used by Tailwind)
├── package.json            # Dependencies and scripts
├── package-lock.json       # Locked dependency versions
├── .eslintrc.*             # Linting rules
├── .prettierrc*            # Code formatting rules
├── README.md
├── FRONTEND.md
└── STRUCTURE.md            # This file
```

---

## `src/` — React Application

### Entry Points

| File | Purpose | Talks to |
|------|---------|----------|
| **main.jsx** | React entry point. Renders `<App />` into the DOM. | `App.jsx`, `styles/index.css` |
| **App.jsx** | Root component. Sets up Router, AuthProvider, and routes. | `contexts/AuthContext`, `Layout`, all page components |

---

### `src/contexts/` — Shared State

| File | Purpose | Talks to |
|------|---------|----------|
| **AuthContext.jsx** | Holds login state (user, token, securitySetupDone). Provides `login`, `logout`, `completeSecuritySetup`. All auth-aware components use this. | `api/client` (login, me, securitySetup) |

---

### `src/api/` — Backend Communication

| File | Purpose | Talks to |
|------|---------|----------|
| **client.js** | HTTP client. Defines `login`, `securitySetup`, `me`. Adds auth token to headers. Base URL from env (`VITE_API_URL` or localhost:5000). | Backend `/api/auth/*` endpoints. Used by `AuthContext` and pages. |

---

### `src/hooks/` — Reusable Logic

| File | Purpose | Talks to |
|------|---------|----------|
| **useAuth.js** | Re-exports `useAuth` from AuthContext. Convenience for components. | `contexts/AuthContext` |

---

### `src/pages/` — Screen-Level Components

Each page is a route. Layout wraps them and shows the nav bar.

| File | Purpose | Talks to |
|------|---------|----------|
| **Login.jsx** | Login form. Calls `login` from AuthContext, redirects to Dashboard or SecuritySetup. | `AuthContext` |
| **SecuritySetup.jsx** | One-time security questions form. Calls `completeSecuritySetup`. | `AuthContext` |
| **Dashboard.jsx** | Home. Shows weekly overview, upcoming assignments, course cards. Placeholder data for now. | `CourseCard`, `Layout` (via App) |
| **Upload.jsx** | Multi-step: upload → review → confirm. Uses SyllabusUpload and ParsedDataReview. | `SyllabusUpload`, `ParsedDataReview` |
| **Schedule.jsx** | Weekly schedule view. Displays SchedulePreview. | `SchedulePreview` |
| **Preferences.jsx** | Work hours, preferred days, max hours per day. UI only (backend integration TODO). | None yet |

---

### `src/components/` — Reusable UI Pieces

| File | Purpose | Talks to |
|------|---------|----------|
| **Layout.jsx** | Nav bar + main content area. Checks auth; redirects to Login or SecuritySetup if needed. Renders child route via `<Outlet />`. | `AuthContext`, `react-router-dom` |
| **CourseCard.jsx** | Card showing course name, term, assignment count. Links to Schedule page. | Receives `course` prop from parent (e.g. Dashboard) |
| **SyllabusUpload.jsx** | Toggle: upload PDF or paste text. Simulates parse (real API TODO). Calls `onComplete` with course name. | Receives `onComplete` from Upload page |
| **ParsedDataReview.jsx** | Editable table of assignments (name, due date, hours). User can edit and confirm. | Receives `assignments`, `onAssignmentsChange`, `onConfirm` from Upload page |
| **SchedulePreview.jsx** | Weekly grid (Mon–Sun, 24h). Renders time blocks. Shows conflicts. Uses mock data (real API TODO). | Receives `weekStart` from Schedule page |

---

### `src/styles/`

| File | Purpose |
|------|---------|
| **index.css** | Global styles, Tailwind directives, CSS variables (colors, fonts). |

---

## Request Flow Summary

1. **User visits app** → `main.jsx` loads `App.jsx` → `AuthProvider` wraps routes
2. **AuthProvider** checks `localStorage` for token → calls `api.me(token)` → sets user/securitySetupDone
3. **Layout** checks `user` → if not logged in, redirects to `/login`
4. **Login** → user submits → `api.login()` → backend returns token → stored in localStorage → redirect
5. **SecuritySetup** → if `!securitySetupDone`, user must complete → `api.securitySetup()` → redirect to Dashboard
6. **Dashboard, Upload, Schedule** → use components; API calls for syllabus/schedule/export will be wired in later

---

## Config Files

- **vite.config.js:** Dev server on port 3000. Proxies `/api` to `http://localhost:5000` so frontend and backend can run separately.
- **tailwind.config.js:** Theme (colors, spacing). Used by `index.css`.
- **package.json:** Dependencies (React, Vite, Tailwind, React Router). Scripts: `npm run dev`, `npm run build`, etc.

---

## Routing (from App.jsx)

| Path | Component | Auth required? |
|------|-----------|----------------|
| `/login` | Login | No |
| `/security-setup` | SecuritySetup | Yes (redirects to login if not) |
| `/` | Layout → Dashboard | Yes |
| `/upload` | Layout → Upload | Yes |
| `/schedule` | Layout → Schedule | Yes |
| `/preferences` | Layout → Preferences | Yes |
| `*` | Redirect to `/` | — |
