"""Revision ID: k3l4m5n6o7p8
Revises: j2k3l4m5n6o7
Create Date: 2026-06-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "k3l4m5n6o7p8"
down_revision: Union[str, Sequence[str], None] = "j2k3l4m5n6o7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

feedback_category = sa.Enum(
    "bug",
    "feature",
    "support",
    "other",
    name="beta_feedback_category",
)


def upgrade() -> None:
    # Let create_table create the enum once (explicit .create() duplicates it in the same txn).
    op.create_table(
        "beta_feedback",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("category", feedback_category, nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("page_path", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_beta_feedback_user_id", "beta_feedback", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_beta_feedback_user_id", table_name="beta_feedback")
    op.drop_table("beta_feedback")
    feedback_category.drop(op.get_bind(), checkfirst=True)
