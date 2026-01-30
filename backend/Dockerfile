# Backend (Flask) image. Standardized on Docker; no venv.
# requirements.txt + requirements-dev.txt (pytest, ruff) for run + tests/lint in container.

FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
COPY backend/requirements-dev.txt backend/requirements-dev.txt

RUN pip install --no-cache-dir -r backend/requirements.txt \
    && pip install --no-cache-dir -r backend/requirements-dev.txt

COPY backend/ ./backend/
WORKDIR /app/backend

ENV FLASK_APP=app.main
EXPOSE 5000
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]
