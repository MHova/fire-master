import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import AssetCategory


class PhysicalAsset(Base):
    __tablename__ = "physical_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    asset_category: Mapped[AssetCategory] = mapped_column(
        Enum(AssetCategory, name="asset_category"), nullable=False
    )
    subcategory: Mapped[str | None] = mapped_column(String, nullable=True)
    purchase_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    purchase_price: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    current_value: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    valuation_method: Mapped[str | None] = mapped_column(String, nullable=True)
    last_valued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Link to Monarch account (mortgage/loan) for equity calculation
    linked_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )

    external_ref: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    cost_tracking_categories: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    photos: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Enrichment (same pattern as accounts)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    fire_role: Mapped[str | None] = mapped_column(String, nullable=True)
    custom_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
