"""
Village Knowledge Model (with pgvector)
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Text, DateTime, Integer, ForeignKey, JSON, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
# pgvector disabled until we have a postgres with the extension
# from pgvector.sqlalchemy import Vector

from app.database import Base


class VillageKnowledge(Base):
    """
    Village Protocol knowledge storage.

    Supports three realms:
    - private: Personal knowledge (only visible to owner)
    - village: Shared knowledge (visible to all agents)
    - bridge: Cross-agent connections
    """

    __tablename__ = "village_knowledge"

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

    content: Mapped[str] = mapped_column(Text)

    # Vector embedding - stored as JSON array until pgvector is available
    # embedding = mapped_column(Vector(1536))
    embedding: Mapped[Optional[list]] = mapped_column(JSON)  # Store as JSON array for now

    # Categorization
    category: Mapped[Optional[str]] = mapped_column(String(50))  # 'preferences', 'technical', 'project', 'general'
    visibility: Mapped[str] = mapped_column(String(20), default="private")  # 'private', 'village', 'bridge'
    agent_id: Mapped[Optional[str]] = mapped_column(String(50), index=True)  # 'AZOTH', 'ELYSIAN', etc.

    # Threading (for dialogue)
    conversation_thread: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    responding_to: Mapped[Optional[dict]] = mapped_column(JSON)  # List of message IDs
    related_agents: Mapped[Optional[dict]] = mapped_column(JSON)  # List of agent IDs

    # Metadata
    tags: Mapped[list] = mapped_column(ARRAY(String), default=list)
    knowledge_type: Mapped[Optional[str]] = mapped_column(String(50))  # 'fact', 'dialogue', 'agent_profile', etc.
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)  # renamed from 'metadata' (reserved by SQLAlchemy)

    # Access tracking (from Memory Enhancement)
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )

    # Relationships
    user = relationship("User", back_populates="knowledge")

    def __repr__(self):
        return f"<VillageKnowledge {self.id} - {self.visibility}/{self.agent_id}>"
