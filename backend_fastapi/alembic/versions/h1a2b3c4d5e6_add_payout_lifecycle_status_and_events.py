"""escrow razorpay_payout_status + payout lifecycle escrow events

Revision ID: h1a2b3c4d5e6
Revises: g4h5i6j7k8l9
Create Date: 2026-03-31

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "h1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "g4h5i6j7k8l9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TYPE escrow_event_type ADD VALUE 'PAYOUT_PROCESSED'"))
    op.execute(sa.text("ALTER TYPE escrow_event_type ADD VALUE 'PAYOUT_FAILED'"))
    op.execute(sa.text("ALTER TYPE escrow_event_type ADD VALUE 'PAYOUT_REVERSED'"))
    op.execute(sa.text("ALTER TYPE escrow_event_type ADD VALUE 'PAYOUT_UPDATED'"))
    op.add_column(
        "escrow_payments",
        sa.Column("razorpay_payout_status", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("escrow_payments", "razorpay_payout_status")
    # PostgreSQL cannot drop enum values safely; leave escrow_event_type as-is.
