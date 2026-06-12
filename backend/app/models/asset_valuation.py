import uuid
from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AssetValuation(Base):
    __tablename__ = "asset_valuations"
    __table_args__ = (
        UniqueConstraint("asset_id", "date", name="uq_asset_valuation_asset_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("physical_assets.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[str | None] = mapped_column(String, nullable=True)
