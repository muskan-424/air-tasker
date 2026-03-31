"""tasker Razorpay contact/fund account + escrow payout id

Revision ID: g4h5i6j7k8l9
Revises: f3a4b5c6d7e8
Create Date: 2026-03-30

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g4h5i6j7k8l9"
down_revision: Union[str, Sequence[str], None] = "f3a4b5c6d7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TYPE escrow_event_type ADD VALUE 'PAYOUT_INITIATED'"))
    op.add_column("users", sa.Column("razorpay_contact_id", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("razorpay_fund_account_id", sa.String(length=255), nullable=True))
    op.create_unique_constraint("uq_users_razorpay_contact_id", "users", ["razorpay_contact_id"])
    op.create_unique_constraint("uq_users_razorpay_fund_account_id", "users", ["razorpay_fund_account_id"])
    op.add_column(
        "escrow_payments",
        sa.Column("razorpay_payout_id", sa.String(length=255), nullable=True),
    )
    op.create_unique_constraint("uq_escrow_payments_razorpay_payout_id", "escrow_payments", ["razorpay_payout_id"])


def downgrade() -> None:
    op.drop_constraint("uq_escrow_payments_razorpay_payout_id", "escrow_payments", type_="unique")
    op.drop_column("escrow_payments", "razorpay_payout_id")
    op.drop_constraint("uq_users_razorpay_fund_account_id", "users", type_="unique")
    op.drop_constraint("uq_users_razorpay_contact_id", "users", type_="unique")
    op.drop_column("users", "razorpay_fund_account_id")
    op.drop_column("users", "razorpay_contact_id")
