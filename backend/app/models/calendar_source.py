from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CalendarSource(Base):
    __tablename__ = "CalendarSources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("Users.id"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, default="google")
    source_label: Mapped[str] = mapped_column(String(100), nullable=False)
    feed_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    feed_url_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    feed_category: Mapped[str] = mapped_column(String(20), nullable=False, default="other")
    google_calendar_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#3B82F6")
    is_writable: Mapped[bool] = mapped_column(Boolean, default=False)
    source_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="import_only")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    events = relationship("CalendarEvent", back_populates="source", cascade="all, delete-orphan")
