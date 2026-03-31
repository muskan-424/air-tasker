"""add razorpay_refund_id and REFUND_ISSUED escrow event

Revision ID: f3a4b5c6d7e8
Revises: e1f2a3b4c5d6
Create Date: 2026-03-30

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f3a4b5c6d7e8"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TYPE escrow_event_type ADD VALUE 'REFUND_ISSUED'"))
    op.add_column(
        "escrow_payments",
        sa.Column("razorpay_refund_id", sa.String(length=255), nullable=True),
    )
    op.create_unique_constraint("uq_escrow_payments_razorpay_refund_id", "escrow_payments", ["razorpay_refund_id"])


def downgrade() -> None:
    op.drop_constraint("uq_escrow_payments_razorpay_refund_id", "escrow_payments", type_="unique")
    op.drop_column("escrow_payments", "razorpay_refund_id")
    # PostgreSQL cannot drop enum values safely; leave escrow_event_type as-is.
