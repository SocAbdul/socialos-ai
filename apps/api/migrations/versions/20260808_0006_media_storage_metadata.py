"""Persist secure media storage metadata.

Revision ID: 20260808_0006
Revises: 20260802_0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260808_0006"
down_revision: str | None = "20260802_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "media_assets",
        sa.Column("storage_key", sa.String(length=512), nullable=False, server_default="legacy"),
    )
    op.add_column(
        "media_assets", sa.Column("size_bytes", sa.BigInteger(), nullable=False, server_default="0")
    )
    op.alter_column("media_assets", "storage_key", server_default=None)
    op.alter_column("media_assets", "size_bytes", server_default=None)


def downgrade() -> None:
    op.drop_column("media_assets", "size_bytes")
    op.drop_column("media_assets", "storage_key")
