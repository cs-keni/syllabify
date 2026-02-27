from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


class Course(Base):
    __tablename__ = "Courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    course_name: Mapped[str] = mapped_column(String(255), nullable=False)

    term_id: Mapped[int] = mapped_column(ForeignKey("Terms.id"), nullable=False)

    study_hours_per_week: Mapped[int | None] = mapped_column(Integer, nullable=True)

    term = relationship("Term", back_populates="courses")
    assignments = relationship(
        "Assignment", back_populates="course", cascade="all, delete-orphan"
    )
    meetings = relationship(
        "Meeting", back_populates="course", cascade="all, delete-orphan"
    )
