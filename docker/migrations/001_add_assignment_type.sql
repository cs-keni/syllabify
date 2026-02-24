-- Add assignment_type for scheduling engine (assignment|midterm|final|quiz|project|participation)
-- Run on existing databases that don't have this column yet
ALTER TABLE Assignments ADD COLUMN assignment_type VARCHAR(50) NULL;
