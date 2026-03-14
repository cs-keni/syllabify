-- =============================================================================
-- Syllabify: Run All Migrations (Fresh Railway/MySQL Database)
-- =============================================================================
-- Use this for a NEW database. In MySQL Workbench:
--   1. Connect to your Railway MySQL (or any MySQL)
--   2. Create/select your database (e.g. "railway")
--   3. File → Open SQL Script → select this file
--   4. Execute (lightning bolt icon or Ctrl+Shift+Enter)
--
-- If you get "Duplicate column" or "Duplicate key" on a later run, that's OK —
-- it means that part was already applied. You can ignore those errors.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Base schema (from railway-schema.sql)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS Users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255),
    security_setup_done BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS UserSecurityAnswers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    question_text VARCHAR(500) NOT NULL,
    answer_hash VARCHAR(255) NOT NULL,
    FOREIGN KEY(user_id) REFERENCES Users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Terms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    term_name VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES Users(id) ON DELETE CASCADE,
    INDEX idx_user_active (user_id, is_active),
    INDEX idx_user_dates (user_id, start_date, end_date)
);

CREATE TABLE IF NOT EXISTS Courses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    course_name VARCHAR(255) NOT NULL,
    term_id INT NOT NULL,
    study_hours_per_week INT NULL,
    FOREIGN KEY (term_id) REFERENCES Terms(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    assignment_name VARCHAR(255) NOT NULL,
    work_load INT NOT NULL,
    notes VARCHAR(2048),
    start_date DATETIME NOT NULL,
    due_date DATETIME NOT NULL,
    assignment_type VARCHAR(50) NULL,
    course_id INT NOT NULL,
    FOREIGN KEY (course_id) REFERENCES Courses(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Meetings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    course_id INT NOT NULL,
    day_of_week VARCHAR(2) NULL,
    start_time_str VARCHAR(5) NULL,
    end_time_str VARCHAR(5) NULL,
    location VARCHAR(255) NULL,
    meeting_type VARCHAR(50) NULL,
    start_time DATETIME NULL,
    end_time DATETIME NULL,
    FOREIGN KEY (course_id) REFERENCES Courses(id) ON DELETE CASCADE
);

-- StudyTimes (required for schedule feature; not in railway-schema.sql)
CREATE TABLE IF NOT EXISTS StudyTimes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    notes VARCHAR(2048) NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    term_id INT NOT NULL,
    FOREIGN KEY (term_id) REFERENCES Terms(id) ON DELETE CASCADE
);

-- -----------------------------------------------------------------------------
-- 2. Migration 003: User registration (email, is_admin, is_disabled) — idempotent
-- -----------------------------------------------------------------------------
SET @c := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'Users' AND COLUMN_NAME = 'email');
SET @s := IF(@c = 0, 'ALTER TABLE Users ADD COLUMN email VARCHAR(255) NULL UNIQUE', 'SELECT 1');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

SET @c := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'Users' AND COLUMN_NAME = 'is_admin');
SET @s := IF(@c = 0, 'ALTER TABLE Users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE', 'SELECT 1');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

SET @c := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'Users' AND COLUMN_NAME = 'is_disabled');
SET @s := IF(@c = 0, 'ALTER TABLE Users ADD COLUMN is_disabled BOOLEAN DEFAULT FALSE', 'SELECT 1');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

-- -----------------------------------------------------------------------------
-- 3. Migration 004/005: UserPreferences + timezone + Courses.color — idempotent
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS UserPreferences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    work_start VARCHAR(5) NOT NULL DEFAULT '09:00',
    work_end VARCHAR(5) NOT NULL DEFAULT '17:00',
    preferred_days VARCHAR(50) NOT NULL DEFAULT 'MO,TU,WE,TH,FR',
    max_hours_per_day INT NOT NULL DEFAULT 8,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
);

SET @c := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'UserPreferences' AND COLUMN_NAME = 'timezone');
SET @s := IF(@c = 0, 'ALTER TABLE UserPreferences ADD COLUMN timezone VARCHAR(64) NULL', 'SELECT 1');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

SET @c := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'Courses' AND COLUMN_NAME = 'color');
SET @s := IF(@c = 0, 'ALTER TABLE Courses ADD COLUMN color VARCHAR(7) NULL', 'SELECT 1');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

