-- Add profile avatar selection to users.
-- Allowed values in app layer: red | green | blue
-- Compatible with MySQL versions that do not support
-- "ADD COLUMN IF NOT EXISTS".

SET @avatar_col_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'Users'
      AND COLUMN_NAME = 'avatar'
);

SET @avatar_sql := IF(
    @avatar_col_exists = 0,
    'ALTER TABLE Users ADD COLUMN avatar VARCHAR(20) NULL',
    'SELECT ''avatar column already exists'' AS info'
);

PREPARE avatar_stmt FROM @avatar_sql;
EXECUTE avatar_stmt;
DEALLOCATE PREPARE avatar_stmt;
