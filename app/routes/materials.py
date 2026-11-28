"""Endpoint repositori materi PDF: Create, Read, Delete tanpa Update (Team D)."""

import io

from flask import Blueprint, jsonify, request, send_file

from app.services import materials_service

materials_bp = Blueprint("materials", __name__, url_prefix="/api/materials")


@materials_bp.app_errorhandler(413)
def file_too_large(_error):
    """Mengubah error ukuran request terlalu besar menjadi pesan JSON yang jelas."""
    return jsonify({"error": "Ukuran file melebihi batas 10 MB"}), 413


@materials_bp.get("")
def list_materials():
    """Mengembalikan daftar materi, bisa difilter dengan ?course=<label>."""
    course = request.args.get("course") or None
    materials = materials_service.list_materials(course)
    return jsonify({"materials": materials}), 200


@materials_bp.post("")
def create_material():
    """Mengunggah materi PDF baru beserta metadata."""
    file = request.files.get("file")
    title = (request.form.get("title") or "").strip()
    course = (request.form.get("course") or "").strip()
    creator = (request.form.get("creator") or "").strip()

    if file is None or not file.filename:
        return jsonify({"error": "File PDF wajib diunggah"}), 400
    if not title or not course or not creator:
        return jsonify({"error": "title, course, dan creator wajib diisi"}), 400

    try:
        material = materials_service.create_material(file, title, course, creator)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(material), 201


@materials_bp.get("/<int:material_id>/file")
def get_material_file(material_id: int):
    """Menampilkan (preview) atau mengunduh PDF dengan ?download=1."""
    material = materials_service.get_material_file(material_id)
    if material is None:
        return jsonify({"error": "Materi tidak ditemukan"}), 404

    return send_file(
        io.BytesIO(material["content"]),
        mimetype="application/pdf",
        as_attachment=request.args.get("download") == "1",
        download_name=material["filename"],
    )


@materials_bp.delete("/<int:material_id>")
def delete_material(material_id: int):
    """Menghapus materi beserta file PDF-nya."""
    deleted = materials_service.delete_material(material_id)
    if not deleted:
        return jsonify({"error": "Materi tidak ditemukan"}), 404

    return jsonify({"message": "Materi berhasil dihapus"}), 200