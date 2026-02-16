# Assignment ORM model.
# TODO: SQLAlchemy model (3NF). id, course_id, title, due_date, est_minutes,
#       type (exam/homework), etc. Relationships to course.
#
# DISCLAIMER: Project structure may change. Fields/relationships may be added or
# modified. This describes the general idea.

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


class Assignment(Base):
    __tablename__ = "Assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    assignment_name: Mapped[str] = mapped_column(String(255), nullable=False)

    work_load: Mapped[int] = mapped_column(Integer, nullable=False)

    notes: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    term_id: Mapped[int] = mapped_column(ForeignKey("Terms.id"), nullable=False)
    term = relationship("Term", back_populates="assignments")
