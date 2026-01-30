# Docker

All development and runtime use **Docker** (no venv). Docker isolates OS, Python, Node, MySQL, and system libs.

## Quick start

From the project root:

```bash
docker compose up -d
```

- **Backend**: <http://localhost:5000>
- **MySQL**: `localhost:3306` (use `DB_*` from `.env` or `docker-compose`).

View logs:

```bash
docker compose logs -f backend
```

## Run backend commands in container

Tests and linting run inside the backend container:

```bash
# Run tests
docker compose run --rm backend pytest

# Lint
docker compose run --rm backend ruff check app/

# Lint fix
docker compose run --rm backend ruff check app/ --fix
```

## Files

- `../docker-compose.yml` – backend + MySQL services.
- `../backend/Dockerfile` – Flask image (uses `requirements.txt` + `requirements-dev.txt`).
- `../.dockerignore` – paths excluded from build context.

## Env vars

Copy `.env.example` to `.env` and set `DB_*`, `SECRET_KEY`, etc. Compose uses these for MySQL and the backend.
