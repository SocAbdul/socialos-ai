"""Use opaque Clerk identifiers for tenant and author identity.

Revision ID: 20260720_0002
Revises: 20260719_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260720_0002"
down_revision: str | None = "20260719_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "posts",
        "organization_id",
        existing_type=sa.Uuid(),
        type_=sa.String(length=64),
        postgresql_using="organization_id::text",
        existing_nullable=False,
    )
    op.alter_column(
        "posts",
        "author_id",
        existing_type=sa.Uuid(),
        type_=sa.String(length=64),
        postgresql_using="author_id::text",
        existing_nullable=False,
    )


def downgrade() -> None:
    raise RuntimeError(
        "This migration is irreversible after Clerk identifiers have been stored. "
        "Restore a verified database backup instead."
    )
