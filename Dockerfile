# Root Dockerfile for Render (Render looks for Dockerfile at repo root).
# Same as backend/Dockerfile; build context is repo root so COPY backend/... works.

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
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5000} app.main:app"]
