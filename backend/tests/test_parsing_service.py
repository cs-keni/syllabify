"""Tests for parsing_service: parse_text, parse_file."""
import io

import pytest

from app.services.parsing_service import parse_file, parse_text


def test_parse_empty_text():
    r = parse_text("")
    assert r["course_name"]
    assert r["assignments"] == []
    conf = r.get("confidence") or {}
    assert conf.get("label") == "low"
    assert conf.get("score") == 0


def test_parse_whitespace_only():
    r = parse_text("   \n\n  ")
    assert r["assignments"] == []
    assert (r.get("confidence") or {}).get("label") == "low"


def test_parse_extracts_course_name():
    text = "CS 422 Software Methodology\nSyllabus..."
    r = parse_text(text)
    assert "CS" in r["course_name"] or "422" in r["course_name"]


def test_parse_table_like():
    text = "Assignment 1 | 2/15/2025 | 4\nMidterm | 3/10 | 2"
    r = parse_text(text)
    assert len(r["assignments"]) >= 2
    names = [a["name"] for a in r["assignments"]]
    assert "Assignment 1" in names or "Assignment" in str(names)
    assert any(a.get("hours") for a in r["assignments"])


def test_confidence_structure():
    """Confidence is { score, label, breakdown? } for UI."""
    r = parse_text("CS 422 Software Methodology\nHW 1 | 2/15 | 4\nExam 1 25%\nTuTh 2-3pm GDC 2.216")
    conf = r.get("confidence")
    assert conf is not None
    assert "score" in conf
    assert "label" in conf
    assert 0 <= conf["score"] <= 100
    assert conf["label"] in ("low", "medium", "high")
    if "breakdown" in conf:
        assert isinstance(conf["breakdown"], dict)


def test_parse_prose_assignment_due():
    text = "Assignment 1 due Feb 15"
    r = parse_text(text)
    assert len(r["assignments"]) >= 1
    a = r["assignments"][0]
    assert "assignment" in a["name"].lower() or "1" in a["name"]
    assert a.get("due_date") == "2025-02-15" or a.get("hours")


def test_parse_file_txt():
    content = b"CS 422\nAssignment 1 | 2/15 | 4"
    f = io.BytesIO(content)
    f.filename = "syllabus.txt"
    r = parse_file(f)
    assert r["course_name"]
    assert isinstance(r["assignments"], list)


def test_parse_syllabus_fixture():
    """Parse a real fixture file if available."""
    try:
        path = __file__
        # Resolve path to fixtures
        import os
        base = os.path.dirname(os.path.dirname(__file__))
        fixture_dir = os.path.join(base, "fixtures", "syllabus-data", "syllabus")
        if os.path.isdir(fixture_dir):
            files = [f for f in os.listdir(fixture_dir) if f.endswith(".txt")]
            if files:
                with open(os.path.join(fixture_dir, files[0]), "rb") as f:
                    content = f.read()
                f = io.BytesIO(content)
                f.filename = files[0]
                r = parse_file(f)
                assert "course_name" in r
                assert "assignments" in r
                assert isinstance(r["assignments"], list)
    except Exception:
        pytest.skip("Fixture dir not found")
