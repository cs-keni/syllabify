-- Per-course cap: max study hours per week for the scheduler (optional)
-- Run on existing databases that don't have this column yet
ALTER TABLE Courses ADD COLUMN study_hours_per_week INT NULL;
