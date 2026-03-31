import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserRole(str, enum.Enum):
    POSTER = "POSTER"
    TASKER = "TASKER"
    ADMIN = "ADMIN"
    REVIEWER = "REVIEWER"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    phone_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), default=UserRole.POSTER, nullable=False)
    razorpay_contact_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    razorpay_fund_account_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    task_drafts = relationship("TaskDraft", back_populates="poster", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="poster", cascade="all, delete-orphan")
    task_acceptances = relationship("TaskAcceptance", back_populates="tasker", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    otp_challenges = relationship("OtpChallenge", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    notification_preferences = relationship(
        "NotificationPreference", back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    trusted_devices = relationship("UserTrustedDevice", back_populates="user", cascade="all, delete-orphan")
    kyc_profile = relationship("UserKycProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")

