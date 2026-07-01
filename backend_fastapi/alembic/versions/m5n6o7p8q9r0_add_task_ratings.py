"""Revision ID: m5n6o7p8q9r0
Revises: l4m5n6o7p8q9
Create Date: 2026-06-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "m5n6o7p8q9r0"
down_revision: Union[str, Sequence[str], None] = "l4m5n6o7p8q9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "task_ratings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("rater_id", sa.UUID(), nullable=False),
        sa.Column("ratee_id", sa.UUID(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("score >= 1 AND score <= 5", name="ck_task_ratings_score_range"),
        sa.ForeignKeyConstraint(["ratee_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rater_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "rater_id", name="uq_task_ratings_task_rater"),
    )
    op.create_index("ix_task_ratings_task_id", "task_ratings", ["task_id"])
    op.create_index("ix_task_ratings_rater_id", "task_ratings", ["rater_id"])
    op.create_index("ix_task_ratings_ratee_id", "task_ratings", ["ratee_id"])


def downgrade() -> None:
    op.drop_index("ix_task_ratings_ratee_id", table_name="task_ratings")
    op.drop_index("ix_task_ratings_rater_id", table_name="task_ratings")
    op.drop_index("ix_task_ratings_task_id", table_name="task_ratings")
    op.drop_table("task_ratings")
