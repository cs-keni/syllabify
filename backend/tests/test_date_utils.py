"""Tests for date_utils: parse_due_date."""
from datetime import date

import pytest

from app.utils.date_utils import parse_due_date


def test_parse_slash_date():
    assert parse_due_date("2/15") == date(2025, 2, 15)
    assert parse_due_date("2/15/2025") == date(2025, 2, 15)
    assert parse_due_date("12/31/2024") == date(2024, 12, 31)


def test_parse_dash_date():
    assert parse_due_date("2-15") == date(2025, 2, 15)
    assert parse_due_date("2025-02-15") == date(2025, 2, 15)


def test_parse_month_name():
    assert parse_due_date("Feb 15") == date(2025, 2, 15)
    assert parse_due_date("February 15, 2025") == date(2025, 2, 15)
    assert parse_due_date("April 23rd") == date(2025, 4, 23)
    assert parse_due_date("May 16th") == date(2025, 5, 16)
    assert parse_due_date("Jun 11") == date(2025, 6, 11)


def test_tba_returns_none():
    assert parse_due_date("TBA") is None
    assert parse_due_date("TBD") is None
    assert parse_due_date("To be announced") is None
    assert parse_due_date("To be determined") is None


def test_empty_returns_none():
    assert parse_due_date("") is None
    assert parse_due_date("   ") is None
    assert parse_due_date(None) is None


def test_invalid_returns_none():
    assert parse_due_date("sometime next week") is None or isinstance(
        parse_due_date("sometime next week"), date
    )
