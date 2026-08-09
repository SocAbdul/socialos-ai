from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


@dataclass(frozen=True, slots=True)
class PostMetrics:
    impressions: int | None = None
    reach: int | None = None
    likes: int | None = None
    comments: int | None = None
    shares: int | None = None
    saves: int | None = None
    clicks: int | None = None
    video_views: int | None = None
    watch_time: float | None = None
    followers_delta: int | None = None
    fetched_at: datetime | None = None


class EngagementEventType(StrEnum):
    COMMENT = "comment"
    MENTION = "mention"
    REPLY = "reply"
    REVIEW = "review"
    MESSAGE = "message"


@dataclass(frozen=True, slots=True)
class EngagementEventReference:
    event_type: EngagementEventType
    provider: str
    platform: str
    external_event_id: str
    occurred_at: datetime

    # Deliberately excludes message/comment bodies until retention and privacy rules exist.
