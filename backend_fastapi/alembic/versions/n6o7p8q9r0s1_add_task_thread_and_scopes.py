"""add task thread messages and task scopes

Revision ID: n6o7p8q9r0s1
Revises: m5n6o7p8q9r0
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "n6o7p8q9r0s1"
down_revision: Union[str, Sequence[str], None] = "m5n6o7p8q9r0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

task_scope_status = sa.Enum(
    "PROPOSED",
    "ACCEPTED",
    "REJECTED",
    name="task_scope_status",
)


def upgrade() -> None:
    # Let create_table create the enum once (explicit .create() duplicates it in the same txn).
    op.create_table(
        "task_scopes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("poster_id", sa.UUID(), nullable=False),
        sa.Column("tasker_id", sa.UUID(), nullable=False),
        sa.Column("proposed_by_id", sa.UUID(), nullable=False),
        sa.Column("agreed_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(length=10), server_default="INR", nullable=False),
        sa.Column("scope_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", task_scope_status, server_default="PROPOSED", nullable=False),
        sa.Column("note", sa.String(length=1000), nullable=True),
        sa.Column("proposed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("agreed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["poster_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proposed_by_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tasker_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id"),
    )
    op.create_index("ix_task_scopes_task_id", "task_scopes", ["task_id"])

    op.create_table(
        "task_thread_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("sender_id", sa.UUID(), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("translated_text", sa.Text(), nullable=True),
        sa.Column("source_lang", sa.String(length=10), server_default="auto", nullable=False),
        sa.Column("target_lang", sa.String(length=10), server_default="en", nullable=False),
        sa.Column("translation_provider", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_thread_messages_task_id", "task_thread_messages", ["task_id"])
    op.create_index("ix_task_thread_messages_sender_id", "task_thread_messages", ["sender_id"])


def downgrade() -> None:
    op.drop_index("ix_task_thread_messages_sender_id", table_name="task_thread_messages")
    op.drop_index("ix_task_thread_messages_task_id", table_name="task_thread_messages")
    op.drop_table("task_thread_messages")
    op.drop_index("ix_task_scopes_task_id", table_name="task_scopes")
    op.drop_table("task_scopes")
    task_scope_status.drop(op.get_bind(), checkfirst=True)
