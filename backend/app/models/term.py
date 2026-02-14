# Term ORM model for semester/quarter management.
# Stores academic terms with start/end dates for organizing courses.

from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


class Term(Base):
    """
    Represents an academic term/semester/quarter.
    Each term has a name (e.g., "Winter 2025"), start and end dates,
    and an is_active flag to mark the current term.
    """

    __tablename__ = "Terms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("Users.id"), nullable=False)
    term_name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[Date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="terms")
    courses = relationship(
        "Course", back_populates="term", cascade="all, delete-orphan"
    )
