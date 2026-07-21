from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from socialos.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PostModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "posts"
    __table_args__ = (
        Index("ix_posts_organization_created", "organization_id", "created_at"),
        Index("ix_posts_status_scheduled", "status", "scheduled_at"),
    )

    organization_id: Mapped[str] = mapped_column(String(64), nullable=False)
    author_id: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkspaceModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        Index("ix_workspaces_owner_created", "owner_id", "created_at"),
        UniqueConstraint("external_organization_id", name="uq_workspaces_external_organization_id"),
    )

    owner_id: Mapped[str] = mapped_column(String(64), nullable=False)
    external_organization_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)


class MembershipModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_memberships_workspace_user"),
        Index("ix_memberships_user", "user_id"),
    )

    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BrandProfileModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "brand_profiles"
    __table_args__ = (Index("ix_brand_profiles_workspace_created", "workspace_id", "created_at"),)

    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    voice: Mapped[str] = mapped_column(Text, nullable=False, default="")
    audience: Mapped[str] = mapped_column(Text, nullable=False, default="")


class PlatformConnectionModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "platform_connections"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "provider",
            "platform",
            "external_account_id",
            name="uq_platform_connections_account",
        ),
        Index("ix_platform_connections_workspace_created", "workspace_id", "created_at"),
    )

    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(48), nullable=False)
    platform: Mapped[str] = mapped_column(String(48), nullable=False)
    external_account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    external_account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_credentials: Mapped[str] = mapped_column(Text, nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    granted_scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    capabilities: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reauth_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SocialAccountModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "social_accounts"
    __table_args__ = (
        UniqueConstraint(
            "platform_connection_id",
            "platform",
            "external_account_id",
            name="uq_social_accounts_connection_platform_external",
        ),
        Index("ix_social_accounts_workspace_active", "workspace_id", "active"),
    )

    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    platform_connection_id: Mapped[UUID] = mapped_column(
        ForeignKey("platform_connections.id"), nullable=False
    )
    parent_account_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("social_accounts.id"), nullable=True
    )
    platform: Mapped[str] = mapped_column(String(48), nullable=False)
    account_type: Mapped[str] = mapped_column(String(48), nullable=False)
    external_account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    capabilities: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    safe_metadata: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    last_validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class CampaignModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "campaigns"
    __table_args__ = (Index("ix_campaigns_workspace_created", "workspace_id", "created_at"),)

    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    brand_profile_id: Mapped[UUID] = mapped_column(ForeignKey("brand_profiles.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)


class ContentItemModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "content_items"
    __table_args__ = (Index("ix_content_items_workspace_created", "workspace_id", "created_at"),)

    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    campaign_id: Mapped[UUID] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    author_id: Mapped[str] = mapped_column(String(64), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)


class MediaAssetModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "media_assets"
    __table_args__ = (Index("ix_media_assets_workspace_created", "workspace_id", "created_at"),)

    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    uploader_id: Mapped[str] = mapped_column(String(64), nullable=False)
    media_type: Mapped[str] = mapped_column(String(32), nullable=False)
    storage_url: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PublicationModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "publications"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_publications_idempotency_key"),
        Index("ix_publications_workspace_created", "workspace_id", "created_at"),
        Index("ix_publications_status_next_attempt", "status", "next_attempt_at"),
    )

    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    content_item_id: Mapped[UUID] = mapped_column(ForeignKey("content_items.id"), nullable=False)
    platform_connection_id: Mapped[UUID] = mapped_column(
        ForeignKey("platform_connections.id"), nullable=False
    )
    social_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("social_accounts.id"), nullable=False
    )
    media_asset_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("media_assets.id"), nullable=True
    )
    platform: Mapped[str] = mapped_column(String(48), nullable=False)
    caption: Mapped[str] = mapped_column(Text, nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(96), nullable=False)
    external_publication_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    container_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    container_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    publishing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    execution_key: Mapped[str | None] = mapped_column(String(96), nullable=True)
    uncertain_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PublicationAttemptModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "publication_attempts"
    __table_args__ = (
        Index("ix_publication_attempts_publication_created", "publication_id", "created_at"),
    )

    publication_id: Mapped[UUID] = mapped_column(ForeignKey("publications.id"), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str] = mapped_column(String(48), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_publication_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ScheduleModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "schedules"
    __table_args__ = (Index("ix_schedules_run_at", "run_at"),)

    publication_id: Mapped[UUID] = mapped_column(ForeignKey("publications.id"), nullable=False)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AIGenerationModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ai_generations"
    __table_args__ = (
        UniqueConstraint("workspace_id", "operation", "input_hash", name="uq_ai_generation_cache"),
        Index("ix_ai_generations_workspace_created", "workspace_id", "created_at"),
    )

    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(48), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    token_usage: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    estimated_cost: Mapped[str] = mapped_column(String(32), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    result: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UsageEventModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "usage_events"
    __table_args__ = (Index("ix_usage_events_workspace_created", "workspace_id", "created_at"),)

    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    extra_metadata: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OAuthStateModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "oauth_states"

    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(48), nullable=False)
    state_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    redirect_uri: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ConnectionAuditEventModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "connection_audit_events"

    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    platform_connection_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("platform_connections.id"), nullable=True
    )
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    safe_metadata: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
