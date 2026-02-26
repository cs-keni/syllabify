#!/usr/bin/env python3
"""Audit all parsed.json files for completeness and schema consistency."""
import json
from pathlib import Path

SYLLABUS_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "syllabus-data" / "syllabus"
EXTRACTED_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "syllabus-data" / "extracted"

REQUIRED_TOP_KEYS = ["course", "assessment_categories", "assessments", "grading_structure", "late_pass_policy", "schedule", "metadata"]


def audit():
    issues = {
        "null_instructor_name": [],
        "null_instructor_email": [],
        "null_term": [],
        "null_course_code_or_title": [],
        "null_weight_in_assessments": [],
        "empty_assessments": [],
        "empty_instructors": [],
        "assessment_weights_sum": [],  # files where weights don't sum to ~100
    }

    for course_dir in sorted(SYLLABUS_DIR.iterdir()):
        if not course_dir.is_dir():
            continue
        parsed_path = course_dir / "parsed.json"
        if not parsed_path.exists():
            continue

        course_id = course_dir.name
        try:
            with open(parsed_path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            issues.setdefault("parse_error", []).append((course_id, str(e)))
            continue

        # Schema: required top-level keys
        for k in REQUIRED_TOP_KEYS:
            if k not in data:
                issues.setdefault("missing_top_key", []).append((course_id, k))

        course = data.get("course", {})
        instructors = course.get("instructors", [])
        if not instructors:
            issues["empty_instructors"].append(course_id)
        else:
            for i, inst in enumerate(instructors):
                if inst.get("name") is None or inst.get("name") == "":
                    issues["null_instructor_name"].append((course_id, i))
                if inst.get("email") is None or inst.get("email") == "":
                    issues["null_instructor_email"].append((course_id, i))

        if course.get("term") is None:
            issues["null_term"].append(course_id)
        if course.get("course_code") is None or course.get("course_title") is None:
            issues["null_course_code_or_title"].append(course_id)

        assessments = data.get("assessments", [])
        if not assessments:
            issues["empty_assessments"].append(course_id)

        total_weight = 0
        null_weights = 0
        for a in assessments:
            w = a.get("weight_percent")
            if w is None:
                null_weights += 1
            else:
                try:
                    total_weight += float(w)
                except (TypeError, ValueError):
                    pass
        if null_weights > 0:
            issues["null_weight_in_assessments"].append((course_id, null_weights))
        if assessments and total_weight > 0 and abs(total_weight - 100) > 5:
            issues["assessment_weights_sum"].append((course_id, round(total_weight, 1)))

    return issues


if __name__ == "__main__":
    issues = audit()
    print("=== AUDIT REPORT ===\n")
    for key, vals in sorted(issues.items()):
        if vals:
            print(f"{key}: {len(vals)}")
            for v in vals[:15]:
                print(f"  - {v}")
            if len(vals) > 15:
                print(f"  ... and {len(vals) - 15} more")
            print()
