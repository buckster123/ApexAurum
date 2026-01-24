"""
Memory (Key-Value) Model
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Memory(Base):
    """
    Simple key-value memory storage.

    Persists across conversations.
    """

    __tablename__ = "memory"

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

    key: Mapped[str] = mapped_column(String(255))
    value: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    user = relationship("User", back_populates="memories")

    # Unique constraint on user_id + key
    __table_args__ = (
        UniqueConstraint('user_id', 'key', name='uq_memory_user_key'),
    )

    def __repr__(self):
        return f"<Memory {self.key}>"
