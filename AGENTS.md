# AGENTS.md - Stop The Tugas

This file provides instructions for AI coding agents working in **Stop The Tugas**.
The user's prompt and task-specific instructions take precedence.

## 1. Project Sources of Truth

Treat planning artifacts as follows:

- [README.md](README.md) and [CONTRIBUTING.md](CONTRIBUTING.md): MVP scope, team ownership, workflow, and delivery guardrails.
- [database/ERD.dmd](database/ERD.dmd), [database/ERD/](database/ERD/), [database/Logical.png](database/Logical.png), and [database/Physical.png](database/Physical.png): database entities and relations.
- [docs/algoritms/README.md](docs/algoritms/README.md) and [docs/flowcharts/](docs/flowcharts/): reminder, calendar, upload, and delete flow specifications.
- [design/](design/): approved UI states and design tokens. The HTML and PNG files are mockups, not a reason to override canonical MVP rules.

When planning artifacts conflict, use the MVP scope in README and CONTRIBUTING, then the ERD and algorithm documentation. In particular:

- Material uploads accept PDF only and are at most `10485760` bytes (10 MB).
- A mockup that says 20 MB or another size is outdated and must not change the 10 MB requirement.
- Assignment reminders are `H-7`, `H-3`, and `H-1`.
- Class reminders are `H-1 at 19:00 WIB` and `H-30 minutes` before class start.
- A mockup that shows a 2-hour class reminder is outdated and must not change the canonical schedule.

## 2. Product and MVP Guardrails

- This MVP has no login, user account, authentication flow, `USER` table, or user foreign key.
- The creator name is input metadata or browser `localStorage` data, not an authenticated identity.
- `COURSE` is shared by agendas and materials and must provide the course dropdown used across Team B, Team C, and Team D.
- The supported agenda types are exactly `TUGAS` and `KULIAH`.
- Agenda editing is not in scope unless a specific approved task explicitly asks for it. Team C is responsible for create and delete workflows.
- Material editing and metadata editing are prohibited. Materials use CRD only: Create, Read/download, and Delete.
- Do not add RBAC, approval workflows, analytics dashboards, or post-MVP features outside the requested task.
- Production PDF storage must be persistent object storage. Do not use ephemeral local disk writes on Vercel.

## 3. Teams and Ownership

- **Team B - Reminders and Web Push:** subscription management, WIB scheduling, reminder dispatch, and duplicate prevention.
- **Team C - Calendar and Agendas:** monthly/daily views, agenda creation/deletion, course and location fields, empty-date states, and delete confirmation.
- **Team D - Materials:** folder/course grouping, PDF validation, metadata, preview/download, delete confirmation, and persistent storage.
- **UI/UX:** Montserrat, the approved palette, responsive states, empty states, notifications, validation errors, and modals.
- **Flowchart and Algorithm:** documented scheduling, calendar, and CRD flows.
- **Database Engineering:** Oracle Data Modeler artifacts and Neon PostgreSQL schema alignment.

Keep changes inside the relevant team boundary unless the task explicitly requires a cross-team contract change.

## 4. Timezone and Reminder Rules

- Use `zoneinfo.ZoneInfo("Asia/Jakarta")` for WIB date and time calculations and display.
- Store Python datetime values and PostgreSQL timestamp columns as aware values. PostgreSQL timestamp columns should use `TIMESTAMPTZ`.
- Never use naive `datetime.now()` for scheduling or display.
- Convert or format values at the application/UI boundary; do not silently assume UTC or server-local timezone.

Assignment reminders:

- Schedule pending reminders for `H-7`, `H-3`, and `H-1` relative to `agenda.deadline_dttm`.
- Skip H-intervals that are already past.
- Past-deadline agendas create no new pending reminder.

Class reminders:

- Schedule `H-1 at 19:00 WIB` the day before the class starts.
- Schedule `H-30 minutes` before `agenda.start_dttm`.
- The class name, course, lecturer, room/location, and start time must be available in reminder payloads.

Agenda synchronization:

- Recalculate pending reminders after supported agenda updates or creations.
- Delete pending reminders after agenda deletion.
- The database relation from `REMINDER` to `AGENDA` must support cascade cleanup.
- Use `claimed_at` and PostgreSQL `FOR UPDATE SKIP LOCKED` to claim cron work and prevent concurrent duplicate delivery.
- Wrap claim, write, and status changes in explicit transactions (`BEGIN` / `COMMIT` / `ROLLBACK`).

