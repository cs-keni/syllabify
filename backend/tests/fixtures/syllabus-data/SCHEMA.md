# Syllabus Extraction Schema

Generic JSON schema for parsed syllabus data. Supports flat and bucketed grading, iCal-style recurrence, calendar export, and schedule generation.

**Design goals:** IDs on all referencable objects, structured datetimes for calendar export, RFC5545-aligned recurrence, and metadata for versioning.

---

## JSON Schema Template

See `syllabus-schema-template.json` for the full template.

---

## Section Explanations

| Section | Purpose |
|--------|---------|
| **course** | Top-level metadata. `id` for references. `instructors` as objects (id, name, email). `meeting_times` structured: `day_of_week` (iCal: MO, TU, WE...), `start_time`, `end_time`, `timezone`, `location`, `type`. `timezone` default for the course. |
| **assessment_categories** | Groups of graded work (Projects, Exams, Quizzes). `drop_lowest` per category. `grading_bucket` links to bucketed grading. |
| **assessments** | Individual graded items. `due_datetime` (ISO 8601) instead of `due_date`—supports calendar export. `all_day`, `timezone` for ambiguous cases. `recurrence` follows RFC5545: `frequency` (weekly, daily), `interval`, `by_day`, `until`, `count`. `confidence` and `source_excerpt` for parser debugging. |
| **grading_structure** | `type`: **flat** (items sum to 100%) or **bucketed** (buckets have weights; items roll up). `buckets` have `id` for reference. |
| **late_pass_policy** | Global policy: `total_allowed`, `extension_days`. Extracted from syllabus text. |
| **schedule** | Week-by-week events. `id` for reference. `date` (YYYY-MM-DD), `type`, `topic`. |
| **metadata** | `created_at`, `updated_at`, `source_type` (pdf, docx, manual), `schema_version`. |

---

## Key Design Decisions

### Why `due_datetime` instead of `due_date`?

Calendar export (Google, Apple, iCal) needs full datetimes. Syllabi often give only dates (e.g. "Feb 20"); use `all_day: true` and `due_datetime: "2026-02-20"` (date-only ISO is valid). For "Friday 11:59 PM", use `due_datetime: "2026-02-20T23:59:00"`, `all_day: false`.

### Why structured `meeting_times`?

Unstructured strings like "Wed 4:00–5:20 PM" can’t be turned into recurring calendar events. With `day_of_week`, `start_time`, `end_time`, `timezone`, we can generate iCal RRULE.

### Why `recurrence` on assessments?

Weekly homework, daily quizzes need recurrence rules for calendar. RFC5545 `frequency`, `interval`, `by_day` map directly to iCal and Google Calendar.

### Why IDs everywhere?

Updating one assessment, instructor, or schedule entry without IDs forces brittle array-index logic. IDs enable references and clean partial updates.

---

## Example: CS 425 (Concepts in Programming Languages)

```json
{
  "course": {
    "id": "cs425-s25",
    "course_code": "CIS 425",
    "course_title": "Concepts in Programming Languages",
    "term": "Spring 2025",
    "timezone": "America/Los_Angeles",
    "instructors": [
      { "id": "inst-1", "name": "Zena M. Ariola", "email": "ariola@uoregon.edu" },
      { "id": "inst-2", "name": "William Qiu", "email": "williamq@uoregon.edu" }
    ],
    "meeting_times": [
      {
        "id": "mt-1",
        "day_of_week": "WE",
        "start_time": "16:00",
        "end_time": "17:20",
        "timezone": "America/Los_Angeles",
        "location": "McKenzie 221",
        "type": "lecture"
      },
      {
        "id": "mt-2",
        "day_of_week": "FR",
        "start_time": "16:00",
        "end_time": "17:20",
        "timezone": "America/Los_Angeles",
        "location": "McKenzie 221",
        "type": "lecture"
      },
      {
        "id": "mt-3",
        "day_of_week": "MO",
        "start_time": "08:30",
        "end_time": "09:50",
        "timezone": "America/Los_Angeles",
        "location": "McKenzie 221",
        "type": "discussion"
      }
    ],
    "location": "McKenzie 221"
  },
  "assessment_categories": [
    {
      "id": "exams",
      "name": "Exams",
      "weight_percent": 100,
      "drop_lowest": null,
      "subcategories": [],
      "grading_bucket": null
    }
  ],
  "assessments": [
    {
      "id": "midterm_1",
      "title": "Midterm 1",
      "category_id": "exams",
      "type": "midterm",
      "due_datetime": "2025-04-23",
      "all_day": true,
      "timezone": "America/Los_Angeles",
      "weight_percent": 30,
      "points": null,
      "recurrence": { "frequency": null, "interval": null, "by_day": null, "until": null, "count": null },
      "policies": { "late_policy": null, "late_pass_allowed": null },
      "confidence": 0.95,
      "source_excerpt": "Midterm 1     30%   April 23rd  (Week 4 Wednesday"
    },
    {
      "id": "midterm_2",
      "title": "Midterm 2",
      "category_id": "exams",
      "type": "midterm",
      "due_datetime": "2025-05-16",
      "all_day": true,
      "timezone": "America/Los_Angeles",
      "weight_percent": 30,
      "points": null,
      "recurrence": null,
      "policies": {},
      "confidence": 0.95,
      "source_excerpt": "Midterm 2     30%   May 16th (Week 7 Friday)"
    },
    {
      "id": "final",
      "title": "Final",
      "category_id": "exams",
      "type": "final",
      "due_datetime": "2025-06-11T14:45:00",
      "all_day": false,
      "timezone": "America/Los_Angeles",
      "weight_percent": 40,
      "points": null,
      "recurrence": null,
      "policies": {},
      "confidence": 0.95,
      "source_excerpt": "Final               40%   Wednesday, Jun 11th, 2025, 2:45 p.m"
    }
  ],
  "grading_structure": {
    "type": "flat",
    "buckets": []
  },
  "late_pass_policy": {
    "total_allowed": null,
    "extension_days": null
  },
  "schedule": [],
  "metadata": {
    "created_at": null,
    "updated_at": null,
    "source_type": "txt",
    "schema_version": "1.0"
  }
}
```

---

## iCal / RFC5545 Reference

For `recurrence` and `meeting_times.day_of_week`:

- **day_of_week**: `MO`, `TU`, `WE`, `TH`, `FR`, `SA`, `SU`
- **frequency**: `yearly`, `monthly`, `weekly`, `daily`, `hourly`
- **interval**: integer (e.g. `2` = every 2 weeks)
- **by_day**: array of day codes
- **until**: ISO date (exclusive end)
- **count**: number of occurrences
