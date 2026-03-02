-- Use this if 005 failed because UserPreferences didn't exist.
-- Creates UserPreferences and adds timezone. Skip this if you already ran the full 005 successfully.

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

ALTER TABLE UserPreferences ADD COLUMN timezone VARCHAR(64) NULL;
