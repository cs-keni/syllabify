# Assignment ORM model.
# TODO: SQLAlchemy model (3NF). id, course_id, title, due_date, est_minutes,
#       type (exam/homework), etc. Relationships to course.
#
# DISCLAIMER: Project structure may change. Fields/relationships may be added or
# modified. This describes the general idea.

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


class StudyTime(Base):
    __tablename__ = "StudyTimes"

    id: Mapped[int] = mapped_column(
        primary_key = True
    )

    notes: Mapped[str | None] = mapped_column(
        String(2048),
        nullable = True
    )

    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone = True),
        nullable = False
    )

    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone = True),
        nullable = False
    )

    schedule_id: Mapped[int] = mapped_column(
        ForeignKey("Schedules.id"),
        nullable = False
    )

    schedule = relationship(
        "Schedule",
        back_populates = "study_times"
        )
