"""
Canonical database connection factory.
Auto-detects backend from environment:
  - DATABASE_URL set to postgres[ql]://...  →  psycopg2 wrapped in PgCompatConnection
  - Otherwise (DB_HOST/PORT/USER/PASSWORD/NAME set)  →  mysql.connector

Import get_db() from here; do not duplicate connection logic across files.
"""
import os


def get_db():
    """Return a database connection appropriate for the current environment."""
    db_url = os.getenv("DATABASE_URL", "")
    if db_url.startswith(("postgres://", "postgresql://")):
        return _get_pg(db_url)
    return _get_mysql()


def _get_pg(url: str):
    import psycopg2

    from app.db.pg_compat import PgCompatConnection

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    conn = psycopg2.connect(url)
    return PgCompatConnection(conn)


def _get_mysql():
    import mysql.connector

    port = os.getenv("DB_PORT", "3306")
    try:
        port = int(port)
    except (TypeError, ValueError):
        port = 3306
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=port,
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        connection_timeout=15,
    )
