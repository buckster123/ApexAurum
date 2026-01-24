"""
Agent Model
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Agent(Base):
    """Background agent task model."""

    __tablename__ = "agents"

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

    agent_type: Mapped[str] = mapped_column(String(50))  # 'general', 'researcher', 'coder', etc.
    task: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # 'pending', 'running', 'complete', 'failed'

    result: Mapped[Optional[str]] = mapped_column(Text)
    error: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", back_populates="agents")

    def __repr__(self):
        return f"<Agent {self.id} - {self.agent_type} ({self.status})>"
