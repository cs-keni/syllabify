-- User preferences for scheduling (work hours, days)
-- One row per user. Created lazily on first GET.

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
