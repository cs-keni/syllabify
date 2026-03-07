from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.assignment import Assignment
from app.models.calendar_event import CalendarEvent  # ensure mapper registration
from app.models.calendar_source import CalendarSource  # ensure mapper registration
from app.models.course import Course
from app.models.meeting import Meeting  # ensure mapper registration
from app.models.study_time import StudyTime
from app.models.term import Term
from app.models.user import User
from app.services.scheduling_service import generate_study_times


@pytest.fixture
def db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_user(db_session):
    user = User(username="scheduler-test-user")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def sample_term(db_session, sample_user):
    term = Term(
        user_id=sample_user.id,
        term_name="Winter 2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        is_active=True,
    )
    db_session.add(term)
    db_session.commit()
    return term


@pytest.fixture
def sample_course(db_session, sample_term):
    course = Course(course_name="CS 422", term_id=sample_term.id)
    db_session.add(course)
    db_session.commit()
    return course


@pytest.fixture
def sample_assignment(db_session, sample_course):
    assignment = Assignment(
        assignment_name="Project Milestone 1",
        work_load=8,  # 8 x 15 minutes = 2 hours
        notes=None,
        start_date=datetime(2026, 1, 5, 8, 0, tzinfo=timezone.utc),
        due_date=datetime(2026, 1, 6, 8, 0, tzinfo=timezone.utc),
        assignment_type="project",
        course_id=sample_course.id,
    )
    db_session.add(assignment)
    db_session.commit()
    return assignment


def test_study_times_have_assignment_and_course_ids(db_session, sample_term, sample_assignment):
    created = generate_study_times(db_session, sample_term.id)
    assert len(created) > 0
    for st in created:
        assert st.assignment_id is not None
        assert st.course_id is not None
        # keep type check to ensure relationship identity is correctly propagated
        assert isinstance(st, StudyTime)


def test_calendar_event_blocks_study_slot(db_session, sample_term, sample_user, sample_assignment):
    src = CalendarSource(
        user_id=sample_user.id,
        source_type="ics_url",
        source_label="Test Source",
        feed_category="other",
    )
    db_session.add(src)
    db_session.flush()

    block_start = datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc)
    block_end = datetime(2026, 1, 5, 17, 0, tzinfo=timezone.utc)
    evt = CalendarEvent(
        user_id=sample_user.id,
        source_id=src.id,
        external_uid="test-block-event",
        instance_key="base",
        title="Blocked Window",
        event_kind="timed",
        sync_status="active",
        start_time=block_start,
        end_time=block_end,
    )
    db_session.add(evt)
    db_session.commit()

    created = generate_study_times(db_session, sample_term.id)
    assert len(created) > 0
    for st in created:
        assert not (st.start_time < block_end and st.end_time > block_start)
