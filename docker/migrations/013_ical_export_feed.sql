-- 013_ical_export_feed.sql
-- Phase 3: user-level iCal subscription feed token and status.

ALTER TABLE Users
  ADD COLUMN IF NOT EXISTS ical_feed_token VARCHAR(191) NULL,
  ADD COLUMN IF NOT EXISTS ical_feed_enabled TINYINT(1) NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS ical_feed_token_updated_at DATETIME NULL;

CREATE UNIQUE INDEX idx_users_ical_feed_token
  ON Users (ical_feed_token);
