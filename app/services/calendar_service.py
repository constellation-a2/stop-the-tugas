"""Validation and calendar grouping for TUGAS and KULIAH agendas."""

from dataclasses import dataclass, replace
from datetime import date, datetime
from typing import Literal, cast

from app.services.time_service import to_wib

AgendaKind = Literal["TUGAS", "KULIAH"]


class AgendaValidationError(ValueError):
    """Raised when an agenda is incomplete or has an invalid time range."""


@dataclass(frozen=True, slots=True)
class Agenda:
    """Validated agenda data used by the service layer."""

    id: str
    title: str
    kind: AgendaKind
    start_at: datetime
    end_at: datetime | None = None
    description: str | None = None
    class_loc: str | None = None


def validate_agenda(agenda: Agenda) -> Agenda:
    """Validate agenda fields and normalize its datetimes to WIB."""
    if not agenda.id.strip():
        raise AgendaValidationError("Agenda ID is required.")
    if not agenda.title.strip():
        raise AgendaValidationError("Agenda title is required.")
    if agenda.kind not in ("TUGAS", "KULIAH"):
        raise AgendaValidationError("Agenda kind must be TUGAS or KULIAH.")
    if agenda.kind == "KULIAH" and not (agenda.class_loc or "").strip():
        raise AgendaValidationError("Class location is required for KULIAH.")

    start_at = to_wib(agenda.start_at)
    end_at = to_wib(agenda.end_at) if agenda.end_at is not None else None
    if end_at is not None and end_at < start_at:
        raise AgendaValidationError(
            "Agenda end time must not be before its start time."
        )

    return replace(agenda, start_at=start_at, end_at=end_at)


def agendas_for_day(agendas: list[Agenda], selected_date: date) -> list[Agenda]:
    """Return agendas starting on a selected WIB date in chronological order."""
    matching = [
        agenda for agenda in agendas if to_wib(agenda.start_at).date() == selected_date
    ]
    return sorted(matching, key=lambda agenda: to_wib(agenda.start_at))


def group_agendas_by_day(
    agendas: list[Agenda], year: int, month: int
) -> dict[date, list[Agenda]]:
    """Group agendas by their WIB start date for a calendar month."""
    first_day = date(year, month, 1)
    grouped: dict[date, list[Agenda]] = {}
    for agenda in agendas:
        local_start = to_wib(agenda.start_at)
        agenda_date = local_start.date()
        if agenda_date.year == first_day.year and agenda_date.month == first_day.month:
            grouped.setdefault(agenda_date, []).append(agenda)

    for day_agendas in grouped.values():
        day_agendas.sort(key=lambda agenda: to_wib(agenda.start_at))
    return grouped


def monthly_agenda_days(agendas: list[Agenda], year: int, month: int) -> set[date]:
    """Return WIB dates in a month that contain at least one agenda."""
    return set(group_agendas_by_day(agendas, year, month))


def empty_date_message(agendas: list[Agenda], selected_date: date) -> str | None:
    """Return the standard empty-date message when no agenda exists that day."""
    if agendas_for_day(agendas, selected_date):
        return None
    return "Tidak ada tugas atau jadwal kuliah pada tanggal ini"


def normalize_agenda_kind(value: str) -> AgendaKind:
    """Validate and normalize an agenda kind."""
    normalized = value.strip().upper()
    if normalized not in ("TUGAS", "KULIAH"):
        raise AgendaValidationError("Agenda kind must be TUGAS or KULIAH.")
    return cast(AgendaKind, normalized)
