import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TaskDraftStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"


class TaskDraft(Base):
    __tablename__ = "task_drafts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    poster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[TaskDraftStatus] = mapped_column(
        Enum(TaskDraftStatus, name="task_draft_status"), default=TaskDraftStatus.DRAFT, nullable=False
    )
    ai_schema: Mapped[dict] = mapped_column(JSONB, nullable=False)
    ai_explain: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    user_edits: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    poster = relationship("User", back_populates="task_drafts")
    published_task = relationship("Task", back_populates="draft", uselist=False)

