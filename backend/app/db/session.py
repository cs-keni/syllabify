# SQLAlchemy engine + session factory.
# Prefers DATABASE_URL env var (Supabase/PostgreSQL).
# Falls back to building a mysql+pymysql:// URL from DB_* vars (Railway/MySQL).

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_raw_url = os.getenv("DATABASE_URL", "")

if _raw_url.startswith(("http://", "https://")):
    raise RuntimeError(
        "DATABASE_URL looks like an HTTP URL, not a database connection string. "
        "In Supabase: Project Settings → Database → Connection string → URI tab. "
        f"It should start with postgresql://... Got: {_raw_url[:60]}"
    )

if _raw_url.startswith("postgres://"):
    # Supabase (and some other providers) emit postgres:// which SQLAlchemy rejects
    _raw_url = _raw_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif _raw_url.startswith("postgresql://"):
    _raw_url = _raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)

if _raw_url:
    DATABASE_URL = _raw_url
else:
    MYSQL_HOST = os.getenv("DB_HOST", "localhost")
    MYSQL_PORT = os.getenv("DB_PORT", "3306")
    MYSQL_DATABASE = os.getenv("DB_NAME")
    MYSQL_USER = os.getenv("DB_USER")
    MYSQL_PASSWORD = os.getenv("DB_PASSWORD")
    DATABASE_URL = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
    )

engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
