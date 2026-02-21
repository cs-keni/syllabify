"""
Validate all parsed.json files against the syllabus schema.
Reports any structural or value inconsistencies.
"""
import json
from pathlib import Path

SYLLABUS_DIR = Path(__file__).resolve().parent / "fixtures" / "syllabus-data" / "syllabus"
TEMPLATE_PATH = Path(__file__).resolve().parent / "fixtures" / "syllabus-data" / "syllabus-schema-template.json"

# Expected structure derived from schema
REQUIRED_TOP_LEVEL = {"course", "assessment_categories", "assessments", "grading_structure", "late_pass_policy", "schedule", "metadata"}
COURSE_KEYS = {"id", "course_code", "course_title", "term", "timezone", "instructors", "meeting_times", "location"}
INSTRUCTOR_KEYS = {"id", "name", "email"}
MEETING_TIME_KEYS = {"id", "day_of_week", "start_time", "end_time", "timezone", "location", "type"}
CATEGORY_KEYS = {"id", "name", "weight_percent", "drop_lowest", "subcategories", "grading_bucket"}
ASSESSMENT_KEYS = {"id", "title", "category_id", "type", "due_datetime", "all_day", "timezone", "weight_percent", "points", "recurrence", "policies", "confidence", "source_excerpt"}
RECURRENCE_KEYS = {"frequency", "interval", "by_day", "until", "count"}
POLICIES_KEYS = {"late_policy", "late_pass_allowed"}
GRADING_STRUCTURE_KEYS = {"type", "buckets"}
BUCKET_KEYS = {"id", "name", "weight_percent"}
LATE_PASS_KEYS = {"total_allowed", "extension_days"}
SCHEDULE_ITEM_KEYS = {"id", "week", "date", "type", "topic"}
METADATA_KEYS = {"created_at", "updated_at", "source_type", "schema_version"}

VALID_DAY_OF_WEEK = {"MO", "TU", "WE", "TH", "FR", "SA", "SU"}
VALID_ASSESSMENT_TYPES = {"assignment", "project", "midterm", "final", "quiz", "participation", "exam"}
VALID_GRADING_TYPES = {"flat", "bucketed"}


def validate_file(path: Path) -> list[str]:
    errors = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]

    # Top-level keys
    if set(data.keys()) != REQUIRED_TOP_LEVEL:
        missing = REQUIRED_TOP_LEVEL - set(data.keys())
        extra = set(data.keys()) - REQUIRED_TOP_LEVEL
        if missing:
            errors.append(f"Missing top-level keys: {missing}")
        if extra:
            errors.append(f"Unexpected top-level keys: {extra}")

    # course
    course = data.get("course")
    if course is not None:
        if set(course.keys()) != COURSE_KEYS:
            missing = COURSE_KEYS - set(course.keys())
            if missing:
                errors.append(f"course missing keys: {missing}")
        if "instructors" in course and course["instructors"]:
            for i, inst in enumerate(course["instructors"]):
                if not isinstance(inst, dict):
                    errors.append(f"instructor[{i}] not a dict")
                elif set(inst.keys()) != INSTRUCTOR_KEYS:
                    errors.append(f"instructor[{i}] keys mismatch: {set(inst.keys())}")
        if "meeting_times" in course and course["meeting_times"]:
            for i, mt in enumerate(course["meeting_times"]):
                if not isinstance(mt, dict):
                    errors.append(f"meeting_times[{i}] not a dict")
                elif set(mt.keys()) != MEETING_TIME_KEYS:
                    errors.append(f"meeting_times[{i}] keys mismatch: {set(mt.keys())}")
                elif mt.get("day_of_week") and mt["day_of_week"] not in VALID_DAY_OF_WEEK:
                    errors.append(f"meeting_times[{i}] invalid day_of_week: {mt.get('day_of_week')}")

    # assessment_categories
    cats = data.get("assessment_categories", [])
    if not isinstance(cats, list):
        errors.append("assessment_categories must be a list")
    else:
        for i, c in enumerate(cats):
            if set(c.keys()) != CATEGORY_KEYS:
                errors.append(f"assessment_categories[{i}] keys mismatch: {set(c.keys())}")

    # assessments
    assess = data.get("assessments", [])
    if not isinstance(assess, list):
        errors.append("assessments must be a list")
    else:
        for i, a in enumerate(assess):
            if set(a.keys()) != ASSESSMENT_KEYS:
                errors.append(f"assessments[{i}] keys mismatch: {set(a.keys())}")
            if a.get("type") and a["type"] not in VALID_ASSESSMENT_TYPES:
                errors.append(f"assessments[{i}] invalid type: {a.get('type')}")
            if a.get("recurrence") is not None:
                if not isinstance(a["recurrence"], dict):
                    errors.append(f"assessments[{i}] recurrence must be dict or null")
                elif set(a["recurrence"].keys()) != RECURRENCE_KEYS:
                    errors.append(f"assessments[{i}] recurrence keys mismatch")
            if "policies" in a and a["policies"] is not None:
                if not isinstance(a["policies"], dict):
                    errors.append(f"assessments[{i}] policies must be dict")
                elif not (set(a["policies"].keys()) <= POLICIES_KEYS):
                    errors.append(f"assessments[{i}] policies has unexpected keys")

    # grading_structure
    gs = data.get("grading_structure")
    if gs:
        if set(gs.keys()) != GRADING_STRUCTURE_KEYS:
            errors.append(f"grading_structure keys mismatch: {set(gs.keys())}")
        if gs.get("type") and gs["type"] not in VALID_GRADING_TYPES:
            errors.append(f"grading_structure invalid type: {gs.get('type')}")
        if gs.get("buckets"):
            for i, b in enumerate(gs["buckets"]):
                if set(b.keys()) != BUCKET_KEYS:
                    errors.append(f"grading_structure.buckets[{i}] keys mismatch")

    # late_pass_policy
    lp = data.get("late_pass_policy")
    if lp and set(lp.keys()) != LATE_PASS_KEYS:
        errors.append(f"late_pass_policy keys mismatch: {set(lp.keys())}")

    # schedule
    sched = data.get("schedule", [])
    if sched and sched[0]:
        for i, s in enumerate(sched):
            if s and set(s.keys()) != SCHEDULE_ITEM_KEYS:
                errors.append(f"schedule[{i}] keys mismatch")

    # metadata
    meta = data.get("metadata")
    if meta and set(meta.keys()) != METADATA_KEYS:
        errors.append(f"metadata keys mismatch: {set(meta.keys())}")

    return errors


def main():
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    print("Schema template loaded. Expected top-level keys:", sorted(template.keys()))
    print()

    all_parsed = sorted(SYLLABUS_DIR.glob("*/parsed.json"))
    print(f"Validating {len(all_parsed)} parsed.json files...\n")

    issues = {}
    for path in all_parsed:
        course_name = path.parent.name
        errs = validate_file(path)
        if errs:
            issues[course_name] = errs

    if not issues:
        print("PASS: All parsed.json files conform to the schema.")
        return 0

    print("FAIL: Schema validation issues found:\n")
    for course in sorted(issues.keys()):
        print(f"  {course}:")
        for e in issues[course]:
            print(f"    - {e}")
        print()
    return 1


if __name__ == "__main__":
    exit(main())
