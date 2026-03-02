-- Fix Railway Assignments table if it was created before railway-schema.sql
-- (e.g. "Unknown column 'a.course_id'", "start_date", or "due_date").
-- Run in MySQL Workbench: connect to Railway, select database "railway", then
-- run each statement. If you get "Duplicate column" or "Duplicate key", skip that statement.

-- 1. Add course_id if missing (required for list_courses JOIN)
ALTER TABLE Assignments ADD COLUMN course_id INT NULL;

-- 2. Add start_date if missing (required for add_assignments INSERT)
ALTER TABLE Assignments ADD COLUMN start_date DATETIME NULL DEFAULT (CURRENT_TIMESTAMP);

-- 3. Add due_date if missing (required for add_assignments INSERT)
ALTER TABLE Assignments ADD COLUMN due_date DATETIME NULL DEFAULT (CURRENT_TIMESTAMP);

-- 3b. Add assignment_type if missing (assignment|midterm|final|quiz|project|participation)
ALTER TABLE Assignments ADD COLUMN assignment_type VARCHAR(50) NULL;

-- 4. If Assignments had rows with NULL course_id, set them or clear the table first, e.g.:
--    DELETE FROM Assignments WHERE course_id IS NULL;
-- Then make course_id NOT NULL and add foreign key (skip if column already had FK):
ALTER TABLE Assignments MODIFY COLUMN course_id INT NOT NULL;
ALTER TABLE Assignments ADD CONSTRAINT fk_assignments_course
    FOREIGN KEY (course_id) REFERENCES Courses(id) ON DELETE CASCADE;

-- 5. Make start_date NOT NULL (skip if already NOT NULL)
ALTER TABLE Assignments MODIFY COLUMN start_date DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP);

-- 6. Make due_date NOT NULL (skip if already NOT NULL)
ALTER TABLE Assignments MODIFY COLUMN due_date DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP);

-- 7. Legacy: if Assignments has schedule_id NOT NULL, the app doesn't set it (uses course_id). Allow NULL.
ALTER TABLE Assignments MODIFY COLUMN schedule_id INT NULL;
