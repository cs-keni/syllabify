"""
Thin compatibility wrapper to make psycopg2 connections behave like mysql.connector
for the patterns used in this codebase:
  - conn.cursor(dictionary=True)  → RealDictCursor (dict rows)
  - cur.lastrowid                 → auto-injects RETURNING id on INSERT, captures result
  - cur.execute / fetchone / fetchall / rowcount / description
"""
import psycopg2
import psycopg2.extras


class PgCompatCursor:
    """Wraps psycopg2 RealDictCursor to support mysql.connector-style API."""

    def __init__(self, pg_cursor):
        self._cur = pg_cursor
        self._lastrowid = None

    def execute(self, sql, params=None):
        sql_upper = sql.upper()
        is_insert = sql_upper.lstrip().startswith("INSERT")
        if is_insert and "RETURNING" not in sql_upper:
            modified = sql.rstrip().rstrip(";") + " RETURNING id"
            self._cur.execute(modified, params)
            row = self._cur.fetchone()
            # row is a RealDictRow; extract id regardless of other columns
            self._lastrowid = row["id"] if row else None
        else:
            self._cur.execute(sql, params)

    @property
    def lastrowid(self):
        return self._lastrowid

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def close(self):
        self._cur.close()

    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def description(self):
        return self._cur.description


class PgCompatConnection:
    """Wraps psycopg2 connection to support mysql.connector-style cursor(dictionary=True)."""

    def __init__(self, pg_conn):
        self._conn = pg_conn

    def cursor(self, dictionary=False):
        pg_cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return PgCompatCursor(pg_cur)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()
