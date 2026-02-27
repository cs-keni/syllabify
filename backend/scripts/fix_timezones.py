#!/usr/bin/env python3
"""
Fix timezone in parsed.json based on institution detected from extracted text.
"""
import json
from pathlib import Path

SYLLABUS_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "syllabus-data" / "syllabus"
EXTRACTED_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "syllabus-data" / "extracted"


def detect_institution(extracted: str) -> str | None:
    text_lower = extracted.lower()
    if "utexas" in text_lower or "austin.utexas" in text_lower or "university of texas at austin" in text_lower:
        return "America/Chicago"
    if "uoregon" in text_lower or "uoregon.edu" in text_lower or "university of oregon" in text_lower:
        return "America/Los_Angeles"
    if "psu.edu" in text_lower or "penn state" in text_lower or "penn state harrisburg" in text_lower:
        return "America/New_York"
    return None


def set_tz_recursive(obj, old_tz: str, new_tz: str) -> int:
    """Update all timezone values in nested structure. Returns count of changes."""
    changes = 0
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "timezone" and v == old_tz:
                obj[k] = new_tz
                changes += 1
            else:
                changes += set_tz_recursive(v, old_tz, new_tz)
    elif isinstance(obj, list):
        for item in obj:
            changes += set_tz_recursive(item, old_tz, new_tz)
    return changes


def fix_file(course_id: str, expected_tz: str) -> bool:
    parsed_path = SYLLABUS_DIR / course_id / "parsed.json"
    if not parsed_path.exists():
        return False
    with open(parsed_path, encoding="utf-8") as f:
        data = json.load(f)
    current = data.get("course", {}).get("timezone")
    if current == expected_tz:
        return False
    n = set_tz_recursive(data, current, expected_tz)
    if n == 0:
        return False
    with open(parsed_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return True


def main():
    fixed = 0
    for course_dir in sorted(SYLLABUS_DIR.iterdir()):
        if not course_dir.is_dir():
            continue
        course_id = course_dir.name
        extracted_path = EXTRACTED_DIR / f"{course_id}.txt"
        if not extracted_path.exists():
            continue
        with open(extracted_path, encoding="utf-8", errors="replace") as f:
            extracted = f.read()
        expected_tz = detect_institution(extracted)
        if expected_tz and fix_file(course_id, expected_tz):
            fixed += 1
            print(f"Fixed {course_id} -> {expected_tz}")
    print(f"\nFixed {fixed} files")


if __name__ == "__main__":
    main()
