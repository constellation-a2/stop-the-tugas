-- =============================================================================
-- Stop The Tugas - Seed data (development / demo only)
-- Run AFTER schema.sql. Do not run on production.
-- All timestamps are written with an explicit WIB offset (+07:00).
-- No personal data, credentials, or push subscriptions are seeded.
-- =============================================================================
INSERT INTO course (course_code, course_name) VALUES
    ('SVRI261101', 'Matematika Diskrit'),
    ('SVRI261102', 'Pemrograman Komputer'),
    ('SVRI261103', 'Komunikasi Data'),
    ('SVRI261104', 'Teknik Telekomunikasi'),
    ('SVRI261105', 'Basis Data'),
    ('SVRI261106', 'Praktikum Pemrograman Komputer'),
    ('SVRI261107', 'Praktikum Teknik Komputer'),
    ('SVRI261108', 'Praktikum Pendukung Infrastruktur Digital'),
    ('SVRI261109', 'Literasi Kesehatan'),
    ('SVRI261110', 'Humaniora Digital');

-- Class schedule (KULIAH): start time - end time and classroom (class_loc).
INSERT INTO agenda (title, agenda_typ, start_dttm, end_dttm, class_loc, course_id, creator)
SELECT 'Kuliah ' || c.course_name,
       'KULIAH',
       v.start_dttm::timestamptz,
       v.end_dttm::timestamptz,
       v.class_loc,
       c.course_id,
       'Seed'
FROM (VALUES
    ('SVRI261101', '2026-12-07 09:15:00+07:00', '2026-12-07 10:55:00+07:00', 'CU 206'),
    ('SVRI261102', '2026-12-10 07:15:00+07:00', '2026-12-10 08:55:00+07:00', 'HU 209'),
    ('SVRI261103', '2026-12-10 12:15:00+07:00', '2026-12-10 13:55:00+07:00', 'CU 204'),
    ('SVRI261104', '2026-12-09 12:15:00+07:00', '2026-12-09 13:55:00+07:00', 'HU 208'),
    ('SVRI261105', '2026-12-10 09:15:00+07:00', '2026-12-10 10:55:00+07:00', 'HU 208'),
    ('SVRI261106', '2026-12-09 07:15:00+07:00', '2026-12-09 10:55:00+07:00', 'HS 103'),
    ('SVRI261107', '2026-12-07 12:15:00+07:00', '2026-12-07 15:55:00+07:00', 'G 301'),
    ('SVRI261108', '2026-12-08 07:15:00+07:00', '2026-12-08 10:55:00+07:00', 'G 103'),
    ('SVRI261109', NULL, NULL, NULL),
    ('SVRI261110', NULL, NULL, NULL)
) AS v (course_code, start_dttm, end_dttm, class_loc)
JOIN course c ON c.course_code = v.course_code;

-- Reminders for every class that has a start time (H-30M before class start)
INSERT INTO reminder (reminder_typ, scheduled_at, agenda_id)
SELECT 'H-30M', a.start_dttm - INTERVAL '30 minutes', a.agenda_id
FROM agenda a
WHERE a.agenda_typ = 'KULIAH'
  AND a.start_dttm IS NOT NULL;
