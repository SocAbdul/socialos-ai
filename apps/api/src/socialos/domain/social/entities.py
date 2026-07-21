from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class DomainValidationError(ValueError):
    """Raised when a social aggregate invariant is violated."""


class Platform(StrEnum):
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"


class MediaType(StrEnum):
    IMAGE = "image"
    VIDEO = "video"


class PublicationStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    SCHEDULED = "scheduled"
    QUEUED = "queued"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED_RETRYABLE = "failed_retryable"
    FAILED_PERMANENT = "failed_permanent"
    UNCERTAIN = "uncertain"
    CANCELLED = "cancelled"


class AttemptStatus(StrEnum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED_RETRYABLE = "failed_retryable"
    FAILED_PERMANENT = "failed_permanent"
    UNCERTAIN = "uncertain"


class SocialAccountType(StrEnum):
    FACEBOOK_PAGE = "facebook_page"
    INSTAGRAM_BUSINESS = "instagram_business"
    INSTAGRAM_CREATOR = "instagram_creator"


class AIOperation(StrEnum):
    GENERATE_CAPTION = "generate_caption"
    ADAPT_FOR_PLATFORM = "adapt_for_platform"
    GENERATE_HASHTAGS = "generate_hashtags"
    GENERATE_CALL_TO_ACTION = "generate_call_to_action"
    REWRITE_TONE = "rewrite_tone"
    TRANSLATE_CONTENT = "translate_content"


@dataclass(slots=True)
class Workspace:
    owner_id: str
    name: str
    external_organization_id: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        if not self.name:
            raise DomainValidationError("Workspace name cannot be empty")


@dataclass(slots=True)
class Membership:
    workspace_id: UUID
    user_id: str
    role: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class BrandProfile:
    workspace_id: UUID
    name: str
    voice: str = ""
    audience: str = ""
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        if not self.name:
            raise DomainValidationError("Brand profile name cannot be empty")


@dataclass(slots=True)
class PlatformConnection:
    workspace_id: UUID
    provider: str
    platform: Platform
    external_account_id: str
    external_account_name: str
    encrypted_credentials: str
    scopes: list[str]
    capabilities: dict[str, object]
    expires_at: datetime | None = None
    granted_scopes: list[str] = field(default_factory=list)
    reauth_required: bool = False
    last_validated_at: datetime | None = None
    revoked_at: datetime | None = None
    id: UUID = field(default_factory=uuid4)
    is_valid: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class SocialAccount:
    workspace_id: UUID
    platform_connection_id: UUID
    platform: Platform
    account_type: SocialAccountType
    external_account_id: str
    display_name: str
    capabilities: dict[str, object]
    username: str | None = None
    parent_account_id: UUID | None = None
    selected: bool = False
    active: bool = True
    safe_metadata: dict[str, object] = field(default_factory=dict)
    last_validated_at: datetime | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class Campaign:
    workspace_id: UUID
    brand_profile_id: UUID
    name: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class ContentItem:
    workspace_id: UUID
    campaign_id: UUID
    author_id: str
    body: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        self.body = self.body.strip()
        if not self.body:
            raise DomainValidationError("Content body cannot be empty")


@dataclass(slots=True)
class MediaAsset:
    workspace_id: UUID
    uploader_id: str
    media_type: MediaType
    storage_url: str
    content_type: str
    checksum_sha256: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class Publication:
    workspace_id: UUID
    content_item_id: UUID
    platform_connection_id: UUID
    social_account_id: UUID
    platform: Platform
    caption: str
    media_asset_id: UUID | None = None
    scheduled_at: datetime | None = None
    status: PublicationStatus = PublicationStatus.DRAFT
    idempotency_key: str = field(default_factory=lambda: str(uuid4()))
    external_publication_id: str | None = None
    external_url: str | None = None
    container_id: str | None = None
    container_status: str | None = None
    last_error: str | None = None
    next_attempt_at: datetime | None = None
    publishing_started_at: datetime | None = None
    lease_expires_at: datetime | None = None
    execution_key: str | None = None
    uncertain_since: datetime | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def mark_ready(self) -> None:
        if self.status != PublicationStatus.DRAFT:
            raise DomainValidationError("Only draft publications can become ready")
        self.status = PublicationStatus.READY
        self.updated_at = datetime.now(UTC)

    def schedule(self, scheduled_at: datetime) -> None:
        if scheduled_at.tzinfo is None or scheduled_at <= datetime.now(UTC):
            raise DomainValidationError("Schedule time must be in the future")
        if self.status not in {PublicationStatus.DRAFT, PublicationStatus.READY}:
            raise DomainValidationError("Only draft or ready publications can be scheduled")
        self.status = PublicationStatus.SCHEDULED
        self.scheduled_at = scheduled_at
        self.updated_at = datetime.now(UTC)


@dataclass(slots=True)
class PublicationAttempt:
    publication_id: UUID
    attempt_number: int
    status: AttemptStatus
    provider: str
    request_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    external_publication_id: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class Schedule:
    publication_id: UUID
    run_at: datetime
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class AIGeneration:
    workspace_id: UUID
    operation: AIOperation
    provider: str
    model: str
    prompt_version: str
    input_hash: str
    token_usage: dict[str, int]
    estimated_cost: str
    latency_ms: int
    result: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class UsageEvent:
    workspace_id: UUID
    event_type: str
    quantity: int
    metadata: dict[str, object]
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
