"""Unit tests for app.models (SQL shape and argument handling, no live database)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import pytest

from app.models import agenda, db, material, reminder

WIB = timezone(timedelta(hours=7))


class FakeCursor:
    def __init__(self, conn: FakeConnection) -> None:
        self._conn = conn
        self._rows: list[tuple[Any, ...]] = []
        self.description: list[tuple[str]] | None = None
        self.rowcount = 0

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def execute(self, sql: str, params: Any = ()) -> None:
        self._conn.calls.append((" ".join(sql.split()), tuple(params)))
        rows = self._conn.results.pop(0) if self._conn.results else []
        self._rows = [tuple(row.values()) for row in rows]
        self.description = [(key,) for key in rows[0]] if rows else None
        self.rowcount = self._conn.rowcount

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._rows


class FakeConnection:
    def __init__(
        self,
        results: list[list[dict[str, Any]]] | None = None,
        rowcount: int = 1,
    ) -> None:
        self.results = results or []
        self.rowcount = rowcount
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self.commits = 0
        self.rollbacks = 0

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


def test_transaction_commits_on_success_and_rolls_back_on_error() -> None:
    conn = FakeConnection()
    with db.transaction(conn):
        pass
    assert (conn.commits, conn.rollbacks) == (1, 0)

    with pytest.raises(RuntimeError), db.transaction(conn):
        raise RuntimeError("boom")
    assert (conn.commits, conn.rollbacks) == (1, 1)


def test_create_agenda_rejects_invalid_type_without_touching_db() -> None:
    conn = FakeConnection()
    with pytest.raises(ValueError):
        agenda.create_agenda(conn, title="x", agenda_typ="UJIAN", creator="Seed")
    assert conn.calls == []


def test_create_agenda_rejects_naive_datetime() -> None:
    conn = FakeConnection()
    with pytest.raises(ValueError):
        agenda.create_agenda(
            conn,
            title="x",
            agenda_typ="TUGAS",
            creator="Seed",
            deadline_dttm=datetime(2026, 12, 10, 23, 59),
        )
    assert conn.calls == []


def test_create_agenda_uses_bound_parameters() -> None:
    title = "Robert'); DROP TABLE agenda;--"
    conn = FakeConnection(results=[[{"agenda_id": 1, "title": title}]])
    row = agenda.create_agenda(conn, title=title, agenda_typ="KULIAH", creator="Seed")

    sql, params = conn.calls[0]
    assert title not in sql
    assert title in params
    assert row["agenda_id"] == 1


def test_delete_agenda_reports_whether_a_row_was_deleted() -> None:
    assert agenda.delete_agenda(FakeConnection(rowcount=1), 1) is True
    assert agenda.delete_agenda(FakeConnection(rowcount=0), 1) is False


def test_list_agendas_on_date_uses_wib_day_bounds() -> None:
    conn = FakeConnection()
    agenda.list_agendas_on_date(conn, date(2026, 12, 7))

    start, end = conn.calls[0][1]
    assert start.utcoffset() == timedelta(hours=7)
    assert (start.year, start.month, start.day, start.hour) == (2026, 12, 7, 0)
    assert end - start == timedelta(days=1)


def test_month_bounds_roll_over_december_and_validate_month() -> None:
    start, end = agenda._month_bounds(2026, 12)
    assert (end.year, end.month, end.day) == (2027, 1, 1)
    assert start.utcoffset() == timedelta(hours=7)
    with pytest.raises(ValueError):
        agenda._month_bounds(2026, 13)


def test_create_reminder_rejects_naive_datetime() -> None:
    conn = FakeConnection()
    with pytest.raises(ValueError):
        reminder.create_reminder(
            conn,
            agenda_id=1,
            reminder_typ="H-30M",
            scheduled_at=datetime(2026, 12, 7, 8, 45),
        )
    assert conn.calls == []


def test_create_reminders_inserts_each_item() -> None:
    conn = FakeConnection(results=[[{"reminder_id": 1}], [{"reminder_id": 2}]])
    rows = reminder.create_reminders(
        conn,
        7,
        [
            ("H-3", datetime(2026, 12, 7, 23, 59, tzinfo=WIB)),
            ("H-1", datetime(2026, 12, 9, 23, 59, tzinfo=WIB)),
        ],
    )
    assert [r["reminder_id"] for r in rows] == [1, 2]
    assert len(conn.calls) == 2


def test_claim_due_reminders_locks_rows_and_stamps_claimed_at() -> None:
    conn = FakeConnection()
    reminder.claim_due_reminders(conn, limit=25)

    sql, params = conn.calls[0]
    assert "FOR UPDATE SKIP LOCKED" in sql
    assert "claimed_at IS NULL" in sql
    assert "SET claimed_at = now()" in sql
    assert params == (25,)


def test_delete_pending_reminders_only_targets_unclaimed_rows() -> None:
    conn = FakeConnection(rowcount=2)
    assert reminder.delete_pending_reminders(conn, 5) == 2
    sql, params = conn.calls[0]
    assert "claimed_at IS NULL" in sql
    assert params == (5,)


def test_material_module_is_create_read_delete_only() -> None:
    public = [name for name in dir(material) if not name.startswith("_")]
    assert not [name for name in public if name.startswith(("update", "edit"))]
    assert {"create_material", "get_material", "list_materials", "delete_material"} <= set(public)


def test_delete_material_returns_deleted_row_for_file_cleanup() -> None:
    conn = FakeConnection(results=[[{"material_id": 3, "file_pth": "blob/x.pdf"}]])
    row = material.delete_material(conn, 3)
    assert row is not None
    assert row["file_pth"] == "blob/x.pdf"
    assert "RETURNING" in conn.calls[0][0]
