from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class PostStatus(StrEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    PARTIALLY_FAILED = "partially_failed"
    FAILED = "failed"


class DomainValidationError(ValueError):
    """Raised when an aggregate invariant is violated."""


@dataclass(slots=True)
class SocialPost:
    organization_id: str
    author_id: str
    content: str
    id: UUID = field(default_factory=uuid4)
    status: PostStatus = PostStatus.DRAFT
    scheduled_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        self.content = self.content.strip()
        if not self.content:
            raise DomainValidationError("Post content cannot be empty")
        if len(self.content) > 10_000:
            raise DomainValidationError("Post content cannot exceed 10,000 characters")
        if self.scheduled_at is not None:
            if self.scheduled_at.tzinfo is None:
                raise DomainValidationError("Scheduled time must include a timezone")
            if self.scheduled_at <= datetime.now(UTC):
                raise DomainValidationError("Scheduled time must be in the future")
            self.status = PostStatus.SCHEDULED
