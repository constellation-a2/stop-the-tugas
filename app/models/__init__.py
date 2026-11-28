"""PostgreSQL (Neon) data access layer for Stop The Tugas.

One module per table, matching ``database/physical/schema.sql``:

* :mod:`app.models.course`
* :mod:`app.models.agenda`
* :mod:`app.models.reminder`
* :mod:`app.models.material`
* :mod:`app.models.push_subscription`

Business rules (WIB reminder countdowns, PDF validation, cron orchestration)
belong in ``app/services/``; routes stay thin. There is intentionally no user
model: the MVP has no login system.
"""
