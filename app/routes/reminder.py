"""Endpoint push subscription dan cron reminder (Team B)."""

import hmac
from typing import Any

from flask import Blueprint, current_app, jsonify, request

from app.services import reminder_service

reminder_bp = Blueprint("reminder", __name__, url_prefix="/api/reminders")


def _is_cron_authorized() -> bool:
    """Memeriksa header Authorization: Bearer <CRON_SECRET>."""
    secret = current_app.config.get("CRON_SECRET", "")
    if not secret:
        return False
    header = request.headers.get("Authorization", "")
    expected = f"Bearer {secret}"
    return hmac.compare_digest(header, expected)


@reminder_bp.get("/vapid-public-key")
def get_vapid_public_key():
    """Mengembalikan VAPID public key untuk pendaftaran di browser."""
    return jsonify({"public_key": current_app.config["VAPID_PUBLIC_KEY"]})


@reminder_bp.post("/subscribe")
def subscribe():
    """Menyimpan push subscription dari browser."""
    data: dict[str, Any] = request.get_json(silent=True) or {}
    keys = data.get("keys") or {}
    endpoint = data.get("endpoint")
    p256dh = keys.get("p256dh")
    auth = keys.get("auth")

    if not endpoint or not p256dh or not auth:
        return jsonify({"error": "endpoint, keys.p256dh, dan keys.auth wajib diisi"}), 400

    reminder_service.save_subscription(endpoint, p256dh, auth)
    return jsonify({"message": "Notifikasi berhasil diaktifkan"}), 201


@reminder_bp.post("/unsubscribe")
def unsubscribe():
    """Menghapus push subscription berdasarkan endpoint."""
    data: dict[str, Any] = request.get_json(silent=True) or {}
    endpoint = data.get("endpoint")

    if not endpoint:
        return jsonify({"error": "endpoint wajib diisi"}), 400

    reminder_service.remove_subscription(endpoint)
    return jsonify({"message": "Notifikasi dinonaktifkan"}), 200


@reminder_bp.get("/cron/dispatch")
def cron_dispatch():
    """Dipanggil Vercel Cron untuk mengirim reminder yang sudah jatuh tempo."""
    if not _is_cron_authorized():
        return jsonify({"error": "Unauthorized"}), 401

    result = reminder_service.dispatch_due_reminders()
    return jsonify(result), 200