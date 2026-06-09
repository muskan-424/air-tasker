"""user marketplace profiles (skills, PINs, languages)

Revision ID: j2k3l4m5n6o7
Revises: i1j2k3l4m5n6
Create Date: 2026-06-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, UUID

revision: str = "j2k3l4m5n6o7"
down_revision: Union[str, Sequence[str], None] = "i1j2k3l4m5n6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("bio", sa.String(length=1000), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("default_location_pin", sa.String(length=6), nullable=True),
        sa.Column("skills", ARRAY(sa.String(length=64)), nullable=False, server_default="{}"),
        sa.Column("service_pin_codes", ARRAY(sa.String(length=6)), nullable=False, server_default="{}"),
        sa.Column(
            "preferred_languages",
            ARRAY(sa.String(length=10)),
            nullable=False,
            server_default="{en}",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(op.f("ix_user_profiles_user_id"), "user_profiles", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_profiles_user_id"), table_name="user_profiles")
    op.drop_table("user_profiles")
