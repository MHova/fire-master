"""Property model — a real-estate holding tracked for per-property P&L.

Mirrors the per-property knowledge previously held in config/properties.json.
Money is stored as BIGINT cents to match Transaction.amount / CashflowEvent.amount_cents.
Equity (value - loan_balance) is computed, never stored.
"""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    # Stable join key (e.g. "coastal_condo", "river_house"). Survives renames; used by the seed importer.
    key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    color: Mapped[str | None] = mapped_column(String, nullable=True)

    value_cents: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    loan_balance_cents: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    purchase_price_cents: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    potential_monthly_rental_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    potential_monthly_rental_full_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    # Free-form notes list (carried over from config) and a catch-all for capital_gains etc.
    notes: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    extra_data: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    @property
    def equity_cents(self) -> int:
        return self.value_cents - self.loan_balance_cents
