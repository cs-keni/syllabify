from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


class Meeting(Base):
    """
    Recurring course meetings (lecture, lab, etc.) for scheduling engine.
    Uses day_of_week + start_time_str + end_time_str (e.g. "WE", "16:00", "17:20").
    start_time/end_time kept for one-off meetings (legacy).
    """
    __tablename__ = "Meetings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    course_id: Mapped[int] = mapped_column(ForeignKey("Courses.id"), nullable=False)

    # Recurring format (parser output): MO, TU, WE, etc.
    day_of_week: Mapped[str | None] = mapped_column(String(2), nullable=True)

    # Times as "HH:MM" (e.g. "16:00", "17:20")
    start_time_str: Mapped[str | None] = mapped_column(String(5), nullable=True)
    end_time_str: Mapped[str | None] = mapped_column(String(5), nullable=True)

    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meeting_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # One-off meetings (legacy)
    start_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    course = relationship("Course", back_populates="meetings")
