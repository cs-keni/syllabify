# Backend (Flask) image. Standardized on Docker; no venv.
# requirements.txt + requirements-dev.txt (pytest, ruff) for run + tests/lint in container.
# Production: gunicorn with PORT from env (e.g. Render). Local: docker-compose overrides CMD if needed.

FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
COPY backend/requirements-dev.txt backend/requirements-dev.txt

RUN pip install --no-cache-dir -r backend/requirements.txt \
    && pip install --no-cache-dir -r backend/requirements-dev.txt

COPY backend/ ./backend/
WORKDIR /app/backend

ENV FLASK_APP=app.main
ENV PORT=5000
EXPOSE 5000
# Render sets PORT at runtime; use shell so ${PORT} is expanded. --timeout 120 for slow DB/cold start.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5000} --timeout 120 app.main:app"]