-- -----------------------------------------------------------------------------
-- 4. Migration 007: AdminSettings
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS AdminSettings (
    `key` VARCHAR(50) PRIMARY KEY,
    value TEXT
);
INSERT IGNORE INTO AdminSettings (`key`, value) VALUES
('maintenance_enabled', '0'),
('maintenance_message', 'Syllabify is undergoing maintenance. Please try again later.');

-- -----------------------------------------------------------------------------
-- 5. Migration 008: AdminAuditLog
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS AdminAuditLog (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_user_id INT NOT NULL,
    admin_username VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    target_user_id INT NULL,
    target_username VARCHAR(50) NULL,
    details TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_created_at (created_at DESC),
    INDEX idx_admin_user_id (admin_user_id),
    INDEX idx_target_user_id (target_user_id)
);

-- -----------------------------------------------------------------------------
-- 6. Migration 009: Registration + announcement
-- -----------------------------------------------------------------------------
INSERT IGNORE INTO AdminSettings (`key`, value) VALUES
('registration_enabled', '1'),
('announcement_banner', '');

-- -----------------------------------------------------------------------------
-- 7. Migration 010: UserAdminNotes
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS UserAdminNotes (
    user_id INT PRIMARY KEY,
    note_text TEXT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    updated_by_admin_id INT NULL,
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
);

-- -----------------------------------------------------------------------------
-- 8. Migration 011: Google OAuth + Calendar — idempotent
-- -----------------------------------------------------------------------------
SET @c := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'Users' AND COLUMN_NAME = 'google_id');
SET @s := IF(@c = 0, 'ALTER TABLE Users ADD COLUMN google_id VARCHAR(255) NULL UNIQUE', 'SELECT 1');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

SET @c := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'Users' AND COLUMN_NAME = 'auth_provider');
SET @s := IF(@c = 0, 'ALTER TABLE Users ADD COLUMN auth_provider VARCHAR(50) DEFAULT ''local''', 'SELECT 1');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

CREATE TABLE IF NOT EXISTS UserOAuthTokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    provider VARCHAR(50) NOT NULL DEFAULT 'google',
    access_token TEXT,
    refresh_token TEXT,
    expires_at DATETIME NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_provider (user_id, provider),
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ExternalEvents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    google_event_id VARCHAR(255) NOT NULL,
    google_calendar_id VARCHAR(255) NOT NULL,
    title VARCHAR(500),
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    source VARCHAR(50) DEFAULT 'google',
    term_id INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_google_event (user_id, google_calendar_id, google_event_id),
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,
    FOREIGN KEY (term_id) REFERENCES Terms(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS UserCalendarConnections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    google_calendar_id VARCHAR(255) NOT NULL,
    calendar_name VARCHAR(255),
    import_date_range_start DATE NULL,
    import_date_range_end DATE NULL,
    last_synced_at DATETIME NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_calendar (user_id, google_calendar_id),
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
);

-- -----------------------------------------------------------------------------
-- 9. Migration 012_user_avatar: avatar column (idempotent)
-- -----------------------------------------------------------------------------
SET @avatar_col_exists := (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'Users' AND COLUMN_NAME = 'avatar'
);
SET @avatar_sql := IF(
    @avatar_col_exists = 0,
    'ALTER TABLE Users ADD COLUMN avatar VARCHAR(20) NULL',
    'SELECT ''avatar column already exists'' AS info'
);
PREPARE avatar_stmt FROM @avatar_sql;
EXECUTE avatar_stmt;
DEALLOCATE PREPARE avatar_stmt;

-- -----------------------------------------------------------------------------
-- 10. Migration 012_calendar_sources_events: CalendarSources, CalendarEvents, StudyTimes columns
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS CalendarSources (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  source_type VARCHAR(20) NOT NULL DEFAULT 'google',
  source_label VARCHAR(100) NOT NULL,
  feed_url TEXT,
  feed_url_hash CHAR(64),
  feed_category VARCHAR(20) DEFAULT 'other',
  google_calendar_id VARCHAR(255),
  color VARCHAR(7) DEFAULT '#3B82F6',
  is_writable TINYINT(1) DEFAULT 0,
  source_mode VARCHAR(20) DEFAULT 'import_only',
  is_active TINYINT(1) DEFAULT 1,
  last_synced_at DATETIME NULL,
  sync_error TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,
  UNIQUE KEY uk_user_feed_url (user_id, feed_url_hash),
  UNIQUE KEY uk_user_google_cal (user_id, source_type, google_calendar_id)
);

