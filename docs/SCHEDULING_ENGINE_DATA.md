# Scheduling Engine – Data Guide

When the scheduling engine is implemented, it will pull data from the Railway database. This doc describes the schema and where it comes from.

## Database Shape

### Courses
- `id`, `course_name`, `term_id`

### Assignments
- `id`, `assignment_name`, `work_load`, `notes`, `start_date`, `due_date`, `assignment_type`, `course_id`
- **assignment_type**: `assignment` | `midterm` | `final` | `quiz` | `project` | `participation`
- **work_load**: 15-min increments (e.g. 12 = 3 hours)
- **due_date**: DATETIME (ISO format when via API)

### Meetings (when populated)
- `id`, `course_id`, `start_time`, `end_time`  
- Used for class meeting times (from syllabus `meeting_times`).

## Parsed Syllabus Schema (JSON)

The parser produces JSON with this shape (see `syllabus-schema-template.json`):

```json
{
  "course": {
    "course_code", "course_title", "term", "instructors",
    "meeting_times": [{ "day_of_week": "MO", "start_time": "10:00", "end_time": "11:15", "location" }],
    "location"
  },
  "assessment_categories": [{ "id", "name", "weight_percent" }],
  "assessments": [{
    "id", "title", "category_id", "type", "due_datetime", "weight_percent",
    "recurrence": { "frequency", "interval", "by_day", "until", "count" }
  }]
}
```

**assessment type** → same as `assignment_type` above.

## Flow to DB

1. User uploads syllabus → parser extracts structured JSON.
2. User reviews in sections (Exams, Projects, Assignments, Quizzes, Participation).
3. On confirm → `POST /api/terms/:id/courses` creates course, then `POST /api/courses/:id/assignments` bulk-inserts assignments with `assignment_type`.
4. Scheduling engine queries Courses + Assignments (+ Meetings if used) for a term and builds schedule.

## Migration for Existing DBs

If your Railway DB was created before `assignment_type` was added:

```sql
ALTER TABLE Assignments ADD COLUMN assignment_type VARCHAR(50) NULL;
```

See `docker/migrations/001_add_assignment_type.sql`.
