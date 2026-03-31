"""user KYC profile (India — PAN / Aadhaar last4; stub provider)

Revision ID: i1j2k3l4m5n6
Revises: h1a2b3c4d5e6
Create Date: 2026-03-31

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "i1j2k3l4m5n6"
down_revision: Union[str, Sequence[str], None] = "h1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_kyc_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="stub"),
        sa.Column("provider_reference_id", sa.String(length=255), nullable=True),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("pan_last4", sa.String(length=4), nullable=False),
        sa.Column("aadhaar_last4", sa.String(length=4), nullable=True),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.String(length=500), nullable=True),
        sa.Column("metadata_json", JSONB(), nullable=True),
        sa.UniqueConstraint("user_id", name="uq_user_kyc_profiles_user_id"),
    )
    op.create_index("ix_user_kyc_profiles_status", "user_kyc_profiles", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_kyc_profiles_status", table_name="user_kyc_profiles")
    op.drop_table("user_kyc_profiles")