CREATE TABLE IF NOT EXISTS CalendarEvents (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  source_id INT NOT NULL,
  external_uid VARCHAR(500) NOT NULL,
  recurrence_id VARCHAR(100),
  instance_key VARCHAR(255) NOT NULL DEFAULT 'base',
  title VARCHAR(500) NOT NULL,
  description TEXT,
  location VARCHAR(500),
  start_time DATETIME,
  end_time DATETIME,
  original_timezone VARCHAR(100),
  start_date DATE,
  end_date DATE,
  event_kind VARCHAR(20) NOT NULL DEFAULT 'timed',
  event_category VARCHAR(30) NOT NULL DEFAULT 'other',
  sync_status VARCHAR(20) NOT NULL DEFAULT 'active',
  recurrence_rule TEXT,
  is_recurring_instance TINYINT(1) DEFAULT 0,
  original_data JSON,
  is_locally_modified TINYINT(1) DEFAULT 0,
  local_title VARCHAR(500),
  local_start_time DATETIME,
  local_end_time DATETIME,
  local_notes TEXT,
  local_modified_at DATETIME,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,
  FOREIGN KEY (source_id) REFERENCES CalendarSources(id) ON DELETE CASCADE,
  UNIQUE KEY uk_source_event_instance (source_id, external_uid, instance_key),
  INDEX idx_user_kind (user_id, event_kind),
  INDEX idx_user_dates (user_id, start_time, end_time),
  INDEX idx_sync_status (sync_status)
);

-- StudyTimes: add is_locked, assignment_id, course_id (idempotent)
SET @st_col := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'StudyTimes' AND COLUMN_NAME = 'is_locked');
SET @st_sql := IF(@st_col = 0, 'ALTER TABLE StudyTimes ADD COLUMN is_locked TINYINT(1) DEFAULT 0, ADD COLUMN assignment_id INT NULL, ADD COLUMN course_id INT NULL', 'SELECT 1');
PREPARE st_stmt FROM @st_sql;
EXECUTE st_stmt;
DEALLOCATE PREPARE st_stmt;

-- -----------------------------------------------------------------------------
-- 11. Migration 013: iCal export feed
-- -----------------------------------------------------------------------------
SET @col_exists := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'Users' AND COLUMN_NAME = 'ical_feed_token');
SET @sql := IF(@col_exists = 0, 'ALTER TABLE Users ADD COLUMN ical_feed_token VARCHAR(191) NULL', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'Users' AND COLUMN_NAME = 'ical_feed_enabled');
SET @sql := IF(@col_exists = 0, 'ALTER TABLE Users ADD COLUMN ical_feed_enabled TINYINT(1) NOT NULL DEFAULT 1', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'Users' AND COLUMN_NAME = 'ical_feed_token_updated_at');
SET @sql := IF(@col_exists = 0, 'ALTER TABLE Users ADD COLUMN ical_feed_token_updated_at DATETIME NULL', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @idx_exists := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'Users' AND INDEX_NAME = 'idx_users_ical_feed_token');
SET @sql := IF(@idx_exists = 0, 'CREATE UNIQUE INDEX idx_users_ical_feed_token ON Users (ical_feed_token)', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- -----------------------------------------------------------------------------
-- 12. Migration 014: User profile (avatar_url, banner_url, description)
-- -----------------------------------------------------------------------------
SET @col_exists := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'Users' AND COLUMN_NAME = 'avatar_url');
SET @sql := IF(@col_exists = 0, 'ALTER TABLE Users ADD COLUMN avatar_url VARCHAR(500) NULL', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'Users' AND COLUMN_NAME = 'banner_url');
SET @sql := IF(@col_exists = 0, 'ALTER TABLE Users ADD COLUMN banner_url VARCHAR(500) NULL', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'Users' AND COLUMN_NAME = 'description');
SET @sql := IF(@col_exists = 0, 'ALTER TABLE Users ADD COLUMN description TEXT NULL', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- =============================================================================
-- Done! Your database is ready.
-- =============================================================================
