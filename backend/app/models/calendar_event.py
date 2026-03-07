from datetime import datetime, date
from sqlalchemy import Integer, String, Text, Boolean, DateTime, Date, ForeignKey, TIMESTAMP, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class CalendarEvent(Base):
    __tablename__ = "CalendarEvents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("Users.id"), nullable=False)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("CalendarSources.id"), nullable=False)
    external_uid: Mapped[str] = mapped_column(String(500), nullable=False)
    recurrence_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    instance_key: Mapped[str] = mapped_column(String(255), nullable=False, default="base")

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)

    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    original_timezone: Mapped[str | None] = mapped_column(String(100), nullable=True)

    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    event_kind: Mapped[str] = mapped_column(String(20), nullable=False, default="timed")
    event_category: Mapped[str] = mapped_column(String(30), nullable=False, default="other")

    sync_status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    recurrence_rule: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_recurring_instance: Mapped[bool] = mapped_column(Boolean, default=False)

    original_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    is_locally_modified: Mapped[bool] = mapped_column(Boolean, default=False)
    local_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    local_start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    local_end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    local_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    local_modified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    source = relationship("CalendarSource", back_populates="events")
