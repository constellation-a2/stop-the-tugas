from datetime import UTC, date, datetime, time, timedelta

import pytest

from app.services.calendar_service import (
    Agenda,
    AgendaValidationError,
    agendas_for_day,
    empty_date_message,
    group_agendas_by_day,
    validate_agenda,
)
from app.services.materials_service import (
    MAX_PDF_SIZE_BYTES,
    Material,
    MaterialNotFoundError,
    MaterialValidationError,
    create_material,
    delete_material,
    get_material,
    list_materials,
    validate_pdf,
)
from app.services.reminder_service import (
    Reminder,
    build_reminders,
    cancel_agenda_reminders,
    claim_due_reminders,
    sync_agenda_reminders,
)
from app.services.time_service import (
    WIB,
    format_date,
    format_datetime,
    format_time,
    parse_date,
    parse_datetime,
    parse_time,
    time_until,
)


def test_time_helpers_parse_and_format_wib() -> None:
    parsed = parse_datetime("2026-05-20T09:30:00")
    assert parsed.tzinfo == WIB
    assert format_datetime(parsed) == "2026-05-20T09:30:00+07:00"
    assert parse_date("2026-05-20") == date(2026, 5, 20)
    assert parse_date(date(2026, 5, 20)) == date(2026, 5, 20)
    assert format_date(date(2026, 5, 20)) == "2026-05-20"
    assert parse_time("19:00") == time(19, 0)
    assert parse_time(time(19, 0)) == time(19, 0)
    assert format_time(time(19, 0)) == "19:00:00"
    assert time_until(parsed, datetime(2026, 5, 20, 8, 30, tzinfo=WIB)) == timedelta(
        hours=1
    )


def test_time_helpers_reject_invalid_or_offset_local_values() -> None:
    with pytest.raises(ValueError):
        parse_date("20-05-2026")
    with pytest.raises(ValueError):
        parse_time("19:00+07:00")


def test_agenda_validation_and_calendar_grouping_use_wib_dates() -> None:
    agenda = validate_agenda(
        Agenda(
            id="a1",
            title="Lab",
            kind="KULIAH",
            start_at=datetime(2026, 5, 1, 0, 30, tzinfo=UTC),
            end_at=datetime(2026, 5, 1, 1, 30, tzinfo=UTC),
            class_loc="R-1",
        )
    )
    assert agenda.start_at == datetime(2026, 5, 1, 7, 30, tzinfo=WIB)
    assert list(group_agendas_by_day([agenda], 2026, 5)) == [date(2026, 5, 1)]
    assert agendas_for_day([agenda], date(2026, 5, 1)) == [agenda]
    assert empty_date_message([agenda], date(2026, 5, 2)) == (
        "Tidak ada tugas atau jadwal kuliah pada tanggal ini"
    )


def test_agenda_validation_rejects_bad_range_and_missing_class_location() -> None:
    with pytest.raises(AgendaValidationError):
        validate_agenda(
            Agenda(
                id="a1",
                title="Class",
                kind="KULIAH",
                start_at=datetime(2026, 5, 1, 10, tzinfo=WIB),
            )
        )
    with pytest.raises(AgendaValidationError):
        validate_agenda(
            Agenda(
                id="a2",
                title="Task",
                kind="TUGAS",
                start_at=datetime(2026, 5, 2, 10, tzinfo=WIB),
                end_at=datetime(2026, 5, 1, 10, tzinfo=WIB),
            )
        )


def test_task_reminders_only_include_remaining_future_intervals() -> None:
    now = datetime(2026, 5, 15, 10, tzinfo=WIB)
    all_intervals = build_reminders(
        "task-1",
        "TUGAS",
        datetime(2026, 5, 20, 10, tzinfo=WIB),
        datetime(2026, 5, 10, 10, tzinfo=WIB),
    )
    assert [reminder.kind for reminder in all_intervals] == ["H-7", "H-3", "H-1"]

    reminders = build_reminders(
        "task-1", "TUGAS", datetime(2026, 5, 20, 10, tzinfo=WIB), now
    )
    assert [reminder.kind for reminder in reminders] == ["H-3", "H-1"]
    assert all(reminder.scheduled_at >= now for reminder in reminders)
    assert (
        build_reminders("task-1", "TUGAS", datetime(2026, 5, 14, 10, tzinfo=WIB), now)
        == []
    )


def test_class_reminders_use_prior_day_1900_and_thirty_minutes_before() -> None:
    reminders = build_reminders(
        "class-1",
        "KULIAH",
        datetime(2026, 5, 20, 8, 0, tzinfo=WIB),
        datetime(2026, 5, 18, 12, tzinfo=WIB),
    )
    assert [(item.kind, item.scheduled_at) for item in reminders] == [
        ("H-1 19:00", datetime(2026, 5, 19, 19, 0, tzinfo=WIB)),
        ("H-30M", datetime(2026, 5, 20, 7, 30, tzinfo=WIB)),
    ]


