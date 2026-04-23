-- =============================================================================
-- Syllabify — PostgreSQL / Supabase schema
-- Translated from MySQL run-all-migrations.sql + migration 015
--
-- Run this once against a fresh Supabase project:
--   1. Open Supabase Dashboard → SQL Editor
--   2. Paste this entire file and click Run
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Shared trigger function for updated_at columns
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------------
-- Users
-- (includes all migrations: 003 email/is_admin/is_disabled, 011 google_id/auth_provider,
--  012 avatar, 013 ical_feed_*, 014 avatar_url/banner_url/description)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Users (
    id                          SERIAL PRIMARY KEY,
    username                    VARCHAR(255) NOT NULL UNIQUE,
    password_hash               VARCHAR(255),
    security_setup_done         BOOLEAN DEFAULT FALSE,
    email                       VARCHAR(255) NULL UNIQUE,
    is_admin                    BOOLEAN DEFAULT FALSE,
    is_disabled                 BOOLEAN DEFAULT FALSE,
    google_id                   VARCHAR(255) NULL UNIQUE,
    auth_provider               VARCHAR(50) DEFAULT 'local',
    avatar                      VARCHAR(20) NULL,
    ical_feed_token             VARCHAR(191) NULL,
    ical_feed_enabled           BOOLEAN NOT NULL DEFAULT TRUE,
    ical_feed_token_updated_at  TIMESTAMP NULL,
    avatar_url                  VARCHAR(500) NULL,
    banner_url                  VARCHAR(500) NULL,
    description                 TEXT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_ical_feed_token
    ON Users (ical_feed_token)
    WHERE ical_feed_token IS NOT NULL;

-- ---------------------------------------------------------------------------
-- UserSecurityAnswers
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS UserSecurityAnswers (
    id            SERIAL PRIMARY KEY,
    user_id       INT NOT NULL REFERENCES Users(id) ON DELETE CASCADE,
    question_text VARCHAR(500) NOT NULL,
    answer_hash   VARCHAR(255) NOT NULL
);

-- ---------------------------------------------------------------------------
-- Terms
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Terms (
    id         SERIAL PRIMARY KEY,
    user_id    INT NOT NULL REFERENCES Users(id) ON DELETE CASCADE,
    term_name  VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date   DATE NOT NULL,
    is_active  BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_terms_user_active ON Terms (user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_terms_user_dates  ON Terms (user_id, start_date, end_date);

-- ---------------------------------------------------------------------------
-- Courses  (includes migration 004: study_hours_per_week, color)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Courses (
    id                   SERIAL PRIMARY KEY,
    course_name          VARCHAR(255) NOT NULL,
    term_id              INT NOT NULL REFERENCES Terms(id) ON DELETE CASCADE,
    study_hours_per_week INT NULL,
    color                VARCHAR(7) NULL
);

-- ---------------------------------------------------------------------------
-- Assignments  (includes migration 015: is_completed, completed_at)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Assignments (
    id              SERIAL PRIMARY KEY,
    assignment_name VARCHAR(255) NOT NULL,
    work_load       INT NOT NULL,
    notes           VARCHAR(2048),
    start_date      TIMESTAMP NOT NULL,
    due_date        TIMESTAMP NOT NULL,
    assignment_type VARCHAR(50) NULL,
    course_id       INT NOT NULL REFERENCES Courses(id) ON DELETE CASCADE,
    is_completed    BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at    TIMESTAMP NULL
);

-- ---------------------------------------------------------------------------
-- Meetings
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Meetings (
    id             SERIAL PRIMARY KEY,
    course_id      INT NOT NULL REFERENCES Courses(id) ON DELETE CASCADE,
    day_of_week    VARCHAR(2) NULL,
    start_time_str VARCHAR(5) NULL,
    end_time_str   VARCHAR(5) NULL,
    location       VARCHAR(255) NULL,
    meeting_type   VARCHAR(50) NULL,
    start_time     TIMESTAMP NULL,
    end_time       TIMESTAMP NULL
);

-- ---------------------------------------------------------------------------
-- StudyTimes  (includes migration 012: is_locked, assignment_id, course_id)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS StudyTimes (
    id            SERIAL PRIMARY KEY,
    notes         VARCHAR(2048) NULL,
    start_time    TIMESTAMP NOT NULL,
    end_time      TIMESTAMP NOT NULL,
    term_id       INT NOT NULL REFERENCES Terms(id) ON DELETE CASCADE,
    is_locked     BOOLEAN DEFAULT FALSE,
    assignment_id INT NULL,
    course_id     INT NULL
);

-- ---------------------------------------------------------------------------
-- UserPreferences  (includes migration 005: timezone)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS UserPreferences (
    id               SERIAL PRIMARY KEY,
    user_id          INT NOT NULL UNIQUE REFERENCES Users(id) ON DELETE CASCADE,
    work_start       VARCHAR(5) NOT NULL DEFAULT '09:00',
    work_end         VARCHAR(5) NOT NULL DEFAULT '17:00',
    preferred_days   VARCHAR(50) NOT NULL DEFAULT 'MO,TU,WE,TH,FR',
    max_hours_per_day INT NOT NULL DEFAULT 8,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    timezone         VARCHAR(64) NULL
);

CREATE TRIGGER trg_user_preferences_updated_at
    BEFORE UPDATE ON UserPreferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------
-- AdminSettings
-- key is not a reserved word in PostgreSQL; no quoting needed.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS AdminSettings (
    key   VARCHAR(50) PRIMARY KEY,
    value TEXT
);

INSERT INTO AdminSettings (key, value) VALUES
    ('maintenance_enabled',  '0'),
    ('maintenance_message',  'Syllabify is undergoing maintenance. Please try again later.'),
    ('registration_enabled', '1'),
    ('announcement_banner',  '')
ON CONFLICT (key) DO NOTHING;

-- ---------------------------------------------------------------------------
-- AdminAuditLog
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS AdminAuditLog (
    id               SERIAL PRIMARY KEY,
    admin_user_id    INT NOT NULL,
    admin_username   VARCHAR(50) NOT NULL,
    action           VARCHAR(50) NOT NULL,
    target_user_id   INT NULL,
    target_username  VARCHAR(50) NULL,
    details          TEXT NULL,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_created_at      ON AdminAuditLog (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_admin_user_id   ON AdminAuditLog (admin_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_target_user_id  ON AdminAuditLog (target_user_id);

-- ---------------------------------------------------------------------------
-- UserAdminNotes
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS UserAdminNotes (
    user_id              INT PRIMARY KEY REFERENCES Users(id) ON DELETE CASCADE,
    note_text            TEXT NULL,
    updated_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by_admin_id  INT NULL
);

CREATE TRIGGER trg_user_admin_notes_updated_at
    BEFORE UPDATE ON UserAdminNotes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------
-- UserOAuthTokens  (migration 011)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS UserOAuthTokens (
    id            SERIAL PRIMARY KEY,
    user_id       INT NOT NULL REFERENCES Users(id) ON DELETE CASCADE,
    provider      VARCHAR(50) NOT NULL DEFAULT 'google',
    access_token  TEXT,
    refresh_token TEXT,
    expires_at    TIMESTAMP NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, provider)
);

CREATE TRIGGER trg_user_oauth_tokens_updated_at
    BEFORE UPDATE ON UserOAuthTokens
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------
-- ExternalEvents  (migration 011)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ExternalEvents (
    id                  SERIAL PRIMARY KEY,
    user_id             INT NOT NULL REFERENCES Users(id) ON DELETE CASCADE,
    google_event_id     VARCHAR(255) NOT NULL,
    google_calendar_id  VARCHAR(255) NOT NULL,
    title               VARCHAR(500),
    start_time          TIMESTAMP NOT NULL,
    end_time            TIMESTAMP NOT NULL,
    source              VARCHAR(50) DEFAULT 'google',
    term_id             INT NULL REFERENCES Terms(id) ON DELETE SET NULL,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, google_calendar_id, google_event_id)
);

-- ---------------------------------------------------------------------------
-- UserCalendarConnections  (migration 011)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS UserCalendarConnections (
    id                       SERIAL PRIMARY KEY,
    user_id                  INT NOT NULL REFERENCES Users(id) ON DELETE CASCADE,
    google_calendar_id       VARCHAR(255) NOT NULL,
    calendar_name            VARCHAR(255),
    import_date_range_start  DATE NULL,
    import_date_range_end    DATE NULL,
    last_synced_at           TIMESTAMP NULL,
    created_at               TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, google_calendar_id)
);

-- ---------------------------------------------------------------------------
-- CalendarSources  (migration 012)
-- TINYINT(1) DEFAULT 0/1 → BOOLEAN DEFAULT FALSE/TRUE
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS CalendarSources (
    id                  SERIAL PRIMARY KEY,
    user_id             INT NOT NULL REFERENCES Users(id) ON DELETE CASCADE,
    source_type         VARCHAR(20) NOT NULL DEFAULT 'google',
    source_label        VARCHAR(100) NOT NULL,
    feed_url            TEXT,
    feed_url_hash       CHAR(64),
    feed_category       VARCHAR(20) DEFAULT 'other',
    google_calendar_id  VARCHAR(255),
    color               VARCHAR(7) DEFAULT '#3B82F6',
    is_writable         BOOLEAN DEFAULT FALSE,
    source_mode         VARCHAR(20) DEFAULT 'import_only',
    is_active           BOOLEAN DEFAULT TRUE,
    last_synced_at      TIMESTAMP NULL,
    sync_error          TEXT,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, feed_url_hash),
    UNIQUE (user_id, source_type, google_calendar_id)
);

CREATE TRIGGER trg_calendar_sources_updated_at
    BEFORE UPDATE ON CalendarSources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------
-- CalendarEvents  (migration 012)
-- JSON → JSONB  |  TINYINT(1) → BOOLEAN
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS CalendarEvents (
    id                    SERIAL PRIMARY KEY,
    user_id               INT NOT NULL REFERENCES Users(id) ON DELETE CASCADE,
    source_id             INT NOT NULL REFERENCES CalendarSources(id) ON DELETE CASCADE,
    external_uid          VARCHAR(500) NOT NULL,
    recurrence_id         VARCHAR(100),
    instance_key          VARCHAR(255) NOT NULL DEFAULT 'base',
    title                 VARCHAR(500) NOT NULL,
    description           TEXT,
    location              VARCHAR(500),
    start_time            TIMESTAMP,
    end_time              TIMESTAMP,
    original_timezone     VARCHAR(100),
    start_date            DATE,
    end_date              DATE,
    event_kind            VARCHAR(20) NOT NULL DEFAULT 'timed',
    event_category        VARCHAR(30) NOT NULL DEFAULT 'other',
    sync_status           VARCHAR(20) NOT NULL DEFAULT 'active',
    recurrence_rule       TEXT,
    is_recurring_instance BOOLEAN DEFAULT FALSE,
    original_data         JSONB,
    is_locally_modified   BOOLEAN DEFAULT FALSE,
    local_title           VARCHAR(500),
    local_start_time      TIMESTAMP,
    local_end_time        TIMESTAMP,
    local_notes           TEXT,
    local_modified_at     TIMESTAMP,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (source_id, external_uid, instance_key)
);

CREATE INDEX IF NOT EXISTS idx_cal_events_user_kind  ON CalendarEvents (user_id, event_kind);
CREATE INDEX IF NOT EXISTS idx_cal_events_user_dates ON CalendarEvents (user_id, start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_cal_events_sync       ON CalendarEvents (sync_status);

CREATE TRIGGER trg_calendar_events_updated_at
    BEFORE UPDATE ON CalendarEvents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =============================================================================
-- Done. Your Supabase database is ready.
-- =============================================================================
