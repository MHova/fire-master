"""PropertyRule model — merchant-match rules that classify transactions to a property.

Normalizes config/properties.json's merchant_rules, the per-property *_merchants lists,
rental_income_merchants, and global exclusions into one ordered table. The classifier
(app/engines/property_pnl.py) walks active rules by ascending `priority`.

rule_kind:
  - 'exclusion'  property_id is NULL; a merchant match means "never a property txn"
  - 'income'     matches positive (income) transactions -> Rental Income
  - 'expense'    matches negative (expense) transactions -> expense_category

require_tx_category gates a rule on the transaction's raw category (e.g. "Check #" only
counts as floating-home moorage when the transaction category is "Rent").
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PropertyRule(Base):
    __tablename__ = "property_rules"
    __table_args__ = (
        Index("ix_property_rules_priority", "priority"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    # NULL property_id is valid only for rule_kind='exclusion' (global exclusions).
    property_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=True
    )
    match_type: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'merchant_substring'"))
    pattern: Mapped[str] = mapped_column(String, nullable=False)
    expense_category: Mapped[str | None] = mapped_column(String, nullable=True)
    require_tx_category: Mapped[str | None] = mapped_column(String, nullable=True)
    rule_kind: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'expense'"))
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("100"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
