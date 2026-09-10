"""Small PostgreSQL compatibility layer for the legacy app database calls."""

import os
import re
from typing import Any, Optional

import psycopg2


_DATABASE_URL = (os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL") or "").strip()
if not _DATABASE_URL:
    raise RuntimeError(
        "PostgreSQL is not configured. Set DATABASE_URL (Supabase direct connection string) "
        "or SUPABASE_DB_URL in Render environment variables."
    )


def _translate_query(query: str) -> str:
    """Translate the small SQLite SQL subset used by app.py to PostgreSQL."""
    query = re.sub(r"\bDATETIME\b", "TIMESTAMP", query, flags=re.I)
    query = re.sub(r"\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b", "SERIAL PRIMARY KEY", query, flags=re.I)
    query = re.sub(r"\bPRAGMA\s+table_info\s*\(\s*([\w]+)\s*\)",
                   r"SELECT ordinal_position, column_name FROM information_schema.columns WHERE table_name = '\1' ORDER BY ordinal_position",
                   query, flags=re.I)
    query = re.sub(r"\bINSERT\s+OR\s+IGNORE\s+INTO\b", "INSERT INTO", query, flags=re.I)
    if re.search(r"\bINSERT\s+OR\s+REPLACE\s+INTO\s+api_cache\b", query, flags=re.I):
        query = re.sub(r"\bINSERT\s+OR\s+REPLACE\s+INTO\b", "INSERT INTO", query, flags=re.I)
        query += " ON CONFLICT (prompt) DO UPDATE SET cached_path = EXCLUDED.cached_path, timestamp = EXCLUDED.timestamp"
    elif re.search(r"\bINSERT\s+OR\s+REPLACE\s+INTO\b", query, flags=re.I):
        query = re.sub(r"\bINSERT\s+OR\s+REPLACE\s+INTO\b", "INSERT INTO", query, flags=re.I)
    query = re.sub(r"\?", "%s", query)
    if re.match(r"\s*INSERT\s+INTO\s+users\b", query, flags=re.I) and "ON CONFLICT" not in query.upper():
        query += " ON CONFLICT DO NOTHING"
    return query


class PostgresCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, query: str, params: Optional[Any] = None):
        return self._cursor.execute(_translate_query(query), params)

    def executemany(self, query: str, params):
        return self._cursor.executemany(_translate_query(query), params)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def close(self):
        return self._cursor.close()


class PostgresConnection:
    def __init__(self, connection):
        self._connection = connection

    def cursor(self):
        return PostgresCursor(self._connection.cursor())

    def commit(self):
        return self._connection.commit()

    def rollback(self):
        return self._connection.rollback()

    def close(self):
        return self._connection.close()


def connect(*args, **kwargs) -> PostgresConnection:
    del args, kwargs
    return PostgresConnection(psycopg2.connect(_DATABASE_URL, connect_timeout=10))
