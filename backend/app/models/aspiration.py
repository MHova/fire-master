import uuid
from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Date, DateTime, Enum, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import AspirationPriority, AspirationStatus


class Aspiration(Base):
    __tablename__ = "aspirations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_cost: Mapped[int] = mapped_column(BigInteger, nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    priority: Mapped[AspirationPriority] = mapped_column(
        Enum(AspirationPriority, name="aspiration_priority"), nullable=False
    )
    category: Mapped[str | None] = mapped_column(String, nullable=True)

    # Link to physical asset being replaced
    linked_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("physical_assets.id", ondelete="SET NULL"), nullable=True
    )

    funding_source: Mapped[str | None] = mapped_column(String, nullable=True)
    financing_terms: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ongoing_cost_delta: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    fire_impact_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[AspirationStatus] = mapped_column(
        Enum(AspirationStatus, name="aspiration_status"),
        nullable=False,
        default=AspirationStatus.PLANNED,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
