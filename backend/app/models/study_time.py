from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


class StudyTime(Base):
    __tablename__ = "StudyTimes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    notes: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    term_id: Mapped[int] = mapped_column(ForeignKey("Terms.id"), nullable=False)

    term = relationship("Term", back_populates="study_times")
