-- Syllabify schema for local Docker MySQL (docker-entrypoint-initdb.d).
-- Kept in sync with app models and docker/migrations. Schedules table was removed (merged into Terms).

-- 1. Users (auth)
CREATE TABLE IF NOT EXISTS Users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255),
    security_setup_done BOOLEAN DEFAULT FALSE,
    google_id VARCHAR(255) NULL UNIQUE,
    auth_provider VARCHAR(50) DEFAULT 'local'
);

-- 2. Security answers (password recovery)
CREATE TABLE IF NOT EXISTS UserSecurityAnswers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    question_text VARCHAR(500) NOT NULL,
    answer_hash VARCHAR(255) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
);

-- 3. Terms (semesters/quarters)
CREATE TABLE IF NOT EXISTS Terms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    term_name VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,
    INDEX idx_user_active (user_id, is_active),
    INDEX idx_user_dates (user_id, start_date, end_date)
);

-- 4. Courses (belong to a Term)
CREATE TABLE IF NOT EXISTS Courses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    course_name VARCHAR(255) NOT NULL,
    term_id INT NOT NULL,
    study_hours_per_week INT NULL,
    color VARCHAR(7) NULL,
    FOREIGN KEY (term_id) REFERENCES Terms(id) ON DELETE CASCADE
);

-- 5. Assignments (belong to a Course)
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

-- 6. Meetings (class times, belong to a Course)
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

-- 7. StudyTimes (generated study blocks, belong to a Term; Schedules was merged into Terms)
CREATE TABLE IF NOT EXISTS StudyTimes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    notes VARCHAR(2048) NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    term_id INT NOT NULL,
    FOREIGN KEY (term_id) REFERENCES Terms(id) ON DELETE CASCADE
);

-- 8. User preferences (work hours, days, timezone)
CREATE TABLE IF NOT EXISTS UserPreferences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    work_start VARCHAR(5) NOT NULL DEFAULT '09:00',
    work_end VARCHAR(5) NOT NULL DEFAULT '17:00',
    preferred_days VARCHAR(50) NOT NULL DEFAULT 'MO,TU,WE,TH,FR',
    max_hours_per_day INT NOT NULL DEFAULT 8,
    timezone VARCHAR(64) NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
);

-- 9. Admin settings (maintenance, registration, announcement)
CREATE TABLE IF NOT EXISTS AdminSettings (
    `key` VARCHAR(50) PRIMARY KEY,
    value TEXT
);
INSERT IGNORE INTO AdminSettings (`key`, value) VALUES
('maintenance_enabled', '0'),
('maintenance_message', 'Syllabify is undergoing maintenance. Please try again later.'),
('registration_enabled', '1'),
('announcement_banner', '');

-- 10. Admin audit log
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

-- 11. Admin notes on users
CREATE TABLE IF NOT EXISTS UserAdminNotes (
    user_id INT PRIMARY KEY,
    note_text TEXT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    updated_by_admin_id INT NULL,
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
);

-- 12. Google OAuth tokens (Calendar API)
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

-- 13. Imported calendar events (conflict avoidance)
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

-- 14. Calendar connections (which calendars user has imported)
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
