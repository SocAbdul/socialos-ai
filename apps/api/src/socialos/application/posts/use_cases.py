from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime

from socialos.application.common.auth import Actor, Permission
from socialos.application.posts.ports import UnitOfWork
from socialos.domain.posts.entities import SocialPost


@dataclass(frozen=True, slots=True)
class CreatePostCommand:
    content: str
    scheduled_at: datetime | None = None


class CreatePost:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, actor: Actor, command: CreatePostCommand) -> SocialPost:
        actor.require(Permission.POSTS_WRITE)
        post = SocialPost(
            organization_id=actor.organization_id,
            author_id=actor.user_id,
            content=command.content,
            scheduled_at=command.scheduled_at,
        )
        async with self._uow_factory() as uow:
            await uow.posts.add(post)
            await uow.commit()
        return post


class ListPosts:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(
        self, actor: Actor, *, limit: int = 50, offset: int = 0
    ) -> Sequence[SocialPost]:
        actor.require(Permission.POSTS_READ)
        async with self._uow_factory() as uow:
            return await uow.posts.list_for_organization(
                actor.organization_id,
                limit=min(limit, 100),
                offset=max(offset, 0),
            )
