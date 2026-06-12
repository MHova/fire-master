import uuid
from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Date, DateTime, Enum, Float, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import GoalStatus, GoalType


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    goal_type: Mapped[GoalType] = mapped_column(
        Enum(GoalType, name="goal_type"), nullable=False
    )
    target_value: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    target_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Computed by engine, cached
    current_value: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    current_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    progress_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    status: Mapped[GoalStatus] = mapped_column(
        Enum(GoalStatus, name="goal_status"),
        nullable=False,
        default=GoalStatus.ACTIVE,
    )
    metric_query: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
