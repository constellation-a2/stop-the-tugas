"""PDF validation and CRD operations for study materials."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

MAX_PDF_SIZE_BYTES = 10 * 1024 * 1024
PDF_CONTENT_TYPE = "application/pdf"
PDF_SIGNATURE = b"%PDF-"


class MaterialValidationError(ValueError):
    """Raised when PDF content or material metadata is invalid."""


class MaterialNotFoundError(LookupError):
    """Raised when a requested material does not exist."""


@dataclass(frozen=True, slots=True)
class Material:
    """Material metadata returned by the persistence layer."""

    id: str
    course_label: str
    title: str
    creator: str
    file_name: str
    content_type: str
    size_bytes: int
    storage_key: str


class MaterialsRepository(Protocol):
    """Persistence boundary for metadata and persistent file storage."""

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
        """Persist a material and its PDF using durable storage."""

    def list_materials(self) -> Sequence[Material]:
        """Return material metadata."""

    def get_material(self, material_id: str) -> Material | None:
        """Return material metadata, or None when it does not exist."""

    def delete_material(self, material_id: str) -> bool:
        """Delete a material and its stored PDF; return whether it existed."""


def validate_pdf(file_name: str, content_type: str, content: bytes) -> int:
    """Validate the PDF name, MIME type, signature, and size.

    Returns the validated content size in bytes.
    """
    if not file_name.lower().endswith(".pdf"):
        raise MaterialValidationError("Only .pdf files are allowed.")
    if content_type.split(";", maxsplit=1)[0].strip().lower() != PDF_CONTENT_TYPE:
        raise MaterialValidationError("Content type must be application/pdf.")
    if len(content) > MAX_PDF_SIZE_BYTES:
        raise MaterialValidationError("PDF files must not exceed 10 MB.")
    if not content.startswith(PDF_SIGNATURE):
        raise MaterialValidationError("File content does not have a PDF header.")
    return len(content)


def create_material(
    repository: MaterialsRepository,
    *,
    course_label: str,
    title: str,
    creator: str,
    file_name: str,
    content_type: str,
    content: bytes,
) -> Material:
    """Validate and create a material without writing to local disk."""
    normalized_course_label = course_label.strip()
    normalized_title = title.strip()
    normalized_creator = creator.strip()
    if not normalized_course_label:
        raise MaterialValidationError("Course label is required.")
    if not normalized_title:
        raise MaterialValidationError("Title is required.")
    if not normalized_creator:
        raise MaterialValidationError("Creator is required.")

    size_bytes = validate_pdf(file_name, content_type, content)
    return repository.create_material(
        course_label=normalized_course_label,
        title=normalized_title,
        creator=normalized_creator,
        file_name=file_name,
        content_type=PDF_CONTENT_TYPE,
        size_bytes=size_bytes,
        content=content,
    )


def list_materials(repository: MaterialsRepository) -> Sequence[Material]:
    """Return all materials."""
    return repository.list_materials()


def get_material(repository: MaterialsRepository, material_id: str) -> Material:
    """Return one material or raise when it is missing."""
    material = repository.get_material(material_id)
    if material is None:
        raise MaterialNotFoundError(f"Material {material_id!r} was not found.")
    return material


def delete_material(repository: MaterialsRepository, material_id: str) -> None:
    """Delete one material or raise when it is missing."""
    if not repository.delete_material(material_id):
        raise MaterialNotFoundError(f"Material {material_id!r} was not found.")
