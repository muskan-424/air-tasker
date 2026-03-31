"""add razorpay_payment_id and PAYMENT_CAPTURED escrow event

Revision ID: c8d9e0f1a2b3
Revises: b3a9c1d2e4f5
Create Date: 2026-03-30

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, Sequence[str], None] = "b3a9c1d2e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TYPE escrow_event_type ADD VALUE 'PAYMENT_CAPTURED'"))
    op.add_column(
        "escrow_payments",
        sa.Column("razorpay_payment_id", sa.String(length=255), nullable=True),
    )
    op.create_unique_constraint("uq_escrow_payments_razorpay_payment_id", "escrow_payments", ["razorpay_payment_id"])


def downgrade() -> None:
    op.drop_constraint("uq_escrow_payments_razorpay_payment_id", "escrow_payments", type_="unique")
    op.drop_column("escrow_payments", "razorpay_payment_id")
    # PostgreSQL cannot drop enum values safely; leave escrow_event_type as-is.
