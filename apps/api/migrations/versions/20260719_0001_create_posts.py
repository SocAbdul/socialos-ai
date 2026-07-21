"""Create tenant-scoped posts.

Revision ID: 20260719_0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260719_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "posts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_posts")),
    )
    op.create_index(
        "ix_posts_organization_created",
        "posts",
        ["organization_id", "created_at"],
    )
    op.create_index(
        "ix_posts_status_scheduled",
        "posts",
        ["status", "scheduled_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_posts_status_scheduled", table_name="posts")
    op.drop_index("ix_posts_organization_created", table_name="posts")
    op.drop_table("posts")
