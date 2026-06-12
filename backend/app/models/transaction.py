import uuid
from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Enum, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import DataSource


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_account_date", "account_id", "date"),
        Index("ix_transactions_category_date", "category", "date"),
        Index("ix_transactions_property_id", "property_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    external_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    subcategory: Mapped[str | None] = mapped_column(String, nullable=True)
    merchant: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    hide_from_reports: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[DataSource] = mapped_column(Enum(DataSource, name="data_source", create_type=False), nullable=False)

    # Property P&L classification. NULL property_id = not a property transaction, so it
    # stays in the Spending Tracker. These columns are NOT written by the Monarch upsert,
    # so auto-classification and manual overrides survive re-sync (same pattern as account
    # enrichment). property_source: 'rule' = auto-classified, 'manual' = user override
    # (never touched by reclassify), NULL = unclassified.
    property_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="SET NULL"), nullable=True
    )
    property_category: Mapped[str | None] = mapped_column(String, nullable=True)
    property_source: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
