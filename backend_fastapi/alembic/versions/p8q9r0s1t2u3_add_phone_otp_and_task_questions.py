"""generalize otp_challenges to email+phone, add task_questions

Revision ID: p8q9r0s1t2u3
Revises: o7p8q9r0s1t2
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "p8q9r0s1t2u3"
down_revision: Union[str, Sequence[str], None] = "o7p8q9r0s1t2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("otp_challenges", "email", new_column_name="target")
    op.add_column("otp_challenges", sa.Column("channel", sa.String(length=10), server_default="EMAIL", nullable=False))
    op.drop_index(op.f("ix_otp_challenges_email"), table_name="otp_challenges")
    op.create_index(op.f("ix_otp_challenges_target"), "otp_challenges", ["target"], unique=False)

    op.create_table(
        "task_questions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("asker_id", sa.UUID(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asker_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_questions_task_id", "task_questions", ["task_id"])
    op.create_index("ix_task_questions_asker_id", "task_questions", ["asker_id"])


def downgrade() -> None:
    op.drop_index("ix_task_questions_asker_id", table_name="task_questions")
    op.drop_index("ix_task_questions_task_id", table_name="task_questions")
    op.drop_table("task_questions")

    op.drop_index(op.f("ix_otp_challenges_target"), table_name="otp_challenges")
    op.drop_column("otp_challenges", "channel")
    op.alter_column("otp_challenges", "target", new_column_name="email")
    op.create_index(op.f("ix_otp_challenges_email"), "otp_challenges", ["email"], unique=False)
