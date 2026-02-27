#!/usr/bin/env python3
"""
Verify parsed.json ground truth against extracted text for test fixture accuracy.
Reports timezone mismatches, missing fields, and potential inaccuracies.
"""
import json
from pathlib import Path

SYLLABUS_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "syllabus-data" / "syllabus"
EXTRACTED_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "syllabus-data" / "extracted"

# Institution markers in extracted text -> expected timezone
INSTITUTION_TZ = {
    "utexas": "America/Chicago",      # UT Austin - Central
    "uoregon": "America/Los_Angeles", # U Oregon - Pacific
    "psu.edu": "America/New_York",   # Penn State - Eastern
    "penn state": "America/New_York",
}


def detect_institution(extracted: str) -> str | None:
    """Return expected timezone based on institution markers in extracted text."""
    text_lower = extracted.lower()
    if "utexas" in text_lower or "austin.utexas" in text_lower or "university of texas at austin" in text_lower:
        return "America/Chicago"
    if "uoregon" in text_lower or "uoregon.edu" in text_lower or "university of oregon" in text_lower:
        return "America/Los_Angeles"
    if "psu.edu" in text_lower or "penn state" in text_lower or "penn state harrisburg" in text_lower:
        return "America/New_York"
    return None


def main():
    tz_mismatches = []
    missing_extracted = []
    null_instructors = []
    null_terms = []

    for course_dir in sorted(SYLLABUS_DIR.iterdir()):
        if not course_dir.is_dir():
            continue
        course_id = course_dir.name
        parsed_path = course_dir / "parsed.json"
        extracted_path = EXTRACTED_DIR / f"{course_id}.txt"

        if not parsed_path.exists():
            continue

        try:
            with open(parsed_path, encoding="utf-8") as f:
                parsed = json.load(f)
        except Exception as e:
            print(f"Parse error {course_id}: {e}")
            continue

        course = parsed.get("course", {})
        current_tz = course.get("timezone")

        # Check extracted for institution
        if extracted_path.exists():
            with open(extracted_path, encoding="utf-8", errors="replace") as f:
                extracted = f.read()
            expected_tz = detect_institution(extracted)
            if expected_tz and current_tz != expected_tz:
                tz_mismatches.append((course_id, current_tz, expected_tz))
        else:
            missing_extracted.append(course_id)

        # Null checks
        instructors = course.get("instructors", [])
        if not instructors or all(not i.get("name") for i in instructors):
            null_instructors.append(course_id)
        if not course.get("term"):
            null_terms.append(course_id)

    print("=== TIMEZONE MISMATCHES (institution in extracted -> wrong tz in parsed) ===\n")
    for cid, current, expected in tz_mismatches:
        print(f"  {cid}: has {current} -> should be {expected}")

    print("\n=== SUMMARY ===")
    print(f"  Timezone mismatches: {len(tz_mismatches)}")
    print(f"  No extracted text: {len(missing_extracted)}")
    print(f"  Null/empty instructors: {len(null_instructors)}")
    print(f"  Null term: {len(null_terms)}")

    return tz_mismatches, null_instructors, null_terms


if __name__ == "__main__":
    main()
