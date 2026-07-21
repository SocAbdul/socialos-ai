from collections.abc import Sequence
from types import TracebackType
from typing import Self, cast

import pytest

from socialos.application.common.auth import Actor, OrganizationRole
from socialos.application.posts.ports import PostRepository, UnitOfWork
from socialos.application.posts.use_cases import CreatePost, CreatePostCommand
from socialos.domain.posts.entities import SocialPost


class InMemoryPostRepository:
    def __init__(self) -> None:
        self.items: list[SocialPost] = []

    async def add(self, post: SocialPost) -> SocialPost:
        self.items.append(post)
        return post

    async def list_for_organization(
        self, organization_id: str, *, limit: int, offset: int
    ) -> Sequence[SocialPost]:
        matches = [item for item in self.items if item.organization_id == organization_id]
        return matches[offset : offset + limit]


class FakeUnitOfWork:
    def __init__(self, repository: InMemoryPostRepository) -> None:
        self.posts = cast(PostRepository, repository)
        self.committed = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True


@pytest.mark.asyncio
async def test_create_post_scopes_it_to_actor() -> None:
    repository = InMemoryPostRepository()
    uow = FakeUnitOfWork(repository)
    actor = Actor(
        user_id="user_test",
        organization_id="org_test",
        role=OrganizationRole.ADMIN,
    )

    post = await CreatePost(lambda: cast(UnitOfWork, uow)).execute(
        actor,
        CreatePostCommand(content="Launch update"),
    )

    assert post.organization_id == actor.organization_id
    assert post.author_id == actor.user_id
    assert repository.items == [post]
    assert uow.committed is True
