from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from socialos.domain.posts.entities import PostStatus, SocialPost


class CreatePostRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=10_000)
    scheduled_at: datetime | None = None


class PostResponse(BaseModel):
    id: UUID
    organization_id: str
    author_id: str
    content: str
    status: PostStatus
    scheduled_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, post: SocialPost) -> "PostResponse":
        return cls(
            id=post.id,
            organization_id=post.organization_id,
            author_id=post.author_id,
            content=post.content,
            status=post.status,
            scheduled_at=post.scheduled_at,
            created_at=post.created_at,
            updated_at=post.updated_at,
        )


class PostListResponse(BaseModel):
    items: list[PostResponse]
    limit: int
    offset: int
