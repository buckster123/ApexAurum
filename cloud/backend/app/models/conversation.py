"""
Conversation and Message Models
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Text, DateTime, Boolean, Integer, ForeignKey, JSON, ARRAY, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Conversation(Base):
    """Conversation (chat session) model."""

    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(500))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    tags: Mapped[list] = mapped_column(ARRAY(String), default=list)

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")

    def __repr__(self):
        return f"<Conversation {self.id} - {self.title}>"


class Message(Base):
    """Individual message within a conversation."""

    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    conversation_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True
    )

    role: Mapped[str] = mapped_column(String(20))  # 'user', 'assistant', 'system'
    content: Mapped[str] = mapped_column(Text)

    # Tool usage
    tool_calls: Mapped[Optional[dict]] = mapped_column(JSON)
    tool_results: Mapped[Optional[dict]] = mapped_column(JSON)

    # Usage tracking
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer)
    cost_usd: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message {self.id} - {self.role}>"
