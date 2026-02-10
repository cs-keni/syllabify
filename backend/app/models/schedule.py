# Schedule ORM model.
# TODO: SQLAlchemy model (3NF). id, user_id, name, time_blocks (JSON or
#       related table), status (draft/approved). Relationships to user, course.
#
# DISCLAIMER: Project structure may change. Fields/relationships may be added or
# modified. This describes the general idea.

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


class Schedule(Base):
    __tablename__ = "Schedules"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key = True,
        autoincrement = True
    )

    sched_name: Mapped[str] = mapped_column(
        String(255),
        nullable = False
    )

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("Users.id"),
        nullable = False
    )

    owner = relationship(
        "User",
        back_populates = "schedules"
    )

    assignments = relationship(
        "Assignment",
        back_populates = "schedule",
        cascade = "all, delete-orphan"
    )
