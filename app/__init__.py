"""Inisialisasi dan konfigurasi aplikasi Flask Stop The Tugas."""

import os
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from flask import Flask

WIB = ZoneInfo("Asia/Jakarta")
MAX_PDF_SIZE_BYTES = 10485760  # 10 MB
BASE_DIR = Path(__file__).resolve().parent


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """Membuat dan mengonfigurasi instance Flask (application factory).

    Args:
        test_config: Konfigurasi opsional yang menimpa default (untuk pytest).

    Returns:
        Instance Flask dengan semua blueprint terdaftar.
    """
    app = Flask(__name__)

    app.config.from_mapping(
        DATABASE_URL=os.environ.get("DATABASE_URL", ""),
        VAPID_PUBLIC_KEY=os.environ.get("VAPID_PUBLIC_KEY", ""),
        VAPID_PRIVATE_KEY=os.environ.get("VAPID_PRIVATE_KEY", ""),
        VAPID_CLAIM_EMAIL=os.environ.get("VAPID_CLAIM_EMAIL", ""),
        CRON_SECRET=os.environ.get("CRON_SECRET", ""),
        TIMEZONE="Asia/Jakarta",
        MAX_PDF_SIZE_BYTES=MAX_PDF_SIZE_BYTES,
        # Beri ruang ekstra untuk overhead multipart agar validasi 10 MB
        # di service bisa mengembalikan pesan error yang jelas.
        MAX_CONTENT_LENGTH=MAX_PDF_SIZE_BYTES + 1024 * 1024,
        # Hanya untuk dev lokal; di Vercel gunakan penyimpanan persisten.
        UPLOAD_FOLDER=str(BASE_DIR / "static" / "uploads"),
    )

    if test_config is not None:
        app.config.update(test_config)

    # from app.routes.calendar import calendar_bp
    # from app.routes.materials import materials_bp
    # from app.routes.reminder import reminder_bp

    # app.register_blueprint(reminder_bp)
    # app.register_blueprint(calendar_bp)
    # app.register_blueprint(materials_bp)

    return app