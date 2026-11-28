import pytest

from app import create_app


@pytest.fixture()
def app():
    return create_app({"TESTING": True, "CRON_SECRET": "test-secret"})


@pytest.fixture()
def client(app):
    return app.test_client()