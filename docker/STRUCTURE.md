# Docker Structure

This document explains the `docker/` folder and how it connects to the rest of Syllabify. Docker is used to run the database and backend in a consistent way for all developers.

---

## Folder Layout

```
docker/
├── init.sql        # SQL script run when MySQL starts for the first time
├── README.md       # Docker setup instructions
└── STRUCTURE.md    # This file
```

---

## `init.sql`

**Purpose:** Defines the database schema (tables) that MySQL needs when it first starts. It runs automatically when the MySQL container is created for the first time.

**What it creates:**
- **Users** — Stores usernames, password hashes, and whether security setup is done
- **UserSecurityAnswers** — Stores security questions and hashed answers (linked to Users)
- **Schedules** — Stores schedule names and which user owns them
- **Assignments** — Stores assignment names, workload, notes (linked to Schedules)

**Connections:**
- Used by **docker-compose.yml** (at project root): `./docker/init.sql` is mounted into the MySQL container at `/docker-entrypoint-initdb.d/init.sql`
- MySQL runs this script automatically on first startup
- The **backend** (Flask) connects to this MySQL database and reads/writes these tables via `app/db/session.py` and `app/models/`

---

## How Docker Fits Into Syllabify

1. **docker-compose.yml** (at project root) defines two services:
   - **mysql** — Runs MySQL 8.0, loads `init.sql`, exposes port 3306
   - **backend** — Builds from `backend/Dockerfile`, runs Flask on port 5000, connects to `mysql`

2. **Startup order:** MySQL starts first. When healthy, the backend starts and connects to it.

3. **Data persistence:** A Docker volume (`mysql_data`) keeps database data between restarts.

---

## Important Note

The `docker/` folder only contains **initialization scripts** for MySQL. The main Docker configuration (`docker-compose.yml`, `backend/Dockerfile`) lives at the project root and in `backend/`, respectively.
