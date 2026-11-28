"""Test route reminder (Team B). Service di-mock, tanpa database."""

from unittest.mock import MagicMock

from app.services import reminder_service

VALID_SUBSCRIPTION = {
    "endpoint": "https://push.example.com/abc",
    "keys": {"p256dh": "key-p256dh", "auth": "key-auth"},
}


def test_get_vapid_public_key(client):
    response = client.get("/api/reminders/vapid-public-key")

    assert response.status_code == 200
    assert response.get_json() == {"public_key": "test-public-key"}


def test_subscribe_success(client, monkeypatch):
    save = MagicMock()
    monkeypatch.setattr(reminder_service, "save_subscription", save, raising=False)

    response = client.post("/api/reminders/subscribe", json=VALID_SUBSCRIPTION)

    assert response.status_code == 201
    save.assert_called_once_with(
        "https://push.example.com/abc", "key-p256dh", "key-auth"
    )


def test_subscribe_missing_fields_returns_400(client, monkeypatch):
    save = MagicMock()
    monkeypatch.setattr(reminder_service, "save_subscription", save, raising=False)

    response = client.post(
        "/api/reminders/subscribe",
        json={"endpoint": "https://push.example.com/abc", "keys": {}},
    )

    assert response.status_code == 400
    save.assert_not_called()


def test_subscribe_without_json_returns_400(client):
    response = client.post("/api/reminders/subscribe")

    assert response.status_code == 400


def test_unsubscribe_success(client, monkeypatch):
    remove = MagicMock()
    monkeypatch.setattr(reminder_service, "remove_subscription", remove, raising=False)

    response = client.post(
        "/api/reminders/unsubscribe", json={"endpoint": "https://push.example.com/abc"}
    )

    assert response.status_code == 200
    remove.assert_called_once_with("https://push.example.com/abc")


def test_unsubscribe_missing_endpoint_returns_400(client):
    response = client.post("/api/reminders/unsubscribe", json={})

    assert response.status_code == 400


def test_cron_without_authorization_returns_401(client, monkeypatch):
    dispatch = MagicMock()
    monkeypatch.setattr(
        reminder_service, "dispatch_due_reminders", dispatch, raising=False
    )

    response = client.get("/api/reminders/cron/dispatch")

    assert response.status_code == 401
    dispatch.assert_not_called()


def test_cron_with_wrong_secret_returns_401(client):
    response = client.get(
        "/api/reminders/cron/dispatch", headers={"Authorization": "Bearer salah"}
    )

    assert response.status_code == 401


def test_cron_rejected_when_secret_not_configured(app, client):
    app.config["CRON_SECRET"] = ""

    response = client.get(
        "/api/reminders/cron/dispatch", headers={"Authorization": "Bearer "}
    )

    assert response.status_code == 401


def test_cron_with_valid_secret_dispatches(client, monkeypatch):
    dispatch = MagicMock(return_value={"sent": 2})
    monkeypatch.setattr(
        reminder_service, "dispatch_due_reminders", dispatch, raising=False
    )

    response = client.get(
        "/api/reminders/cron/dispatch",
        headers={"Authorization": "Bearer test-secret"},
    )

    assert response.status_code == 200
    assert response.get_json() == {"sent": 2}
    dispatch.assert_called_once_with()