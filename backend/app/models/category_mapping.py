"""Category mapping model — normalizes raw Monarch/Mint categories into a two-level hierarchy."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CategoryMapping(Base):
    __tablename__ = "category_mappings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    raw_category: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    normalized_category: Mapped[str] = mapped_column(String, nullable=False)
    parent_category: Mapped[str] = mapped_column(String, nullable=False)
    is_discretionary: Mapped[bool] = mapped_column(Boolean, default=True)
    is_income: Mapped[bool] = mapped_column(Boolean, default=False)
    is_transfer: Mapped[bool] = mapped_column(Boolean, default=False)
    monarch_category_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
