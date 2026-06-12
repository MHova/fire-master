"""Request/response schemas for the advisor API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: str | None = None
    page_context: str | None = None
    model: str | None = None


class ConversationSummary(BaseModel):
    id: UUID
    title: str | None
    model: str
    message_count: int
    total_input_tokens: int
    total_output_tokens: int
    created_at: datetime
    updated_at: datetime


class ConversationDetail(BaseModel):
    id: UUID
    title: str | None
    model: str
    messages: list
    context_snapshot: dict
    total_input_tokens: int
    total_output_tokens: int
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]
