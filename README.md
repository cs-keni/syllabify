# Syllabify

## Project Overview

Syllabify is a web-based academic planning tool designed to help university students transform course syllabi into structured, personalized study schedules. While platforms like Canvas provide assignment due dates, they do not help students plan when to work on assignments, how much time to allocate to each task, or how to balance workloads across multiple courses. Syllabify addresses this gap by extracting key academic information from syllabi and using heuristics to generate balanced study plans that integrate directly with students' calendars.

---

## Problem Statement

Course syllabi are the primary source of academic expectations for students, but they vary widely in format and structure (PDFs, Canvas pages, plain text). Students are often left to manually interpret deadlines, estimate workload, and plan their time across multiple courses. This frequently leads to poor time management, workload imbalance, and last-minute stress.

---

## Solution Overview

The system supports multiple syllabus formats, including uploaded PDFs and pasted text (e.g., Canvas syllabus pages). After parsing and extracting important information such as assignments, exams, and course schedules, Syllabify allows students to review and manually edit the extracted data to ensure accuracy. Once confirmed, the system generates a proposed study schedule that allocates time blocks based on assignment complexity, deadlines, and user preferences. The student remains in full control and must approve any generated schedule before it is finalized or exported.

Syllabify is designed as a client-server web application. The frontend provides interfaces for uploading syllabi, reviewing parsed data, previewing schedules, and managing multiple courses. The backend handles syllabus parsing, scheduling heuristics, validation, persistence, and integrations such as calendar exports. The system emphasizes transparency, user confirmation, and incremental refinement rather than fully automated decision-making.

---

## Key Features (Planned)

- Syllabus upload (PDF and text-based)
- Heuristic-based syllabus parsing
- Manual editing and validation of extracted data
- Support for multiple courses per user
- Study schedule generation with conflict detection
- Calendar export (Google Calendar / ICS)
- User preferences for work hours and days
- Responsive web interface

---

## Architecture Overview

Syllabify follows a client-server architecture:

- **Frontend**: Provides interfaces for uploading syllabi, reviewing parsed data, previewing schedules, and managing multiple courses
- **Backend**: Handles syllabus parsing, scheduling heuristics, validation, persistence, and integrations such as calendar exports
- **Database**: Relational database (3NF) storing users, courses, assignments, and schedules
- **Integrations**: Calendar export services (e.g., Google Calendar, ICS files)

This project is developed incrementally using Scrum, with early delivery of a minimum viable product (MVP) and continuous improvement through CI/CD. The final system demonstrates software engineering best practices, including modular architecture, RESTful APIs, database normalization, version control discipline, and user-centered design.

---

## Tech Stack

### Frontend

- React
- Tailwind CSS

### Backend

- Python
- Flask
- RESTful APIs
- SQLAlchemy (ORM)

### Database

- MySQL (3NF schema)

### Tooling

- Git & GitHub
- GitHub Actions (CI/CD)
- Jira (Scrum-based project management)

---

## Installation

<!-- Installation instructions will be added as the project is developed -->

We standardize on **Docker** (no venv). Docker isolates OS, Python, Node, MySQL, and system libs.

**Backend + MySQL:** From project root: `docker compose up -d`. See `docker/README.md` and `backend/README.md`.

<!-- - Prerequisites (Docker, Node for frontend) -->
<!-- - Frontend setup / Docker -->
<!-- - Database configuration -->
<!-- - Environment variable setup -->

---

## Development Workflow

- `dev` branch: Active development and integration
- `main` branch: Stable, production-ready code
- Direct pushes to `main` are blocked
- All releases are merged into `main` via pull requests

---

## Project Context

This project is developed as part of **CS 422 / CS 522 – Software Methodologies I** at the University of Oregon. The goal is to apply software engineering principles including requirements analysis, system design, iterative development, and team collaboration.

---

## Team

- Andrew Martin  
- Leon Wong  
- Saint George Aufranc  
- Kenny Nguyen  

