"""add task offers, task cancellations, and escrow fee breakdown

Revision ID: o7p8q9r0s1t2
Revises: n6o7p8q9r0s1
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "o7p8q9r0s1t2"
down_revision: Union[str, Sequence[str], None] = "n6o7p8q9r0s1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

offer_status = sa.Enum("PENDING", "ACCEPTED", "DECLINED", "WITHDRAWN", name="offer_status")
cancelled_by = sa.Enum("POSTER", "TASKER", "ADMIN", name="cancelled_by")


def upgrade() -> None:
    # create_table creates each enum once; do not call .create() explicitly.
    op.create_table(
        "task_offers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("tasker_id", sa.UUID(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(length=10), server_default="INR", nullable=False),
        sa.Column("message", sa.String(length=1000), nullable=True),
        sa.Column("status", offer_status, server_default="PENDING", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tasker_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "tasker_id", name="uq_task_offers_task_tasker"),
    )
    op.create_index("ix_task_offers_task_id", "task_offers", ["task_id"])
    op.create_index("ix_task_offers_tasker_id", "task_offers", ["tasker_id"])

    op.create_table(
        "task_cancellations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("cancelled_by_id", sa.UUID(), nullable=False),
        sa.Column("cancelled_by", cancelled_by, nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=True),
        sa.Column("previous_status", sa.String(length=32), nullable=False),
        sa.Column("fee_amount", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("refund_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("refund_status", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cancelled_by_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_cancellations_task_id", "task_cancellations", ["task_id"], unique=True)
    op.create_index("ix_task_cancellations_cancelled_by_id", "task_cancellations", ["cancelled_by_id"])

    op.add_column("escrow_payments", sa.Column("task_price", sa.Numeric(10, 2), nullable=True))
    op.add_column("escrow_payments", sa.Column("poster_fee", sa.Numeric(10, 2), nullable=True))
    op.add_column("escrow_payments", sa.Column("tasker_fee", sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("escrow_payments", "tasker_fee")
    op.drop_column("escrow_payments", "poster_fee")
    op.drop_column("escrow_payments", "task_price")
    op.drop_index("ix_task_cancellations_cancelled_by_id", table_name="task_cancellations")
    op.drop_index("ix_task_cancellations_task_id", table_name="task_cancellations")
    op.drop_table("task_cancellations")
    op.drop_index("ix_task_offers_tasker_id", table_name="task_offers")
    op.drop_index("ix_task_offers_task_id", table_name="task_offers")
    op.drop_table("task_offers")
    cancelled_by.drop(op.get_bind(), checkfirst=True)
    offer_status.drop(op.get_bind(), checkfirst=True)
