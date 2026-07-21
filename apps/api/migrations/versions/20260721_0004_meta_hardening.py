"""Harden Meta publishing idempotency and account model.

Revision ID: 20260721_0004
Revises: 20260721_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0004"
down_revision: str | None = "20260721_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("platform_connections", sa.Column("granted_scopes", sa.JSON(), nullable=True))
    op.add_column(
        "platform_connections",
        sa.Column("reauth_required", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "platform_connections",
        sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "platform_connections",
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("UPDATE platform_connections SET granted_scopes = scopes")
    op.alter_column("platform_connections", "granted_scopes", nullable=False)

    op.create_table(
        "social_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("platform_connection_id", sa.Uuid(), nullable=False),
        sa.Column("parent_account_id", sa.Uuid(), nullable=True),
        sa.Column("platform", sa.String(length=48), nullable=False),
        sa.Column("account_type", sa.String(length=48), nullable=False),
        sa.Column("external_account_id", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("selected", sa.Boolean(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("safe_metadata", sa.JSON(), nullable=False),
        sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_account_id"],
            ["social_accounts.id"],
            name=op.f("fk_social_accounts_parent_account_id_social_accounts"),
        ),
        sa.ForeignKeyConstraint(
            ["platform_connection_id"],
            ["platform_connections.id"],
            name=op.f("fk_social_accounts_platform_connection_id_platform_connections"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_social_accounts_workspace_id_workspaces"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_social_accounts")),
        sa.UniqueConstraint(
            "platform_connection_id",
            "platform",
            "external_account_id",
            name="uq_social_accounts_connection_platform_external",
        ),
    )
    op.create_index(
        "ix_social_accounts_workspace_active",
        "social_accounts",
        ["workspace_id", "active"],
    )

    op.add_column("publications", sa.Column("social_account_id", sa.Uuid(), nullable=True))
    op.add_column("publications", sa.Column("container_id", sa.String(length=255), nullable=True))
    op.add_column(
        "publications", sa.Column("container_status", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "publications",
        sa.Column("publishing_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "publications",
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("publications", sa.Column("execution_key", sa.String(length=96), nullable=True))
    op.add_column(
        "publications",
        sa.Column("uncertain_since", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_publications_social_account_id_social_accounts"),
        "publications",
        "social_accounts",
        ["social_account_id"],
        ["id"],
    )
    op.create_index("ix_publications_execution_key", "publications", ["execution_key"], unique=True)

    op.create_index(
        "uq_publications_active_execution",
        "publications",
        ["id"],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('publishing', 'uncertain') AND lease_expires_at IS NOT NULL"
        ),
    )

    op.create_table(
        "oauth_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=48), nullable=False),
        sa.Column("state_hash", sa.String(length=64), nullable=False),
        sa.Column("redirect_uri", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_oauth_states_workspace_id_workspaces"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_oauth_states")),
        sa.UniqueConstraint("state_hash", name="uq_oauth_states_state_hash"),
    )

    op.create_table(
        "connection_audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("platform_connection_id", sa.Uuid(), nullable=True),
        sa.Column("actor_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("safe_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["platform_connection_id"],
            ["platform_connections.id"],
            name=op.f("fk_connection_audit_events_platform_connection_id_platform_connections"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_connection_audit_events_workspace_id_workspaces"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_connection_audit_events")),
    )


def downgrade() -> None:
    op.drop_table("connection_audit_events")
    op.drop_table("oauth_states")
    op.drop_index("uq_publications_active_execution", table_name="publications")
    op.drop_index("ix_publications_execution_key", table_name="publications")
    op.drop_constraint(
        op.f("fk_publications_social_account_id_social_accounts"),
        "publications",
        type_="foreignkey",
    )
    op.drop_column("publications", "uncertain_since")
    op.drop_column("publications", "execution_key")
    op.drop_column("publications", "lease_expires_at")
    op.drop_column("publications", "publishing_started_at")
    op.drop_column("publications", "container_status")
    op.drop_column("publications", "container_id")
    op.drop_column("publications", "social_account_id")
    op.drop_index("ix_social_accounts_workspace_active", table_name="social_accounts")
    op.drop_table("social_accounts")
    op.drop_column("platform_connections", "revoked_at")
    op.drop_column("platform_connections", "last_validated_at")
    op.drop_column("platform_connections", "reauth_required")
    op.drop_column("platform_connections", "granted_scopes")
