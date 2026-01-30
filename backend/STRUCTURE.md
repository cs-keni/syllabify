# Backend Structure

This document explains the backend folder structure, why each file exists, and how components connect to make Syllabify work. It is intended for developers new to full-stack projects who are used to focused assignments.

---

## Root Layout

```
backend/
├── app/                    # Main application code
├── tests/                  # Automated tests
├── Dockerfile              # Build instructions for running backend in Docker
├── pyproject.toml          # Project metadata and tool config (e.g., pytest)
├── requirements.txt        # Python dependencies (Flask, MySQL, etc.)
├── requirements-dev.txt    # Dev-only dependencies (testing, linting)
├── README.md
├── AUTH.md
├── BACKEND.md
└── STRUCTURE.md            # This file
```

---

## `app/` — Application Code

The `app/` folder is the heart of the backend. Everything here serves the API that the frontend calls.

### `app/main.py`
**Purpose:** Entry point of the backend. Creates the Flask app and wires everything together.

**Connections:**
- Registers API blueprints (auth, syllabus, schedule, export)
- Configures CORS so the frontend can call the backend
- Exposes routes like `/` and `/api/auth/*`
- Reads `DB_*` env vars to connect to MySQL

---

### `app/api/` — HTTP Endpoints

These files define the URLs the frontend calls (e.g. `/api/auth/login`).

| File | Purpose | Talks to |
|------|---------|----------|
| **auth.py** | Login, security setup (one-time questions), `/me` (current user). Returns JWT token. | MySQL (Users, UserSecurityAnswers), `core/security` concepts (JWT, bcrypt) |
| **syllabus.py** | Upload syllabus (PDF or paste text) and parse it. Returns extracted assignments/dates. | `services/parsing_service`, `utils/pdf_utils`, `utils/date_utils` |
| **schedule.py** | Generate schedules from courses + user prefs. List schedules. | `services/scheduling_service`, `models/`, `schemas/` |
| **export.py** | Export schedule to Google Calendar or ICS file. | `services/calendar_service`, `models/` |

**Flow:** Browser → `main.py` (Flask) → `api/*` route → service/model → database → response → browser.

---

### `app/core/` — Shared Configuration & Logic

| File | Purpose | Talks to |
|------|---------|----------|
| **config.py** | Loads env vars (DB, SECRET_KEY, JWT, Google OAuth, etc.) into one place. | Used by `main.py`, `db/session.py`, `api/auth.py` |
| **dependencies.py** | Helpers like `get_current_user` (from JWT) and `require_auth` decorator. | Used by API routes that need authentication |
| **security.py** | JWT encode/decode, password hashing (bcrypt), OAuth helpers. | Used by `api/auth.py` and `dependencies.py` |

---

### `app/db/` — Database

| File | Purpose | Talks to |
|------|---------|----------|
| **base.py** | SQLAlchemy base class. All models inherit from this. | Imported by every file in `models/` |
| **session.py** | Creates the database engine and session factory. Connects to MySQL. | Used by API routes and services that read/write data |
| **init_db.py** | Creates tables from models. Can seed data. Run on first setup or via Docker. | Uses `base.py` and `models/` |

---

### `app/models/` — Database Tables (ORM)

Each file defines one or more database tables as Python classes. SQLAlchemy turns these into SQL.

| File | Purpose | Talks to |
|------|---------|----------|
| **user.py** | Users table (id, username, password_hash, security_setup_done). Links to Schedules. | `db/base`, `db/session` |
| **course.py** | Courses (future). Links user, assignments, schedule. | `db/base` |
| **assignment.py** | Assignments (name, workload, notes). Belongs to a Schedule. | `db/base`, `models/schedule` |
| **schedule.py** | Schedules (name, owner). Has many Assignments. Belongs to a User. | `db/base`, `models/user`, `models/assignment` |

---

### `app/schemas/` — Request/Response Shapes

Schemas define the expected JSON format for API requests and responses. They validate and document the API.

| File | Purpose | Talks to |
|------|---------|----------|
| **user.py** | Shapes for login request, user response. | `api/auth` |
| **course.py** | Shapes for create/update course, course list. | `api/syllabus`, `api/schedule` |
| **assignment.py** | Shapes for parsed assignment, create/update, list. | `api/syllabus`, `api/schedule`, `services/parsing_service` |
| **schedule.py** | Shapes for generate request (course ids, prefs) and schedule response (time blocks). | `api/schedule`, `api/export` |

---

### `app/services/` — Business Logic

Services contain the core logic. API routes call them; they use utils and models.

| File | Purpose | Talks to |
|------|---------|----------|
| **parsing_service.py** | Takes PDF or text, extracts assignments and dates. Returns structured data for review. | `utils/pdf_utils`, `utils/date_utils`, `schemas/assignment` |
| **scheduling_service.py** | Takes courses, assignments, user prefs. Allocates time blocks, detects conflicts. Returns proposed schedule. | `models/`, `schemas/schedule` |
| **calendar_service.py** | Builds ICS file or pushes to Google Calendar from an approved schedule. | `config` (OAuth vars), `models/schedule` |

---

### `app/utils/` — Helper Functions

| File | Purpose | Talks to |
|------|---------|----------|
| **date_utils.py** | Parses due dates, exam dates from text (regex, heuristics). Normalizes to datetime. | Used by `parsing_service` |
| **pdf_utils.py** | Extracts text from PDF bytes. Handles encoding. | Used by `parsing_service` |

---

## `tests/` — Automated Tests

| File | Purpose |
|------|---------|
| **test_api.py** | Tests HTTP endpoints (auth, syllabus, etc.) |
| **test_parsing.py** | Tests parsing logic |
| **test_scheduling.py** | Tests scheduling logic |
| **test_placeholder.py** | Placeholder/smoke tests |

---

## Data Flow Summary

1. **Login:** Frontend → `POST /api/auth/login` → `auth.py` → MySQL → JWT → Frontend
2. **Upload syllabus:** Frontend → `POST /api/syllabus/upload` or `/parse` → `syllabus.py` → `parsing_service` → `pdf_utils` / `date_utils` → Frontend
3. **Generate schedule:** Frontend → `POST /api/schedule/generate` → `schedule.py` → `scheduling_service` → Frontend
4. **Export:** Frontend → `POST /api/export/google` or `/ics` → `export.py` → `calendar_service` → Frontend

---

## Config Files

- **Dockerfile:** Builds the backend image. Used by `docker-compose`.
- **requirements.txt:** Production dependencies.
- **requirements-dev.txt:** Test and dev tools.
- **pyproject.toml:** Project config (pytest, black, etc.).
