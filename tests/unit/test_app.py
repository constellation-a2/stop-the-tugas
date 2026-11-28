from app import WIB, MAX_PDF_SIZE_BYTES


def test_app_factory_uses_test_config(app):
    assert app.config["TESTING"] is True
    assert app.config["CRON_SECRET"] == "test-secret"
    assert app.config["MAX_PDF_SIZE_BYTES"] == 10485760


def test_app_uses_wib_timezone():
    assert str(WIB) == "Asia/Jakarta"
    assert MAX_PDF_SIZE_BYTES == 10 * 1024 * 1024
