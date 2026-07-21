from datetime import UTC, datetime, timedelta

import pytest

from socialos.domain.posts.entities import (
    DomainValidationError,
    PostStatus,
    SocialPost,
)


def test_creates_draft_and_normalizes_content() -> None:
    post = SocialPost(
        organization_id="org_test",
        author_id="user_test",
        content="  A useful update  ",
    )

    assert post.content == "A useful update"
    assert post.status is PostStatus.DRAFT


def test_future_schedule_transitions_post() -> None:
    scheduled_at = datetime.now(UTC) + timedelta(hours=1)
    post = SocialPost(
        organization_id="org_test",
        author_id="user_test",
        content="Scheduled",
        scheduled_at=scheduled_at,
    )

    assert post.status is PostStatus.SCHEDULED


@pytest.mark.parametrize("content", ["", "   ", "\n"])
def test_rejects_empty_content(content: str) -> None:
    with pytest.raises(DomainValidationError):
        SocialPost(
            organization_id="org_test",
            author_id="user_test",
            content=content,
        )
