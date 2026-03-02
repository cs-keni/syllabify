-- Per-course color (hex, e.g. #0f8a4c) and user timezone (IANA, e.g. America/Chicago)
-- Run on existing DB: mysql -u syllabify -p syllabify < docker/migrations/005_course_color_timezone.sql
-- Creates UserPreferences if missing (Railway/legacy DBs may not have run 004), then adds timezone.
-- Order: UserPreferences first (so it runs even if Courses.color already exists).
-- Ignore "Duplicate column" errors if you've run this before.

-- 1. Ensure UserPreferences exists (from migration 004)
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

-- 2. Add timezone to UserPreferences
ALTER TABLE UserPreferences ADD COLUMN timezone VARCHAR(64) NULL;

-- 3. Add color to Courses (skip if you get "Duplicate column name 'color'")
ALTER TABLE Courses ADD COLUMN color VARCHAR(7) NULL;
