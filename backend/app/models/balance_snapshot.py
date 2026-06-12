import uuid
from datetime import date

from sqlalchemy import BigInteger, Date, Enum, ForeignKey, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import DataSource


class BalanceSnapshot(Base):
    __tablename__ = "balance_snapshots"
    __table_args__ = (
        UniqueConstraint("account_id", "date", name="uq_balance_snapshot_account_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    balance: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source: Mapped[DataSource] = mapped_column(Enum(DataSource, name="data_source", create_type=False), nullable=False)
