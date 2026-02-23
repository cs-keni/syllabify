from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


class UserSecurityAnswer(Base):
    __tablename__ = "UserSecurityAnswers"

    id: Mapped[int] = mapped_column(
        primary_key = True
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        nullable = False
    )

    question_text: Mapped[str] = mapped_column(
        String(500),
        nullable = False
    )

    answer_hash: Mapped[str] = mapped_column(
        String(255),
        nullable = False
    )

    user = relationship(
        "User",
        back_populates = "user_security_answers"
    )