---

## Project Structure

```text
syllabify/
├── .github/
│   └── workflows/
│       └── ci.yml                 # GitHub Actions CI pipeline
│
├── backend/
│   ├── app/
│   │   ├── main.py                # Flask entry point
│   │   ├── api/                   # Route definitions
│   │   │   ├── __init__.py
│   │   │   ├── auth.py             # Auth routes (login, signup)
│   │   │   ├── syllabus.py         # Upload + parse syllabus
│   │   │   ├── schedule.py         # Generate schedules
│   │   │   └── export.py           # Calendar export endpoints
│   │   │
│   │   ├── core/                  # Core app logic
│   │   │   ├── config.py           # App config, env vars
│   │   │   ├── security.py         # JWT, OAuth helpers
│   │   │   └── dependencies.py     # Flask dependencies
│   │   │
│   │   ├── services/              # Business logic
│   │   │   ├── parsing_service.py  # Syllabus parsing logic
│   │   │   ├── scheduling_service.py # Heuristics + engine
│   │   │   └── calendar_service.py # Google Calendar / ICS
│   │   │
│   │   ├── models/                # ORM models (3NF)
│   │   │   ├── user.py
│   │   │   ├── course.py
│   │   │   ├── assignment.py
│   │   │   └── schedule.py
│   │   │
│   │   ├── schemas/               # Request/response schemas
│   │   │   ├── user.py
│   │   │   ├── course.py
│   │   │   ├── assignment.py
│   │   │   └── schedule.py
│   │   │
│   │   ├── db/
│   │   │   ├── session.py          # DB connection
│   │   │   ├── base.py             # SQLAlchemy base
│   │   │   └── init_db.py          # DB initialization
│   │   │
│   │   └── utils/
│   │       ├── pdf_utils.py        # PDF/text extraction helpers
│   │       └── date_utils.py       # Date parsing helpers
│   │
│   ├── tests/
│   │   ├── test_parsing.py
│   │   ├── test_scheduling.py
│   │   └── test_api.py
│   │
│   ├── requirements.txt            # Backend deps (Flask, MySQL, etc.); Docker install
│   ├── requirements-dev.txt        # Dev deps (ruff, pytest); Docker install
│   ├── Dockerfile                  # Backend image for Docker Compose
│   ├── pyproject.toml              # Ruff / pytest config
│   └── README.md
│
├── docker/
│   └── README.md                   # Docker usage (compose, run tests/lint in container)
│
├── frontend/
│   ├── public/
│   │   └── index.html
│   │
│   ├── src/
│   │   ├── api/                    # API client calls
│   │   │   └── client.js
│   │   │
│   │   ├── components/             # Reusable UI components
│   │   │   ├── SyllabusUpload.jsx
│   │   │   ├── SchedulePreview.jsx
│   │   │   └── CourseCard.jsx
│   │   │
│   │   ├── pages/                  # Page-level components
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Upload.jsx
│   │   │   └── Login.jsx
│   │   │
│   │   ├── hooks/                  # Custom React hooks
│   │   │   └── useAuth.js
│   │   │
│   │   ├── styles/
│   │   │   └── index.css
│   │   │
│   │   ├── App.jsx
│   │   └── main.jsx
│   │
│   ├── package.json
│   ├── .eslintrc.cjs
│   ├── .prettierrc
│   └── README.md
│
├── docs/
│   ├── SRS.md
│   ├── SDS.md
│   ├── architecture/
│   │   └── system_architecture.png
│   └── presentations/
│       └── proposal_slides.pdf
│
├── docker-compose.yml              # Backend + MySQL services
├── .dockerignore                   # Excluded from Docker build context
├── .env.example                    # Environment variable template
├── .gitignore
├── LICENSE
└── README.md                       # Main project README
```

---

## Status

Under active development  
Initial MVP will be delivered early and expanded incrementally through CI/CD.
