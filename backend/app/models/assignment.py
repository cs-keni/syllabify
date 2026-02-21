from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


class Assignment(Base):
    __tablename__ = "Assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    assignment_name: Mapped[str] = mapped_column(String(255), nullable=False)

    work_load: Mapped[int] = mapped_column(Integer, nullable=False)

    notes: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    course_id: Mapped[int] = mapped_column(ForeignKey("Courses.id"), nullable=False)

    course = relationship("Course", back_populates="assignments")
