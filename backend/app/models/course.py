# Course ORM model.
# TODO: SQLAlchemy model (3NF). id, user_id, name, term, etc. Relationships
#       to user, assignment, schedule.
#
# DISCLAIMER: Project structure may change. Fields/relationships may be added or
# modified. This describes the general idea.

from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.base import Base

class Course(Base):
    __tablename__ = "Courses"

    id: Mapped[int] = mapped_column(
        primary_key = True
    )

    course_name: Mapped[str] = mapped_column(
        String(255),
        nullable = False
    )

    schedule_id: Mapped[int] = mapped_column(
        ForeignKey("Schedules.id"),
        nullable = False
    )

    schedule = relationship(
        "Schedule",
        back_populates = "courses"
    )

    meetings = relationship(
        "Meeting",
        back_populates = "course",
        cascade = "all, delete-orphan"
    )