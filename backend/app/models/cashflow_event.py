"""Cash flow events — one-time and recurring future income/expense events for runway projection."""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Float, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CashflowEvent(Base):
    __tablename__ = "cashflow_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # "income" or "expense"
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)

    # Recurrence
    is_recurring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recurrence: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # "monthly", "quarterly", "annual"
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Certainty
    probability: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # Status
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="planned"
    )  # "planned", "confirmed", "completed", "cancelled"

    # Context
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    linked_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