## 5. Database Contract

Use the planned Oracle Data Modeler entities and columns instead of inventing alternate names:

| Entity | Purpose | Key fields |
| --- | --- | --- |
| `COURSE` | Shared course metadata | `course_id`, `course_code`, `course_name` |
| `AGENDA` | Assignment and class items | `agenda_id`, `title`, `agenda_typ`, `description`, `start_dttm`, `end_dttm`, `deadline_dttm`, `class_loc`, `created_at`, `COURSE_course_id`, `creator` |
| `REMINDER` | Pending/scheduled dispatches | `reminder_id`, `reminder_typ`, `scheduled_at`, `created_at`, `AGENDA_agenda_id`, `claimed_at` |
| `PUSH_SUBSCRIPTION` | Browser push subscriptions | `subscription_id`, `endpoint`, `p256dh`, `auth`, `created_at` |
| `MATERIAL` | Uploaded PDF metadata | `material_id`, `title`, `file_nm`, `file_pth`, `file_sz`, `mime_type`, `uploaded_at`, `COURSE_course_id`, `creator` |

Database implementation rules:

- Use parameterized queries (`%s` or SQLAlchemy bound parameters); never interpolate user input into SQL.
- PostgreSQL mapping must preserve `TIMESTAMPTZ` for date/time and upload fields.
- Foreign key names and cascade behavior must remain consistent with the Oracle Data Modeler project.
- Keep `COURSE.course_code` unique.
- `AGENDA.COURSE_course_id` is nullable because it is more relevant to class/course-linked agendas and assignments; `MATERIAL.COURSE_course_id` is required by the ERD.
- Do not add users or user IDs to core MVP tables.
- Database DDL changes require explicit approval and corresponding migration/schema documentation.

The repository currently contains the `.dmd` project and ERD exports, but no implemented application schema under `database/physical/` or migration SQL under `migrations/`. Before adding DDL or migrations, inspect the current worktree and ask first for schema changes.

## 6. Calendar and Agenda Behavior

Team C must support:

- Monthly calendar view with dates marked for agendas.
- Daily agenda view in WIB.
- A clear empty-date state, for example: "Tidak ada tugas atau jadwal kuliah pada tanggal ini".
- Create workflows for `TUGAS` and `KULIAH`.
- Assignment fields: name/title, deadline, description, course, and creator metadata.
- Class fields: name/course, course label, start time, optional end time, lecturer/dosen, room/location (`class_loc`), description, and creator metadata.
- Delete confirmation before removing an agenda.
- Delete success feedback.
- Removal of pending reminders for deleted agendas.

Use `deadline_dttm` for assignments and `start_dttm`/`end_dttm` for classes. Do not use a class deadline field for class start times.

## 7. Web Push Behavior

- Use the Browser Push API, VAPID, and a Service Worker for opt-in delivery.
- Store push subscription keys in `PUSH_SUBSCRIPTION`; never log or commit VAPID private keys.
- The UI must expose active and inactive notification states.
- Notification opt-in is optional and must not block core calendar/material functionality.
- Handle delivery failures without stopping unrelated reminder processing.
- Use `claimed_at` and row locking for duplicate-delivery prevention; do not rely only on in-process flags.

## 8. Materials Repository Behavior

Team D must enforce CRD without update:

- Create a material under a selected `COURSE`.
- Required metadata: course, title, and creator.
- Read/open/download a material.
- Delete a material only after confirmation.
- No edit or rename endpoints or UI for materials or metadata.

PDF validation is mandatory:

- MIME type must be `application/pdf`.
- Filename must end in `.pdf`, case-insensitively.
- The first bytes must contain the `%PDF-` signature.
- Maximum size is exactly `10485760` bytes.
- Reject files over the limit, wrong MIME type, missing signature, and files with no selected content.
- Return clear Indonesian or English UI errors matching the design.
- Unit test the size boundary, MIME mismatch, signature mismatch, and successful upload.

Store the original filename, persistent path/storage URL, size, MIME type, upload timestamp, course relation, title, and creator. Never store copyrighted fixture PDFs in the repository.

## 9. Design and Frontend Rules

