-- Add recurring meeting format (day_of_week + start/end time) for scheduling engine.
-- Parser outputs: day_of_week (MO,TU,...), start_time "16:00", end_time "17:20".
-- Run on existing databases.
ALTER TABLE Meetings
  ADD COLUMN day_of_week VARCHAR(2) NULL AFTER course_id,
  ADD COLUMN start_time_str VARCHAR(5) NULL AFTER day_of_week,
  ADD COLUMN end_time_str VARCHAR(5) NULL AFTER start_time_str,
  ADD COLUMN location VARCHAR(255) NULL,
  ADD COLUMN meeting_type VARCHAR(50) NULL;
ALTER TABLE Meetings MODIFY COLUMN start_time DATETIME NULL;
ALTER TABLE Meetings MODIFY COLUMN end_time DATETIME NULL;
