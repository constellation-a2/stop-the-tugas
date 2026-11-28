"""Queries for the ``agenda`` table (``TUGAS`` and ``KULIAH``).

Agendas are Create/Delete only in the MVP. Deleting an agenda also removes its
reminders through ``ON DELETE CASCADE``. Calendar day/month filters use WIB
(``Asia/Jakarta``); an agenda is placed on the day of its start time, or of its
deadline when it has no start time.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.models.db import Connection, Row, execute, fetch_all, fetch_one, fetch_returning

WIB = ZoneInfo("Asia/Jakarta")
AGENDA_TYPES = ("TUGAS", "KULIAH")

_COLUMNS = (
    "agenda_id, title, agenda_typ, description, start_dttm, end_dttm, "
    "deadline_dttm, class_loc, created_at, course_id, creator"
)

_SELECT_WITH_COURSE = """
SELECT a.agenda_id, a.title, a.agenda_typ, a.description, a.start_dttm,
       a.end_dttm, a.deadline_dttm, a.class_loc, a.created_at, a.creator,
       a.course_id, c.course_code, c.course_name
FROM agenda a
LEFT JOIN course c ON c.course_id = a.course_id
"""

_EVENT_TIME = "COALESCE(a.start_dttm, a.deadline_dttm)"


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    """Return the WIB-aware ``[start, end)`` bounds of a calendar day."""
    start = datetime(day.year, day.month, day.day, tzinfo=WIB)
    return start, start + timedelta(days=1)


def _month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    """Return the WIB-aware ``[start, end)`` bounds of a calendar month."""
    if not 1 <= month <= 12:
        raise ValueError(f"month must be between 1 and 12, got {month}")
    start = datetime(year, month, 1, tzinfo=WIB)
    end = datetime(year + (month == 12), month % 12 + 1, 1, tzinfo=WIB)
    return start, end


def create_agenda(
    conn: Connection,
    *,
    title: str,
    agenda_typ: str,
    creator: str,
    course_id: int | None = None,
    description: str | None = None,
    start_dttm: datetime | None = None,
    end_dttm: datetime | None = None,
    deadline_dttm: datetime | None = None,
    class_loc: str | None = None,
) -> Row:
    """Insert an agenda and return the created row.

    Args:
        conn: Open connection.
        title: Agenda title (max 200 characters).
        agenda_typ: ``"TUGAS"`` or ``"KULIAH"``.
        creator: Creator name (no login system; max 100 characters).
        course_id: Optional course the agenda belongs to.
        description: Optional notes.
        start_dttm: Start time (timezone-aware), mainly for ``KULIAH``.
        end_dttm: End time (timezone-aware).
        deadline_dttm: Deadline (timezone-aware), mainly for ``TUGAS``.
        class_loc: Classroom code for ``KULIAH``.

    Returns:
        The inserted row.

    Raises:
        ValueError: If ``agenda_typ`` is invalid or a datetime is naive.
    """
    if agenda_typ not in AGENDA_TYPES:
        raise ValueError(f"agenda_typ must be one of {AGENDA_TYPES}, got {agenda_typ!r}")
    for name, value in (
        ("start_dttm", start_dttm),
        ("end_dttm", end_dttm),
        ("deadline_dttm", deadline_dttm),
    ):
        if value is not None and value.tzinfo is None:
            raise ValueError(f"{name} must be timezone-aware (use WIB)")

    return fetch_returning(
        conn,
        f"""
        INSERT INTO agenda (title, agenda_typ, description, start_dttm, end_dttm,
                            deadline_dttm, class_loc, course_id, creator)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING {_COLUMNS}
        """,
        (
            title,
            agenda_typ,
            description,
            start_dttm,
            end_dttm,
            deadline_dttm,
            class_loc,
            course_id,
            creator,
        ),
    )


def get_agenda(conn: Connection, agenda_id: int) -> Row | None:
    """Return one agenda (with course code/name) or ``None``."""
    return fetch_one(
        conn,
        f"{_SELECT_WITH_COURSE} WHERE a.agenda_id = %s",
        (agenda_id,),
    )


def delete_agenda(conn: Connection, agenda_id: int) -> bool:
    """Delete an agenda; its reminders are removed by ``ON DELETE CASCADE``.

    Returns:
        ``True`` if a row was deleted, ``False`` if the agenda did not exist.
    """
    return execute(conn, "DELETE FROM agenda WHERE agenda_id = %s", (agenda_id,)) > 0


def list_agendas_on_date(conn: Connection, day: date) -> list[Row]:
    """Return the agendas that fall on ``day`` in WIB, earliest first."""
    start, end = _day_bounds(day)
    return fetch_all(
        conn,
        f"""
        {_SELECT_WITH_COURSE}
        WHERE {_EVENT_TIME} >= %s AND {_EVENT_TIME} < %s
        ORDER BY {_EVENT_TIME}, a.agenda_id
        """,
        (start, end),
    )


def list_dates_with_agenda(conn: Connection, year: int, month: int) -> list[date]:
    """Return the WIB dates in a month that have at least one agenda."""
    start, end = _month_bounds(year, month)
    rows = fetch_all(
        conn,
        f"""
        SELECT DISTINCT ({_EVENT_TIME} AT TIME ZONE 'Asia/Jakarta')::date AS day
        FROM agenda a
        WHERE {_EVENT_TIME} >= %s AND {_EVENT_TIME} < %s
        ORDER BY day
        """,
        (start, end),
    )
    return [row["day"] for row in rows]
