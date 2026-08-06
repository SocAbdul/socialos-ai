"""Add intent-bound Meta OAuth sessions.

Revision ID: 20260802_0005
Revises: 20260721_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260802_0005"
down_revision: str | None = "20260721_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "oauth_states",
        sa.Column(
            "connection_intent",
            sa.String(length=32),
            nullable=False,
            server_default="facebook_instagram",
        ),
    )
    op.add_column(
        "oauth_states",
        sa.Column("channel_nonce", sa.String(length=128), nullable=False, server_default="legacy"),
    )
    op.add_column(
        "oauth_states",
        sa.Column(
            "return_to", sa.String(length=255), nullable=False, server_default="/integrations"
        ),
    )
    op.alter_column("oauth_states", "connection_intent", server_default=None)
    op.alter_column("oauth_states", "channel_nonce", server_default=None)
    op.alter_column("oauth_states", "return_to", server_default=None)
    op.add_column("oauth_states", sa.Column("target_connection_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_oauth_states_target_connection_id_platform_connections"),
        "oauth_states",
        "platform_connections",
        ["target_connection_id"],
        ["id"],
    )

    op.create_table(
        "meta_oauth_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_hash", sa.String(length=64), nullable=False),
        sa.Column("oauth_state_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=48), nullable=False),
        sa.Column("connection_intent", sa.String(length=32), nullable=False),
        sa.Column("channel_nonce", sa.String(length=128), nullable=False),
        sa.Column("return_to", sa.String(length=255), nullable=False),
        sa.Column("target_connection_id", sa.Uuid(), nullable=True),
        sa.Column("encrypted_temporary_token", sa.Text(), nullable=False),
        sa.Column("candidates", sa.JSON(), nullable=False),
        sa.Column("required_scopes", sa.JSON(), nullable=False),
        sa.Column("granted_scopes", sa.JSON(), nullable=False),
        sa.Column("declined_scopes", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["oauth_state_id"],
            ["oauth_states.id"],
            name=op.f("fk_meta_oauth_sessions_oauth_state_id_oauth_states"),
        ),
        sa.ForeignKeyConstraint(
            ["target_connection_id"],
            ["platform_connections.id"],
            name=op.f("fk_meta_oauth_sessions_target_connection_id_platform_connections"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_meta_oauth_sessions_workspace_id_workspaces"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_meta_oauth_sessions")),
        sa.UniqueConstraint("session_hash", name="uq_meta_oauth_sessions_session_hash"),
    )
    op.create_index(
        "ix_meta_oauth_sessions_workspace_expires",
        "meta_oauth_sessions",
        ["workspace_id", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_meta_oauth_sessions_workspace_expires", table_name="meta_oauth_sessions")
    op.drop_table("meta_oauth_sessions")
    op.drop_constraint(
        op.f("fk_oauth_states_target_connection_id_platform_connections"),
        "oauth_states",
        type_="foreignkey",
    )
    op.drop_column("oauth_states", "target_connection_id")
    op.drop_column("oauth_states", "return_to")
    op.drop_column("oauth_states", "channel_nonce")
    op.drop_column("oauth_states", "connection_intent")