- Use Montserrat as the primary font, with Montserrat 400/500/600/700/800 weights as needed.
- Core palette:
  - Navy: `#1E3A8A`
  - Background: `#F8FAFF`
  - Supporting line: `#D5DDF0`
  - Supporting text: `#4B5B85`
  - Ink: `#0F1B3D`
- Preserve responsive layouts, visible keyboard focus, and `prefers-reduced-motion` behavior.
- Use consistent confirmation dialogs for agenda/material deletion.
- Show success, validation, and no-file/no-agenda feedback clearly.
- Keep navigation labels as Pengingat, Kalender, and Materi.
- Match the design only when it does not contradict a canonical MVP rule listed above.

## 10. Flask Architecture

Target modern Python 3.11+ and type hints on public functions and route handlers.

- `app/routes/`: HTTP parsing, request validation entry points, status codes, and thin orchestration.
- `app/services/`: WIB calculations, reminder scheduling, cron locking, push dispatch, and PDF validation.
- `app/models/`: PostgreSQL queries and data access.
- `app/templates/`: server-rendered HTML or PyScript integration.
- `app/static/`: CSS, JavaScript, and `sw.js`.
- `api/`: Vercel serverless entrypoint.
- `tests/unit/`: pure reminder, calendar, and validation logic.
- `tests/integration/`: Flask routes, cron locking, database workflows, and PDF CRD.
- `tests/fixtures/`: small, lightweight, non-copyrighted test files.

Use EAFP with specific exceptions, `pathlib.Path`, f-strings, and concise Google-style docstrings for non-trivial public helpers.
Do not hide errors behind broad catches or success-shaped fallbacks.

## 11. Commands and Quality Gates

After changing Python code or tests, run the relevant checks:

```bash
pip install -r requirements.txt
pytest -v
ruff check .
ruff format --check .
```

Use `uv sync` instead of pip only when the repository adopts uv and a lockfile exists.
Run type checking with `mypy app` or `pyrefly check app` only if the repository configures that tool.

Every PR that adds or modifies routes, services, database queries, or business rules must include corresponding pytest unit and/or integration coverage.

## 12. Testing Priorities

Add focused tests for:

- WIB H-7, H-3, H-1, H-1 19:00, and H-30M scheduling.
- Short-notice and past-deadline agendas.
- Agenda deletion/cancellation and reminder recalculation.
- Monthly/daily calendar filtering and empty dates.
- Cron claimed rows and concurrent duplicate prevention.
- PDF MIME, signature, exact 10 MB boundary, oversized files, and missing files.
- Material delete confirmation and successful CRD behavior.
- Agenda delete confirmation and cascade behavior.

Do not weaken or delete existing tests to make a failing build pass.

## 13. Contribution and Branching

- Branch off the latest `dev`.
- Direct pushes to `main` and `dev` are prohibited.
- Use track-prefixed names such as `team-b/`, `team-c/`, `team-d/`, `ui-ux/`, `algo/`, or `db/`.
- PRs into `dev` require passing CI and relevant team/lead approval.
- Shared schema, API, or cross-team contract changes require sign-off from every affected team.
- Use clear commits such as `feat(team-c): add agenda delete confirmation`.
- Update [README.md](README.md), [docs/](docs/), [design/](design/), or database documentation when behavior, schemas, or workflows change.

## 14. Always Do

- Keep changes scoped to the requested issue or task.
- Read existing code and planning artifacts before implementing.
- Add or update pytest coverage for routes, services, queries, and business rules.
- Use WIB-aware calculations and parameterized SQL.
- Update directly related documentation.
- Verify no secrets or copyrighted test assets are staged.
- Use `.env.example` for environment variable names only.

## 15. Ask First

- Before adding external Python packages to `requirements.txt`.
- Before changing database DDL, migrations, foreign keys, shared API contracts, or cross-team field names.
- Before changing canonical reminder intervals or material size/type limits.
- Before adopting persistent storage or introducing a login/account feature outside MVP scope.

## 16. Never Do

- Never commit `.env`, VAPID private keys, Neon credentials, cron secrets, or database connection strings.
- Never commit copyrighted PDFs or add them to test fixtures.
- Never edit or update existing materials or material metadata.
- Never add authentication or user foreign keys to the MVP.
- Never push directly to `main` or `dev`.
- Never use ephemeral local disk storage for production PDF files.
- Never interpolate user input into SQL.
- Never weaken or delete tests merely to pass CI.
