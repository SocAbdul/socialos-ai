"""Persist the portable media storage provider.

Revision ID: 20260809_0007
Revises: 20260808_0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_0007"
down_revision: str | None = "20260808_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "media_assets",
        sa.Column(
            "storage_provider",
            sa.String(length=32),
            nullable=False,
            server_default="external",
        ),
    )
    op.alter_column("media_assets", "storage_provider", server_default=None)


def downgrade() -> None:
    op.drop_column("media_assets", "storage_provider")
