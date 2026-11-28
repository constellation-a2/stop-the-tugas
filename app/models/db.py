"""Low-level PostgreSQL helpers shared by all model modules.

Model functions receive an open DB-API connection (psycopg) and never commit
on their own. Callers (services) group multi-step writes with
:func:`transaction`. All SQL uses bound parameters (``%s``); user input is
never interpolated into SQL strings.
"""

from __future__ import annotations

import os
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any

Row = dict[str, Any]
Params = Sequence[Any]
Connection = Any  # DB-API / psycopg connection


def get_connection() -> Connection:
    """Open a connection to Neon using the ``DATABASE_URL`` environment variable.

    Returns:
        A new psycopg connection (autocommit off). The caller must close it.

    Raises:
        RuntimeError: If ``DATABASE_URL`` is not set.
    """
    import psycopg  # lazy import: unit tests do not need a live driver

    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg.connect(url)


@contextmanager
def transaction(conn: Connection) -> Iterator[Connection]:
    """Commit on success, roll back on any exception.

    Args:
        conn: Open connection.

    Yields:
        The same connection, for convenience.
    """
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    else:
        conn.commit()


def fetch_all(conn: Connection, sql: str, params: Params = ()) -> list[Row]:
    """Run a statement and return every result row as a dict."""
    with conn.cursor() as cur:
        cur.execute(sql, params)
        if cur.description is None:
            return []
        columns = [col[0] for col in cur.description]
        return [dict(zip(columns, values, strict=True)) for values in cur.fetchall()]


def fetch_one(conn: Connection, sql: str, params: Params = ()) -> Row | None:
    """Run a statement and return the first row, or ``None`` if there is none."""
    rows = fetch_all(conn, sql, params)
    return rows[0] if rows else None


def fetch_returning(conn: Connection, sql: str, params: Params = ()) -> Row:
    """Run an ``INSERT``/``UPDATE ... RETURNING`` statement that must return a row.

    Raises:
        RuntimeError: If the statement returned no row.
    """
    row = fetch_one(conn, sql, params)
    if row is None:
        raise RuntimeError("Statement did not return a row")
    return row


def execute(conn: Connection, sql: str, params: Params = ()) -> int:
    """Run a statement and return the number of affected rows."""
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return int(cur.rowcount)
