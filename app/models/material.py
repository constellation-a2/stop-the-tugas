"""Queries for the ``material`` table (Team D).

Materials are **CRD only** (Create, Read, Delete). This module intentionally has
no update function. File validation (``.pdf``, ``%PDF-`` header, <= 10 MB) is done
in ``app/services/``; the schema also enforces PDF MIME type and size.
"""

from __future__ import annotations

from app.models.db import Connection, Row, fetch_all, fetch_one, fetch_returning

_COLUMNS = (
    "material_id, title, file_nm, file_pth, file_sz, mime_type, "
    "uploaded_at, course_id, creator"
)

_SELECT_WITH_COURSE = """
SELECT m.material_id, m.title, m.file_nm, m.file_pth, m.file_sz, m.mime_type,
       m.uploaded_at, m.course_id, m.creator, c.course_code, c.course_name
FROM material m
JOIN course c ON c.course_id = m.course_id
"""


def create_material(
    conn: Connection,
    *,
    title: str,
    file_nm: str,
    file_pth: str,
    file_sz: int,
    mime_type: str,
    course_id: int,
    creator: str,
) -> Row:
    """Insert a material record and return the created row.

    Args:
        conn: Open connection.
        title: Material title (max 200 characters).
        file_nm: Original file name.
        file_pth: Storage path or URL (persistent storage on Vercel).
        file_sz: Size in bytes (1 to 10485760).
        mime_type: Must be ``application/pdf``.
        course_id: Course label (required).
        creator: Creator name (no login system).
    """
    return fetch_returning(
        conn,
        f"""
        INSERT INTO material (title, file_nm, file_pth, file_sz, mime_type,
                              course_id, creator)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING {_COLUMNS}
        """,
        (title, file_nm, file_pth, file_sz, mime_type, course_id, creator),
    )


def get_material(conn: Connection, material_id: int) -> Row | None:
    """Return one material (with course code/name) or ``None``."""
    return fetch_one(
        conn,
        f"{_SELECT_WITH_COURSE} WHERE m.material_id = %s",
        (material_id,),
    )


def list_materials(conn: Connection, course_id: int | None = None) -> list[Row]:
    """Return materials, newest first, optionally filtered by course."""
    if course_id is None:
        return fetch_all(
            conn,
            f"{_SELECT_WITH_COURSE} ORDER BY m.uploaded_at DESC, m.material_id DESC",
        )
    return fetch_all(
        conn,
        f"""
        {_SELECT_WITH_COURSE}
        WHERE m.course_id = %s
        ORDER BY m.uploaded_at DESC, m.material_id DESC
        """,
        (course_id,),
    )


def delete_material(conn: Connection, material_id: int) -> Row | None:
    """Delete a material record and return it, or ``None`` if it did not exist.

    The returned row contains ``file_pth`` so the service can also remove the
    stored file from persistent storage.
    """
    return fetch_one(
        conn,
        f"DELETE FROM material WHERE material_id = %s RETURNING {_COLUMNS}",
        (material_id,),
    )
