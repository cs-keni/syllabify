# Backend

Backend API server for Syllabify.

## Tech Stack

- **Framework**: Flask
- **Database**: MySQL (3NF schema)
- **ORM**: SQLAlchemy
- **Testing**: pytest
- **Linting**: ruff

## Project Structure

```text
backend/
├── app/
│   ├── main.py                # Flask entry point
│   ├── api/                   # Route definitions
│   ├── core/                  # Core app logic
│   ├── services/              # Business logic
│   ├── models/                # ORM models (3NF)
│   ├── schemas/               # Request/response schemas
│   ├── db/                    # Database setup
│   └── utils/                 # Utility functions
├── tests/                     # Test files
├── requirements.txt           # Backend dependencies (Docker)
├── requirements-dev.txt       # Dev deps (ruff, pytest) (Docker)
├── Dockerfile                 # Backend image
└── pyproject.toml             # Ruff / pytest config
```

## Setup (Docker)

We standardize on **Docker** (no venv). See `docker/README.md` in the project root.

1. From project root: `docker compose up -d` (backend + MySQL).
2. Copy `.env.example` to `.env` and set `DB_*`, `SECRET_KEY`, etc.
3. Initialize DB (run inside backend container when implemented):

   ```bash
   docker compose run --rm backend python -m app.db.init_db
   ```

## Run backend

```bash
docker compose up -d
# Backend: http://localhost:5000
```

## Testing (in container)

```bash
docker compose run --rm backend pytest

# With coverage
docker compose run --rm backend pytest --cov=app --cov-report=html
```

## Linting (in container)

```bash
docker compose run --rm backend ruff check app/
docker compose run --rm backend ruff check app/ --fix
```
