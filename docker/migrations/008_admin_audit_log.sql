-- Admin audit log for accountability. Logs who did what, when.
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
