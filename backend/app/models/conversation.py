import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    messages: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    context_snapshot: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    model: Mapped[str] = mapped_column(String, nullable=False, default="claude-opus-4-6")
    total_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
