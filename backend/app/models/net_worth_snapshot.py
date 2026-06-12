import uuid
from datetime import date

from sqlalchemy import BigInteger, Date, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NetWorthSnapshot(Base):
    __tablename__ = "net_worth_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    total_assets: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_liabilities: Mapped[int] = mapped_column(BigInteger, nullable=False)
    net_worth: Mapped[int] = mapped_column(BigInteger, nullable=False)
    breakdown: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
