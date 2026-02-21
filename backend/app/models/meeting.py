from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


class Meeting(Base):
    __tablename__ = "Meetings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    course_id: Mapped[int] = mapped_column(ForeignKey("Courses.id"), nullable=False)

    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    course = relationship("Course", back_populates="meetings")
