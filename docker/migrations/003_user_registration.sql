-- User registration and admin support
-- Add email, is_admin, is_disabled to Users.
-- Run once. If you see "Duplicate column", that column already exists.

ALTER TABLE Users ADD COLUMN email VARCHAR(255) NULL UNIQUE;
ALTER TABLE Users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;
ALTER TABLE Users ADD COLUMN is_disabled BOOLEAN DEFAULT FALSE;
