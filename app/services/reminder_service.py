"""Reminder scheduling and persistence boundaries for agenda reminders."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Literal, Protocol

from app.services.calendar_service import AgendaKind
from app.services.time_service import WIB, now_wib, to_wib

ReminderKind = Literal["H-7", "H-3", "H-1", "H-1 19:00", "H-30M"]


@dataclass(frozen=True, slots=True)
class Reminder:
    """A reminder candidate scheduled for an agenda."""

    agenda_id: str
    kind: ReminderKind
    scheduled_at: datetime


class ReminderRepository(Protocol):
    """Persistence boundary to implement once the database schema is available."""

    def replace_pending_reminders(
        self, agenda_id: str, reminders: Sequence[Reminder]
    ) -> None:
        """Replace an agenda's unclaimed reminders atomically."""

    def cancel_pending_reminders(self, agenda_id: str) -> None:
        """Cancel an agenda's unclaimed reminders."""

    def claim_due_reminders(self, *, now: datetime, limit: int) -> Sequence[Reminder]:
        """Claim reminders transactionally using claimed_at and SKIP LOCKED."""


def build_reminders(
    agenda_id: str,
    agenda_kind: AgendaKind,
    event_at: datetime,
    now: datetime | None = None,
) -> list[Reminder]:
    """Build future reminder candidates for a task deadline or class start."""
    current_time = to_wib(now) if now is not None else now_wib()
    event_time = to_wib(event_at)

    candidates: list[tuple[ReminderKind, datetime]]
    if agenda_kind == "TUGAS":
        candidates = [
            ("H-7", event_time - timedelta(days=7)),
            ("H-3", event_time - timedelta(days=3)),
            ("H-1", event_time - timedelta(days=1)),
        ]
    elif agenda_kind == "KULIAH":
        day_before = event_time.date() - timedelta(days=1)
        candidates = [
            (
                "H-1 19:00",
                datetime.combine(day_before, time(19, 0), tzinfo=WIB),
            ),
            ("H-30M", event_time - timedelta(minutes=30)),
        ]
    else:
        raise ValueError("Agenda kind must be TUGAS or KULIAH.")

    return [
        Reminder(agenda_id, kind, scheduled_at)
        for kind, scheduled_at in candidates
        if scheduled_at >= current_time
    ]


def sync_agenda_reminders(
    repository: ReminderRepository,
    agenda_id: str,
    agenda_kind: AgendaKind,
    event_at: datetime,
    now: datetime | None = None,
) -> list[Reminder]:
    """Replace pending reminders after an agenda's schedule changes."""
    reminders = build_reminders(agenda_id, agenda_kind, event_at, now)
    repository.replace_pending_reminders(agenda_id, reminders)
    return reminders


def cancel_agenda_reminders(repository: ReminderRepository, agenda_id: str) -> None:
    """Cancel pending reminders when an agenda is deleted."""
    repository.cancel_pending_reminders(agenda_id)


def claim_due_reminders(
    repository: ReminderRepository,
    now: datetime | None = None,
    limit: int = 100,
) -> Sequence[Reminder]:
    """Delegate a safe cron claim to a repository implementation.

    The eventual PostgreSQL adapter must claim rows in a transaction using
    ``claimed_at`` and ``FOR UPDATE SKIP LOCKED`` to avoid duplicate delivery.
    """
    if limit < 1:
        raise ValueError("Claim limit must be at least 1.")
    current_time = to_wib(now) if now is not None else now_wib()
    return repository.claim_due_reminders(now=current_time, limit=limit)
