# User ORM model.
# TODO: SQLAlchemy model (3NF). id, email, password_hash, created_at, etc.
#       Relationships to course, schedule. Use db.base, db.session.
#
# DISCLAIMER: Project structure may change. Fields/relationships may be added or
# modified. This describes the general idea.

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


class User(Base):
    __tablename__ = "Users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key = True,
        autoincrement = True
    )

    username: Mapped[str] = mapped_column(
        String(255),
        nullable = False,
        unique = True
    )

    schedules = relationship(
        "Schedule",
        back_populates = "owner",
        cascade = "all, delete-orphan"
    )
