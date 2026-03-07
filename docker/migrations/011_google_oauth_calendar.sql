-- Google OAuth and Calendar Import
-- Adds google_id, auth_provider to Users; UserOAuthTokens; ExternalEvents; UserCalendarConnections.
-- Run once. If you see "Duplicate column", that column already exists.

-- 1. Users: add google_id and auth_provider
ALTER TABLE Users ADD COLUMN google_id VARCHAR(255) NULL UNIQUE;
ALTER TABLE Users ADD COLUMN auth_provider VARCHAR(50) DEFAULT 'local';

-- 2. UserOAuthTokens: store Google OAuth tokens for Calendar API
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

-- 3. ExternalEvents: imported calendar events for conflict avoidance
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

-- 4. UserCalendarConnections: track which calendars user has imported
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
