"""
Music Task Model
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Text, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class MusicTask(Base):
    """Music generation task (Suno AI integration)."""

    __tablename__ = "music_tasks"

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

    # Generation parameters
    prompt: Mapped[str] = mapped_column(Text)
    style: Mapped[Optional[str]] = mapped_column(String(255))
    title: Mapped[Optional[str]] = mapped_column(String(255))

    # Status
    status: Mapped[str] = mapped_column(String(20), default="pending")  # 'pending', 'processing', 'complete', 'failed'
    suno_task_id: Mapped[Optional[str]] = mapped_column(String(100))

    # Result
    file_path: Mapped[Optional[str]] = mapped_column(String(500))  # S3 key
    error: Mapped[Optional[str]] = mapped_column(Text)

    # Curation
    favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    play_count: Mapped[int] = mapped_column(Integer, default=0)

    # Attribution
    agent_id: Mapped[Optional[str]] = mapped_column(String(50))  # Which agent created it

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", back_populates="music_tasks")

    def __repr__(self):
        return f"<MusicTask {self.id} - {self.status}>"
