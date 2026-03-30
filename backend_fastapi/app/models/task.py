import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TaskStatus(str, enum.Enum):
    PUBLISHED = "PUBLISHED"
    ACCEPTED = "ACCEPTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    poster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_drafts.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status"), default=TaskStatus.PUBLISHED, nullable=False
    )
    category: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    subcategory: Mapped[str | None] = mapped_column(String(120), nullable=True)
    task_schema: Mapped[dict] = mapped_column(JSONB, nullable=False)
    suggested_price_min: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    suggested_price_max: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    poster = relationship("User", back_populates="tasks")
    draft = relationship("TaskDraft", back_populates="published_task")
    acceptances = relationship("TaskAcceptance", back_populates="task", cascade="all, delete-orphan")
    evidence_uploads = relationship("EvidenceUpload", back_populates="task", cascade="all, delete-orphan")
    verification_results = relationship("VerificationResult", back_populates="task", cascade="all, delete-orphan")
    escrow_payment = relationship("EscrowPayment", back_populates="task", uselist=False, cascade="all, delete-orphan")
    disputes = relationship("Dispute", back_populates="task", cascade="all, delete-orphan")


class AcceptanceStatus(str, enum.Enum):
    ACCEPTED = "ACCEPTED"
    CANCELLED = "CANCELLED"


class TaskAcceptance(Base):
    __tablename__ = "task_acceptances"
    __table_args__ = (UniqueConstraint("task_id", "tasker_id", name="uq_task_acceptances_task_tasker"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tasker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[AcceptanceStatus] = mapped_column(
        Enum(AcceptanceStatus, name="acceptance_status"), default=AcceptanceStatus.ACCEPTED, nullable=False
    )
    acknowledgement: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    task = relationship("Task", back_populates="acceptances")
    tasker = relationship("User", back_populates="task_acceptances")


class VerificationStatus(str, enum.Enum):
    PASS = "PASS"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    FAIL = "FAIL"


class EvidenceUpload(Base):
    __tablename__ = "evidence_uploads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    before_image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    after_image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    evidence_video_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    evidence_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    task = relationship("Task", back_populates="evidence_uploads")


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="verification_status"), nullable=False
    )
    confidence: Mapped[float] = mapped_column(nullable=False)
    explanation: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    task = relationship("Task", back_populates="verification_results")


class EscrowStatus(str, enum.Enum):
    HELD = "HELD"
    RELEASE_ELIGIBLE = "RELEASE_ELIGIBLE"
    RELEASED = "RELEASED"
    DISPUTE_OPENED = "DISPUTE_OPENED"
    CANCELLED = "CANCELLED"


class EscrowEventType(str, enum.Enum):
    HELD = "HELD"
    VERIFICATION_PASSED = "VERIFICATION_PASSED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    RELEASE_ELIGIBLE = "RELEASE_ELIGIBLE"
    RELEASED = "RELEASED"
    DISPUTE_OPENED = "DISPUTE_OPENED"
    CANCELLED = "CANCELLED"


class EscrowPayment(Base):
    __tablename__ = "escrow_payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    razorpay_order_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    status: Mapped[EscrowStatus] = mapped_column(
        Enum(EscrowStatus, name="escrow_status"), default=EscrowStatus.HELD, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    task = relationship("Task", back_populates="escrow_payment")
    events = relationship("EscrowEvent", back_populates="escrow_payment", cascade="all, delete-orphan")


class EscrowEvent(Base):
    __tablename__ = "escrow_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    escrow_payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("escrow_payments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[EscrowEventType] = mapped_column(Enum(EscrowEventType, name="escrow_event_type"), nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    escrow_payment = relationship("EscrowPayment", back_populates="events")


class DisputeStatus(str, enum.Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


class Dispute(Base):
    __tablename__ = "disputes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opened_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[DisputeStatus] = mapped_column(
        Enum(DisputeStatus, name="dispute_status"), default=DisputeStatus.OPEN, nullable=False
    )
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    task = relationship("Task", back_populates="disputes")
    events = relationship("DisputeEvent", back_populates="dispute", cascade="all, delete-orphan")


class DisputeEvent(Base):
    __tablename__ = "dispute_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dispute_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("disputes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    dispute = relationship("Dispute", back_populates="events")

