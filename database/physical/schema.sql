-- =============================================================================
-- Stop The Tugas - Physical schema (PostgreSQL / Neon)
-- Source: ERD "stop_the_tugas" (Oracle Data Modeler), adapted for PostgreSQL.
--
-- Conventions (see CONTRIBUTING.md):
--   * No login system: there is intentionally NO users table and no user FK.
--   * All timestamps are TIMESTAMPTZ. Schedules/reminders are interpreted and
--     displayed in WIB (Asia/Jakarta); PostgreSQL stores them as absolute UTC.
--   * Reminders are removed automatically with their agenda (ON DELETE CASCADE).
--   * Cron dispatch uses reminder.claimed_at + FOR UPDATE SKIP LOCKED.
--   * Materials are CRD only (no update flow); only PDF <= 10 MB is accepted.
--
-- Oracle -> PostgreSQL type mapping:
--   INTEGER (PK)                  -> INTEGER GENERATED ALWAYS AS IDENTITY
--   VARCHAR2(n)                   -> VARCHAR(n)
--   CLOB                          -> TEXT
--   TIMESTAMP WITH TIME ZONE      -> TIMESTAMPTZ
-- =============================================================================

-- -----------------------------------------------------------------------------
-- COURSE: shared course dropdown for Team B, C, and D
-- -----------------------------------------------------------------------------
CREATE TABLE course (
    course_id   INTEGER      GENERATED ALWAYS AS IDENTITY,
    course_code VARCHAR(20)  NOT NULL,
    course_name VARCHAR(100) NOT NULL,
    CONSTRAINT course_pk PRIMARY KEY (course_id),
    CONSTRAINT course_course_code_un UNIQUE (course_code)
);

-- -----------------------------------------------------------------------------
-- PUSH_SUBSCRIPTION: Web Push subscriptions (no user link; no login in MVP)
-- -----------------------------------------------------------------------------
CREATE TABLE push_subscription (
    subscription_id INTEGER     GENERATED ALWAYS AS IDENTITY,
    endpoint        TEXT        NOT NULL,
    p256dh          TEXT        NOT NULL,
    auth            TEXT        NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT push_subscription_pk PRIMARY KEY (subscription_id)
);

-- -----------------------------------------------------------------------------
-- AGENDA: assignments (TUGAS) and class schedules (KULIAH)
-- course_id is optional (dashed relationship in the ERD).
-- -----------------------------------------------------------------------------
CREATE TABLE agenda (
    agenda_id     INTEGER      GENERATED ALWAYS AS IDENTITY,
    title         VARCHAR(200) NOT NULL,
    agenda_typ    VARCHAR(20)  NOT NULL,
    description   TEXT,
    start_dttm    TIMESTAMPTZ,
    end_dttm      TIMESTAMPTZ,
    deadline_dttm TIMESTAMPTZ,
    class_loc     VARCHAR(100),
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    course_id     INTEGER,
    creator       VARCHAR(100) NOT NULL,
    CONSTRAINT agenda_pk PRIMARY KEY (agenda_id),
    CONSTRAINT agenda_course_fk FOREIGN KEY (course_id)
        REFERENCES course (course_id),
    CONSTRAINT agenda_agenda_typ_ck CHECK (agenda_typ IN ('TUGAS', 'KULIAH')),
    CONSTRAINT agenda_end_after_start_ck
        CHECK (start_dttm IS NULL OR end_dttm IS NULL OR end_dttm >= start_dttm)
);

-- -----------------------------------------------------------------------------
-- MATERIAL: study materials and notes (CRD, no update). Course is mandatory.
-- -----------------------------------------------------------------------------
CREATE TABLE material (
    material_id INTEGER      GENERATED ALWAYS AS IDENTITY,
    title       VARCHAR(200) NOT NULL,
    file_nm     VARCHAR(255) NOT NULL,
    file_pth    TEXT         NOT NULL,
    file_sz     INTEGER      NOT NULL,
    mime_type   VARCHAR(100) NOT NULL,
    uploaded_at TIMESTAMPTZ  NOT NULL DEFAULT now(),
    course_id   INTEGER      NOT NULL,
    creator     VARCHAR(100) NOT NULL,
    CONSTRAINT material_pk PRIMARY KEY (material_id),
    CONSTRAINT material_course_fk FOREIGN KEY (course_id)
        REFERENCES course (course_id),
    CONSTRAINT material_file_sz_ck CHECK (file_sz > 0 AND file_sz <= 10485760), -- 10 MB
    CONSTRAINT material_mime_type_ck CHECK (mime_type = 'application/pdf')
);

-- -----------------------------------------------------------------------------
-- REMINDER: scheduled notifications for an agenda.
-- claimed_at is set by the cron job that claims the row (anti double-delivery).
-- -----------------------------------------------------------------------------
CREATE TABLE reminder (
    reminder_id  INTEGER     GENERATED ALWAYS AS IDENTITY,
    reminder_typ VARCHAR(20) NOT NULL,
    scheduled_at TIMESTAMPTZ NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    agenda_id    INTEGER     NOT NULL,
    claimed_at   TIMESTAMPTZ,
    CONSTRAINT reminders_pk PRIMARY KEY (reminder_id),
    CONSTRAINT reminder_agenda_fk FOREIGN KEY (agenda_id)
        REFERENCES agenda (agenda_id) ON DELETE CASCADE
);

-- -----------------------------------------------------------------------------
-- Indexes
-- -----------------------------------------------------------------------------
-- Foreign key lookups (also speeds up ON DELETE CASCADE on reminder)
CREATE INDEX agenda_course_id_idx    ON agenda   (course_id);
CREATE INDEX material_course_id_idx  ON material (course_id);
CREATE INDEX reminder_agenda_id_idx  ON reminder (agenda_id);

-- Calendar queries (monthly markers / daily agenda)
CREATE INDEX agenda_start_dttm_idx    ON agenda (start_dttm);
CREATE INDEX agenda_deadline_dttm_idx ON agenda (deadline_dttm);

-- Cron dispatch: due reminders that nobody has claimed yet, e.g.
--   SELECT ... FROM reminder
--   WHERE claimed_at IS NULL AND scheduled_at <= now()
--   ORDER BY scheduled_at
--   FOR UPDATE SKIP LOCKED;
CREATE INDEX reminder_due_unclaimed_idx
    ON reminder (scheduled_at)
    WHERE claimed_at IS NULL;
