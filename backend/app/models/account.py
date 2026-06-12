import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, Float, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import AccountType, DataSource


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    external_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    account_type: Mapped[AccountType] = mapped_column(Enum(AccountType, name="account_type"), nullable=False)
    institution: Mapped[str | None] = mapped_column(String, nullable=True)
    current_balance: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    is_asset: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    include_in_net_worth: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source: Mapped[DataSource] = mapped_column(Enum(DataSource, name="data_source"), nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    extra_data: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))

    # Enrichment fields (user-managed, NOT overwritten by Monarch sync)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    fire_role: Mapped[str | None] = mapped_column(String, nullable=True)
    target_balance: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    target_allocation_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    strategy: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
