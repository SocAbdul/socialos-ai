from collections.abc import Sequence
from types import TracebackType
from typing import Protocol

from socialos.domain.posts.entities import SocialPost


class PostRepository(Protocol):
    async def add(self, post: SocialPost) -> SocialPost: ...

    async def list_for_organization(
        self, organization_id: str, *, limit: int, offset: int
    ) -> Sequence[SocialPost]: ...


class UnitOfWork(Protocol):
    posts: PostRepository

    async def __aenter__(self) -> "UnitOfWork": ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...


class SocialPublisher(Protocol):
    """Every external network adapter must implement this contract."""

    @property
    def provider_name(self) -> str: ...

    async def publish(self, post: SocialPost, access_token: str) -> str:
        """Publish content and return the provider's external post ID."""
        ...
