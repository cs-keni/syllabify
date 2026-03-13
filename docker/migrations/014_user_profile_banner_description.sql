-- 014_user_profile_banner_description.sql
-- Add profile banner, description, and custom avatar URL (supports GIFs).
-- avatar: preset key (red/green/blue). avatar_url: custom image URL (overrides avatar when set).

SET @col_exists := (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'Users' AND COLUMN_NAME = 'avatar_url'
);
SET @sql := IF(@col_exists = 0, 'ALTER TABLE Users ADD COLUMN avatar_url VARCHAR(500) NULL', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists := (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'Users' AND COLUMN_NAME = 'banner_url'
);
SET @sql := IF(@col_exists = 0, 'ALTER TABLE Users ADD COLUMN banner_url VARCHAR(500) NULL', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists := (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'Users' AND COLUMN_NAME = 'description'
);
SET @sql := IF(@col_exists = 0, 'ALTER TABLE Users ADD COLUMN description TEXT NULL', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
