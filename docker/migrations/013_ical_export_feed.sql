-- 013_ical_export_feed.sql
-- Phase 3: user-level iCal subscription feed token and status.
-- Compatible with MySQL versions that do not support "ADD COLUMN IF NOT EXISTS".

-- ical_feed_token
SET @col_exists := (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'Users' AND COLUMN_NAME = 'ical_feed_token'
);
SET @sql := IF(@col_exists = 0, 'ALTER TABLE Users ADD COLUMN ical_feed_token VARCHAR(191) NULL', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ical_feed_enabled
SET @col_exists := (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'Users' AND COLUMN_NAME = 'ical_feed_enabled'
);
SET @sql := IF(@col_exists = 0, 'ALTER TABLE Users ADD COLUMN ical_feed_enabled TINYINT(1) NOT NULL DEFAULT 1', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ical_feed_token_updated_at
SET @col_exists := (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'Users' AND COLUMN_NAME = 'ical_feed_token_updated_at'
);
SET @sql := IF(@col_exists = 0, 'ALTER TABLE Users ADD COLUMN ical_feed_token_updated_at DATETIME NULL', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Unique index on ical_feed_token (only if it doesn't exist)
SET @idx_exists := (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'Users' AND INDEX_NAME = 'idx_users_ical_feed_token'
);
SET @sql := IF(@idx_exists = 0, 'CREATE UNIQUE INDEX idx_users_ical_feed_token ON Users (ical_feed_token)', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
