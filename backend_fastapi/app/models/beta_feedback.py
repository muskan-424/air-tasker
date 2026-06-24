import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BetaFeedbackCategory(str, enum.Enum):
    BUG = "bug"
    FEATURE = "feature"
    SUPPORT = "support"
    OTHER = "other"


class BetaFeedback(Base):
    __tablename__ = "beta_feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    category: Mapped[BetaFeedbackCategory] = mapped_column(
        Enum(BetaFeedbackCategory, name="beta_feedback_category"),
        nullable=False,
        default=BetaFeedbackCategory.OTHER,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    page_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
