"""Queries for the ``push_subscription`` table (Team B, Web Push).

Subscriptions are not linked to any user (the MVP has no login system).
"""

from __future__ import annotations

from app.models.db import Connection, Row, execute, fetch_all, fetch_one, fetch_returning

_COLUMNS = "subscription_id, endpoint, p256dh, auth, created_at"


def save_subscription(
    conn: Connection,
    *,
    endpoint: str,
    p256dh: str,
    auth: str,
) -> Row:
    """Store a browser subscription, refreshing its keys if the endpoint exists.

    Returns:
        The stored row.
    """
    existing = fetch_one(
        conn,
        "SELECT subscription_id FROM push_subscription WHERE endpoint = %s",
        (endpoint,),
    )
    if existing is not None:
        return fetch_returning(
            conn,
            f"""
            UPDATE push_subscription SET p256dh = %s, auth = %s
            WHERE subscription_id = %s
            RETURNING {_COLUMNS}
            """,
            (p256dh, auth, existing["subscription_id"]),
        )
    return fetch_returning(
        conn,
        f"""
        INSERT INTO push_subscription (endpoint, p256dh, auth)
        VALUES (%s, %s, %s)
        RETURNING {_COLUMNS}
        """,
        (endpoint, p256dh, auth),
    )


def list_subscriptions(conn: Connection) -> list[Row]:
    """Return all subscriptions, oldest first."""
    return fetch_all(
        conn,
        f"SELECT {_COLUMNS} FROM push_subscription ORDER BY subscription_id",
    )


def delete_subscription_by_endpoint(conn: Connection, endpoint: str) -> bool:
    """Delete a subscription (e.g. after the push service answers 404/410).

    Returns:
        ``True`` if at least one row was deleted.
    """
    return (
        execute(conn, "DELETE FROM push_subscription WHERE endpoint = %s", (endpoint,)) > 0
    )
