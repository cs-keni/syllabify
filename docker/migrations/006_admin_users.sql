-- Add initial admin accounts. Run in Railway MySQL console (Query tab) or any MySQL client.
-- Password for all: Changeme123!
-- Admins should change their password in Preferences after first login.
-- Uses INSERT IGNORE so existing users are not overwritten.

-- Ensure is_admin column exists (migration 003)
-- ALTER TABLE Users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;

INSERT IGNORE INTO Users (username, password_hash, security_setup_done, is_admin) VALUES
('admin-andrew',     '$2b$12$ZXgg0wuDJmleqk1sNzm2LOpAaeLyTEqBUyBI2pr5cV3GFyidxoT3m', FALSE, TRUE),
('admin-leon',       '$2b$12$ZXgg0wuDJmleqk1sNzm2LOpAaeLyTEqBUyBI2pr5cV3GFyidxoT3m', FALSE, TRUE),
('admin-saintgeorge','$2b$12$ZXgg0wuDJmleqk1sNzm2LOpAaeLyTEqBUyBI2pr5cV3GFyidxoT3m', FALSE, TRUE),
('admin-kenny',      '$2b$12$ZXgg0wuDJmleqk1sNzm2LOpAaeLyTEqBUyBI2pr5cV3GFyidxoT3m', FALSE, TRUE);
