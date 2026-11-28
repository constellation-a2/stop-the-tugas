"""Queries for the ``reminder`` table (Team B).

Reminders are removed automatically when their agenda is deleted
(``ON DELETE CASCADE``). Cron workers use :func:`claim_due_reminders`, which
claims rows atomically with ``claimed_at`` and ``FOR UPDATE SKIP LOCKED`` so
two overlapping runs never deliver the same reminder twice.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from app.models.db import Connection, Row, execute, fetch_all, fetch_returning

_COLUMNS = "reminder_id, reminder_typ, scheduled_at, created_at, agenda_id, claimed_at"


def create_reminder(
    conn: Connection,
    *,
    agenda_id: int,
    reminder_typ: str,
    scheduled_at: datetime,
) -> Row:
    """Insert one reminder and return the created row.

    Args:
        conn: Open connection.
        agenda_id: Agenda the reminder belongs to.
        reminder_typ: Reminder label such as ``"H-7"`` or ``"H-30M"``.
        scheduled_at: When to deliver it (timezone-aware).

    Raises:
        ValueError: If ``scheduled_at`` is naive.
    """
    if scheduled_at.tzinfo is None:
        raise ValueError("scheduled_at must be timezone-aware (use WIB)")
    return fetch_returning(
        conn,
        f"""
        INSERT INTO reminder (reminder_typ, scheduled_at, agenda_id)
        VALUES (%s, %s, %s)
        RETURNING {_COLUMNS}
        """,
        (reminder_typ, scheduled_at, agenda_id),
    )


def create_reminders(
    conn: Connection,
    agenda_id: int,
    items: Sequence[tuple[str, datetime]],
) -> list[Row]:
    """Insert several ``(reminder_typ, scheduled_at)`` reminders for one agenda."""
    return [
        create_reminder(
            conn,
            agenda_id=agenda_id,
            reminder_typ=reminder_typ,
            scheduled_at=scheduled_at,
        )
        for reminder_typ, scheduled_at in items
    ]


def list_reminders_for_agenda(conn: Connection, agenda_id: int) -> list[Row]:
    """Return all reminders of an agenda ordered by schedule."""
    return fetch_all(
        conn,
        f"SELECT {_COLUMNS} FROM reminder WHERE agenda_id = %s ORDER BY scheduled_at",
        (agenda_id,),
    )


def delete_pending_reminders(conn: Connection, agenda_id: int) -> int:
    """Delete reminders of an agenda that were not claimed yet.

    Used to recalculate reminders: delete the pending ones, then insert the new
    schedule. Already-claimed reminders are kept as delivery history.

    Returns:
        Number of deleted reminders.
    """
    return execute(
        conn,
        "DELETE FROM reminder WHERE agenda_id = %s AND claimed_at IS NULL",
        (agenda_id,),
    )


def claim_due_reminders(conn: Connection, limit: int = 100) -> list[Row]:
    """Atomically claim due, unclaimed reminders for delivery.

    A single statement selects due rows with ``FOR UPDATE SKIP LOCKED``, stamps
    ``claimed_at``, and returns them joined with their agenda and course so the
    caller can build the push message. Call it inside a transaction.

    Args:
        conn: Open connection.
        limit: Maximum number of reminders to claim in this run.

    Returns:
        Claimed reminders with ``title``, ``agenda_typ``, ``start_dttm``,
        ``deadline_dttm``, ``class_loc`` and ``course_name``.
    """
    return fetch_all(
        conn,
        """
        WITH due AS (
            SELECT reminder_id
            FROM reminder
            WHERE claimed_at IS NULL AND scheduled_at <= now()
            ORDER BY scheduled_at
            LIMIT %s
            FOR UPDATE SKIP LOCKED
        ),
        claimed AS (
            UPDATE reminder r
            SET claimed_at = now()
            FROM due
            WHERE r.reminder_id = due.reminder_id
            RETURNING r.reminder_id, r.reminder_typ, r.scheduled_at, r.agenda_id
        )
        SELECT cl.reminder_id, cl.reminder_typ, cl.scheduled_at, cl.agenda_id,
               a.title, a.agenda_typ, a.start_dttm, a.deadline_dttm, a.class_loc,
               c.course_name
        FROM claimed cl
        JOIN agenda a ON a.agenda_id = cl.agenda_id
        LEFT JOIN course c ON c.course_id = a.course_id
        ORDER BY cl.scheduled_at, cl.reminder_id
        """,
        (limit,),
    )


def release_claim(conn: Connection, reminder_id: int) -> bool:
    """Release a claim so a failed delivery can be retried by the next cron run.

    Returns:
        ``True`` if the reminder existed and was claimed.
    """
    return (
        execute(
            conn,
            "UPDATE reminder SET claimed_at = NULL "
            "WHERE reminder_id = %s AND claimed_at IS NOT NULL",
            (reminder_id,),
        )
        > 0
    )
