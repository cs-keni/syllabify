"""
Canonical database connection factory.
Auto-detects backend from environment:
  - DATABASE_URL set to postgres[ql]://...  →  psycopg2 wrapped in PgCompatConnection
  - Otherwise (DB_HOST/PORT/USER/PASSWORD/NAME set)  →  mysql.connector (pooled)

Import get_db() from here; do not duplicate connection logic across files.
"""
import os
import threading


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


_mysql_pool = None
_mysql_pool_lock = threading.Lock()


def _get_mysql_pool():
    global _mysql_pool
    if _mysql_pool is not None:
        return _mysql_pool
    with _mysql_pool_lock:
        if _mysql_pool is None:
            import mysql.connector.pooling

            port = os.getenv("DB_PORT", "3306")
            try:
                port = int(port)
            except (TypeError, ValueError):
                port = 3306
            pool_size = int(os.getenv("MYSQL_POOL_SIZE", "5"))
            _mysql_pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="syllabify",
                pool_size=pool_size,
                host=os.getenv("DB_HOST", "localhost"),
                port=port,
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME"),
                connection_timeout=15,
            )
    return _mysql_pool


def _get_mysql():
    try:
        return _get_mysql_pool().get_connection()
    except Exception:
        # Fall back to direct connection if pooling unavailable (e.g. first import fails)
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
