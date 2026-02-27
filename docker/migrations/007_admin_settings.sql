-- AdminSettings for maintenance mode and other config.
-- Run in Railway MySQL or apply locally.
CREATE TABLE IF NOT EXISTS AdminSettings (
    key VARCHAR(50) PRIMARY KEY,
    value TEXT
);
INSERT IGNORE INTO AdminSettings (key, value) VALUES
('maintenance_enabled', '0'),
('maintenance_message', 'Syllabify is undergoing maintenance. Please try again later.');
