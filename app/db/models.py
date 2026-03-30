from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.services.utils import utc_now


class RequestRecord(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(50), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    prompt_preview: Mapped[str] = mapped_column(String(160))
    evidence_strength: Mapped[float] = mapped_column(Float)
    sensitivity: Mapped[str] = mapped_column(String(30), index=True)
    requested_action: Mapped[str | None] = mapped_column(String(100), nullable=True)
    outcome: Mapped[str] = mapped_column(String(30), index=True)
    reason_summary: Mapped[str] = mapped_column(Text)
    suggested_response: Mapped[str] = mapped_column(Text)
    risk_score: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    audit_events: Mapped[list[AuditEvent]] = relationship(back_populates="request", cascade="all, delete-orphan")
    review_item: Mapped[ReviewItem | None] = relationship(back_populates="request", uselist=False, cascade="all, delete-orphan")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(50))
    detail: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    request: Mapped[RequestRecord] = relationship(back_populates="audit_events")


class ReviewItem(Base):
    __tablename__ = "review_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    reviewer: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    request: Mapped[RequestRecord] = relationship(back_populates="review_item")