class FakeReminderRepository:
    def __init__(self) -> None:
        self.replaced: tuple[str, list[Reminder]] | None = None
        self.cancelled: str | None = None
        self.claim_args: tuple[datetime, int] | None = None

    def replace_pending_reminders(
        self, agenda_id: str, reminders: list[Reminder]
    ) -> None:
        self.replaced = agenda_id, list(reminders)

    def cancel_pending_reminders(self, agenda_id: str) -> None:
        self.cancelled = agenda_id

    def claim_due_reminders(self, *, now: datetime, limit: int) -> list[Reminder]:
        self.claim_args = now, limit
        return []


def test_reminder_repository_boundaries_sync_cancel_and_claim() -> None:
    repository = FakeReminderRepository()
    now = datetime(2026, 5, 15, 10, tzinfo=WIB)
    reminders = sync_agenda_reminders(
        repository,
        "task-1",
        "TUGAS",
        datetime(2026, 5, 20, 10, tzinfo=WIB),
        now,
    )
    cancel_agenda_reminders(repository, "task-1")
    assert repository.replaced == ("task-1", reminders)
    assert repository.cancelled == "task-1"
    assert claim_due_reminders(repository, now, 25) == []
    assert repository.claim_args == (now, 25)
    with pytest.raises(ValueError):
        claim_due_reminders(repository, now, 0)


def test_pdf_validation_enforces_signature_mime_and_size_boundary() -> None:
    assert validate_pdf("notes.PDF", "application/pdf", b"%PDF-example") == 12
    assert (
        validate_pdf(
            "large.pdf",
            "application/pdf",
            b"%PDF-" + b"x" * (MAX_PDF_SIZE_BYTES - len(b"%PDF-")),
        )
        == MAX_PDF_SIZE_BYTES
    )
    with pytest.raises(MaterialValidationError):
        validate_pdf("notes.txt", "application/pdf", b"%PDF-example")
    with pytest.raises(MaterialValidationError):
        validate_pdf("notes.pdf", "text/plain", b"%PDF-example")
    with pytest.raises(MaterialValidationError):
        validate_pdf("notes.pdf", "application/pdf", b"not a pdf")
    with pytest.raises(MaterialValidationError):
        validate_pdf(
            "large.pdf", "application/pdf", b"%PDF-" + b"x" * MAX_PDF_SIZE_BYTES
        )


class FakeMaterialsRepository:
    def __init__(self) -> None:
        self.material = Material(
            id="m1",
            course_label="Math",
            title="Notes",
            creator="Ari",
            file_name="notes.pdf",
            content_type="application/pdf",
            size_bytes=12,
            storage_key="materials/m1",
        )
        self.created_args: dict[str, object] | None = None

    def create_material(
        self,
        *,
        course_label: str,
        title: str,
        creator: str,
        file_name: str,
        content_type: str,
        size_bytes: int,
        content: bytes,
    ) -> Material:
        self.created_args = {
            "course_label": course_label,
            "title": title,
            "creator": creator,
            "file_name": file_name,
            "content_type": content_type,
            "size_bytes": size_bytes,
            "content": content,
        }
        return self.material

    def list_materials(self) -> list[Material]:
        return [self.material]

    def get_material(self, material_id: str) -> Material | None:
        return self.material if material_id == self.material.id else None

    def delete_material(self, material_id: str) -> bool:
        return material_id == self.material.id


def test_material_crd_validates_and_has_no_update_operation() -> None:
    repository = FakeMaterialsRepository()
    material = create_material(
        repository,
        course_label=" Math ",
        title=" Notes ",
        creator=" Ari ",
        file_name="notes.pdf",
        content_type="application/pdf",
        content=b"%PDF-example",
    )
    assert material == repository.material
    assert repository.created_args is not None
    assert repository.created_args["course_label"] == "Math"
    assert repository.created_args["size_bytes"] == 12
    assert list_materials(repository) == [material]
    assert get_material(repository, "m1") == material
    delete_material(repository, "m1")
    with pytest.raises(MaterialNotFoundError):
        get_material(repository, "missing")
    with pytest.raises(MaterialNotFoundError):
        delete_material(repository, "missing")
    with pytest.raises(MaterialValidationError):
        create_material(
            repository,
            course_label="Math",
            title="",
            creator="Ari",
            file_name="notes.pdf",
            content_type="application/pdf",
            content=b"%PDF-example",
        )
