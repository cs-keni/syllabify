-- 012_calendar_sources_events.sql
-- Phase 1: Unified calendar sources and events tables

-- 1. CalendarSources — tracks all import sources (Google, ICS URL)
CREATE TABLE IF NOT EXISTS CalendarSources (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  source_type VARCHAR(20) NOT NULL DEFAULT 'google',       -- 'google' | 'ics_url'
  source_label VARCHAR(100) NOT NULL,
  feed_url TEXT,
  feed_url_hash CHAR(64),                                   -- SHA-256 for uniqueness
  feed_category VARCHAR(20) DEFAULT 'other',                -- 'canvas' | 'personal' | 'work' | 'academic' | 'other'
  google_calendar_id VARCHAR(255),
  color VARCHAR(7) DEFAULT '#3B82F6',
  is_writable TINYINT(1) DEFAULT 0,
  source_mode VARCHAR(20) DEFAULT 'import_only',            -- 'import_only' | 'two_way'
  is_active TINYINT(1) DEFAULT 1,
  last_synced_at DATETIME NULL,
  sync_error TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,
  UNIQUE KEY uk_user_feed_url (user_id, feed_url_hash),
  UNIQUE KEY uk_user_google_cal (user_id, source_type, google_calendar_id)
);

-- 2. CalendarEvents — unified storage for all imported events
CREATE TABLE IF NOT EXISTS CalendarEvents (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  source_id INT NOT NULL,
  external_uid VARCHAR(500) NOT NULL,
  recurrence_id VARCHAR(100),
  instance_key VARCHAR(255) NOT NULL DEFAULT 'base',        -- 'base' | 'master' | recurrence_id | provider instance id

  title VARCHAR(500) NOT NULL,
  description TEXT,
  location VARCHAR(500),

  start_time DATETIME,
  end_time DATETIME,
  original_timezone VARCHAR(100),

  start_date DATE,
  end_date DATE,

  event_kind VARCHAR(20) NOT NULL DEFAULT 'timed',          -- 'timed' | 'all_day' | 'deadline_marker'
  event_category VARCHAR(30) NOT NULL DEFAULT 'other',      -- 'class' | 'office_hours' | 'exam' | 'assignment_deadline' | 'meeting' | 'blocked_time' | 'personal' | 'work' | 'other'

  sync_status VARCHAR(20) NOT NULL DEFAULT 'active',        -- 'active' | 'cancelled' | 'deleted_at_source' | 'stale'

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

-- 3. Extend StudyTimes for locked/pinned support (Phase 2 prep)
ALTER TABLE StudyTimes
  ADD COLUMN is_locked TINYINT(1) DEFAULT 0,
  ADD COLUMN assignment_id INT NULL,
  ADD COLUMN course_id INT NULL;

-- Note: Not adding FK constraints on assignment_id/course_id here because
-- MySQL requires the referenced column to have an index, and we want
-- ON DELETE SET NULL behavior which we'll handle in application code.
