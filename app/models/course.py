"""Queries for the ``course`` table (shared dropdown for Teams B, C and D)."""

from __future__ import annotations

from app.models.db import Connection, Row, fetch_all, fetch_one

_COLUMNS = "course_id, course_code, course_name"


def list_courses(conn: Connection) -> list[Row]:
    """Return all courses ordered by course code."""
    return fetch_all(
        conn,
        f"SELECT {_COLUMNS} FROM course ORDER BY course_code",
    )


def get_course(conn: Connection, course_id: int) -> Row | None:
    """Return one course by id, or ``None`` if it does not exist."""
    return fetch_one(
        conn,
        f"SELECT {_COLUMNS} FROM course WHERE course_id = %s",
        (course_id,),
    )


def get_course_by_code(conn: Connection, course_code: str) -> Row | None:
    """Return one course by its unique code, or ``None`` if it does not exist."""
    return fetch_one(
        conn,
        f"SELECT {_COLUMNS} FROM course WHERE course_code = %s",
        (course_code,),
    )
