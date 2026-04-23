-- Migration 015: Add is_completed and completed_at to Assignments
-- Enables assignment completion tracking and filtering from schedule generation.

ALTER TABLE Assignments
  ADD COLUMN IF NOT EXISTS is_completed BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS completed_at DATETIME NULL;
