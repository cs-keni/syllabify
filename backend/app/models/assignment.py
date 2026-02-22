# Assignment ORM model.
# TODO: SQLAlchemy model (3NF). id, course_id, title, due_date, est_minutes,
#       type (exam/homework), etc. Relationships to course.
#
# DISCLAIMER: Project structure may change. Fields/relationships may be added or
# modified. This describes the general idea.

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


class Assignment(Base):
    __tablename__ = "Assignments"

    id: Mapped[int] = mapped_column(
        primary_key = True
    )

    assignment_name: Mapped[str] = mapped_column(
        String(255),
        nullable = False
    )

#    Quantized as: work_load * 15 = number of minutes to complete the assignment
    work_load: Mapped[int] = mapped_column(
        Integer,
        nullable = False
    )

    notes: Mapped[str | None] = mapped_column(
        String(2048),
        nullable = True
    )

    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone = True),
        nullable = False
    )

    due_date: Mapped[datetime] = mapped_column(
        DateTime(timezone = True),
        nullable = False
    )

# #    assignments are now associated with a course instead of a schedule
# #    commenting schedule_id logic here in case it is needed in the future
#    schedule_id: Mapped[int] = mapped_column(
#        ForeignKey("Schedules.id"),
#        nullable = False
#    )

    course_id: Mapped[int] = mapped_column(
        ForeignKey("Courses.id"),
        nullable = False
    )

#    schedule = relationship(
#        "Schedule",
#        back_populates = "assignments"
#    )

    course = relationship(
        "Course",
        back_populates = "assignments"
    )
