"""Endpoint kalender dan agenda TUGAS/KULIAH (Team C)."""

from datetime import date
from typing import Any

from flask import Blueprint, jsonify, request

from app.services import calendar_service

calendar_bp = Blueprint("calendar", __name__, url_prefix="/api/calendar")

AGENDA_TYPES = {"TUGAS", "KULIAH"}
EMPTY_DATE_MESSAGE = "Tidak ada tugas atau jadwal kuliah pada tanggal ini"


@calendar_bp.get("/month")
def get_month():
    """Mengembalikan tanggal-tanggal yang memiliki agenda pada bulan tertentu."""
    try:
        year = int(request.args.get("year", ""))
        month = int(request.args.get("month", ""))
    except ValueError:
        return jsonify({"error": "year dan month harus berupa angka"}), 400

    if not 1 <= month <= 12:
        return jsonify({"error": "month harus antara 1 dan 12"}), 400

    marked_dates = calendar_service.get_marked_dates(year, month)
    return jsonify({"year": year, "month": month, "dates": marked_dates}), 200


@calendar_bp.get("/day")
def get_day():
    """Mengembalikan daftar agenda pada satu tanggal (WIB)."""
    try:
        target = date.fromisoformat(request.args.get("date", ""))
    except ValueError:
        return jsonify({"error": "date harus berformat YYYY-MM-DD"}), 400

    agendas = calendar_service.get_agendas_by_date(target)
    if not agendas:
        return jsonify({"date": target.isoformat(), "agendas": [], "message": EMPTY_DATE_MESSAGE}), 200

    return jsonify({"date": target.isoformat(), "agendas": agendas}), 200


@calendar_bp.post("/agendas")
def create_agenda():
    """Membuat agenda baru (TUGAS atau KULIAH)."""
    data: dict[str, Any] = request.get_json(silent=True) or {}

    if not data.get("title") or not data.get("start_at"):
        return jsonify({"error": "title dan start_at wajib diisi"}), 400
    if data.get("type") not in AGENDA_TYPES:
        return jsonify({"error": "type harus TUGAS atau KULIAH"}), 400

    try:
        agenda = calendar_service.create_agenda(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(agenda), 201


@calendar_bp.delete("/agendas/<int:agenda_id>")
def delete_agenda(agenda_id: int):
    """Menghapus agenda beserta reminder yang masih pending."""
    deleted = calendar_service.delete_agenda(agenda_id)
    if not deleted:
        return jsonify({"error": "Agenda tidak ditemukan"}), 404

    return jsonify({"message": "Agenda berhasil dihapus"}), 200