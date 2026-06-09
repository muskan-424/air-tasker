import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bio: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    default_location_pin: Mapped[str | None] = mapped_column(String(6), nullable=True)
    skills: Mapped[list[str]] = mapped_column(ARRAY(String(64)), nullable=False, default=list)
    service_pin_codes: Mapped[list[str]] = mapped_column(ARRAY(String(6)), nullable=False, default=list)
    preferred_languages: Mapped[list[str]] = mapped_column(ARRAY(String(10)), nullable=False, default=lambda: ["en"])
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User", back_populates="profile")
