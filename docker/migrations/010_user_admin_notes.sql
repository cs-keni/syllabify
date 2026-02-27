-- Admin notes on users. One note per user, only admins see.
CREATE TABLE IF NOT EXISTS UserAdminNotes (
    user_id INT PRIMARY KEY,
    note_text TEXT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    updated_by_admin_id INT NULL,
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
);
