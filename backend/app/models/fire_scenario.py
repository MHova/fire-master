import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FireScenario(Base):
    """Named scenario with assumption overrides for FIRE projections.

    Each scenario stores only the fields that differ from the base fire_config.
    The engine merges overrides into a temporary config object at projection time.
    Exactly one scenario can be active at a time (or none = use base config).
    """

    __tablename__ = "fire_scenarios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Overrides for fire_config fields + custom_assumptions subkeys.
    # Structure: top-level keys override fire_config columns,
    # "custom_assumptions" key deep-merges with base custom_assumptions.
    overrides: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
