"""Test route materials (Team D). Service di-mock, tanpa database/storage."""

import io
from unittest.mock import MagicMock

import pytest

from app.services import materials_service

PDF_BYTES = b"%PDF-1.4 isi pdf contoh"


def _form(**overrides):
    """Membuat data multipart valid; field bisa ditimpa atau dihapus (None)."""
    data = {
        "file": (io.BytesIO(PDF_BYTES), "catatan.pdf"),
        "title": "Catatan Basis Data",
        "course": "Basis Data",
        "creator": "Andi",
    }
    data.update(overrides)
    return {key: value for key, value in data.items() if value is not None}


def test_list_materials_without_filter(client, monkeypatch):
    items = [{"id": 1, "title": "Catatan"}]
    lister = MagicMock(return_value=items)
    monkeypatch.setattr(materials_service, "list_materials", lister, raising=False)

    response = client.get("/api/materials")

    assert response.status_code == 200
    assert response.get_json() == {"materials": items}
    lister.assert_called_once_with(None)


def test_list_materials_with_course_filter(client, monkeypatch):
    lister = MagicMock(return_value=[])
    monkeypatch.setattr(materials_service, "list_materials", lister, raising=False)

    response = client.get("/api/materials?course=Basis Data")

    assert response.status_code == 200
    lister.assert_called_once_with("Basis Data")


def test_create_material_success(client, monkeypatch):
    create = MagicMock(return_value={"id": 3, "title": "Catatan Basis Data"})
    monkeypatch.setattr(materials_service, "create_material", create, raising=False)

    response = client.post(
        "/api/materials", data=_form(), content_type="multipart/form-data"
    )

    assert response.status_code == 201
    assert response.get_json()["id"] == 3
    args = create.call_args.args
    assert args[0].filename == "catatan.pdf"
    assert args[1:] == ("Catatan Basis Data", "Basis Data", "Andi")


def test_create_material_without_file_returns_400(client, monkeypatch):
    create = MagicMock()
    monkeypatch.setattr(materials_service, "create_material", create, raising=False)

    response = client.post(
        "/api/materials", data=_form(file=None), content_type="multipart/form-data"
    )

    assert response.status_code == 400
    create.assert_not_called()


@pytest.mark.parametrize("missing", ["title", "course", "creator"])
def test_create_material_missing_metadata_returns_400(client, monkeypatch, missing):
    create = MagicMock()
    monkeypatch.setattr(materials_service, "create_material", create, raising=False)

    response = client.post(
        "/api/materials",
        data=_form(**{missing: ""}),
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    create.assert_not_called()


def test_create_material_service_value_error_returns_400(client, monkeypatch):
    create = MagicMock(side_effect=ValueError("Hanya file PDF yang diperbolehkan"))
    monkeypatch.setattr(materials_service, "create_material", create, raising=False)

    response = client.post(
        "/api/materials", data=_form(), content_type="multipart/form-data"
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Hanya file PDF yang diperbolehkan"}


def test_create_material_too_large_returns_413(app, client):
    app.config["MAX_CONTENT_LENGTH"] = 10

    response = client.post(
        "/api/materials", data=_form(), content_type="multipart/form-data"
    )

    assert response.status_code == 413
    assert "10 MB" in response.get_json()["error"]


def test_get_material_file_preview(client, monkeypatch):
    getter = MagicMock(return_value={"filename": "catatan.pdf", "content": PDF_BYTES})
    monkeypatch.setattr(materials_service, "get_material_file", getter, raising=False)

    response = client.get("/api/materials/1/file")

    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data == PDF_BYTES
    assert "attachment" not in response.headers.get("Content-Disposition", "")
    getter.assert_called_once_with(1)


def test_get_material_file_download(client, monkeypatch):
    getter = MagicMock(return_value={"filename": "catatan.pdf", "content": PDF_BYTES})
    monkeypatch.setattr(materials_service, "get_material_file", getter, raising=False)

    response = client.get("/api/materials/1/file?download=1")

    assert response.status_code == 200
    disposition = response.headers["Content-Disposition"]
    assert "attachment" in disposition
    assert "catatan.pdf" in disposition


def test_get_material_file_not_found_returns_404(client, monkeypatch):
    monkeypatch.setattr(
        materials_service,
        "get_material_file",
        MagicMock(return_value=None),
        raising=False,
    )

    response = client.get("/api/materials/999/file")

    assert response.status_code == 404


def test_delete_material_success(client, monkeypatch):
    delete = MagicMock(return_value=True)
    monkeypatch.setattr(materials_service, "delete_material", delete, raising=False)

    response = client.delete("/api/materials/4")

    assert response.status_code == 200
    delete.assert_called_once_with(4)


def test_delete_material_not_found_returns_404(client, monkeypatch):
    monkeypatch.setattr(
        materials_service,
        "delete_material",
        MagicMock(return_value=False),
        raising=False,
    )

    response = client.delete("/api/materials/999")

    assert response.status_code == 404


@pytest.mark.parametrize("method", ["put", "patch"])
def test_materials_have_no_update_endpoint(client, method):
    """CRD tanpa Update: PUT/PATCH tidak boleh tersedia."""
    response = getattr(client, method)("/api/materials/1", json={"title": "Baru"})

    assert response.status_code == 405