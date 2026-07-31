from __future__ import annotations

import hashlib
from collections.abc import Sequence

from socialos.application.social.ports import (
    OAuthConnectionCandidate,
    PublishResult,
    SocialProviderCapabilities,
)
from socialos.domain.social import Platform, PlatformConnection, SocialAccount


class LocalDevelopmentRetryableError(RuntimeError):
    retryable = True
    error_code = "LOCAL_RETRYABLE"
    consume_caption_marker = "[local-retryable-error]"


class LocalDevelopmentSocialProvider:
    """Development-only provider that exercises the publication state machine.

    It never talks to a social network. The deterministic external id keeps worker retries
    idempotent while still recording real PublicationAttempt rows in local PostgreSQL.
    """

    provider_name = "local-dev"

    def authorize(self, state: str, scopes: object) -> str:
        return f"http://localhost:3000/?local_social_state={state}"

    async def exchange_code(self, code: str) -> Sequence[OAuthConnectionCandidate]:
        return ()

    async def refresh_credentials(self, encrypted_credentials: str) -> str:
        return encrypted_credentials

    async def validate_connection(self, encrypted_credentials: str) -> bool:
        return True

    async def publish_text(
        self,
        connection: PlatformConnection,
        account: SocialAccount,
        caption: str,
        *,
        idempotency_key: str,
    ) -> PublishResult:
        return self._publish(connection, account, caption, idempotency_key)

    async def publish_image(
        self,
        connection: PlatformConnection,
        account: SocialAccount,
        caption: str,
        media_url: str,
        *,
        idempotency_key: str,
    ) -> PublishResult:
        return self._publish(connection, account, caption, idempotency_key)

    async def publish_video(
        self,
        connection: PlatformConnection,
        account: SocialAccount,
        caption: str,
        media_url: str,
        *,
        idempotency_key: str,
    ) -> PublishResult:
        return self._publish(connection, account, caption, idempotency_key)

    async def get_publication_status(
        self,
        connection: PlatformConnection,
        account: SocialAccount,
        external_publication_id: str,
    ) -> str:
        return "published"

    async def delete_publication(
        self, connection: PlatformConnection, external_publication_id: str
    ) -> None:
        return None

    def get_capabilities(self, platform: Platform) -> SocialProviderCapabilities:
        return _capabilities(platform)

    def _publish(
        self,
        connection: PlatformConnection,
        account: SocialAccount,
        caption: str,
        idempotency_key: str,
    ) -> PublishResult:
        if "[local-retryable-error]" in caption.lower():
            raise LocalDevelopmentRetryableError(
                "Local development provider simulated a retryable network error"
            )
        digest = hashlib.sha256(
            f"{connection.id}:{account.id}:{idempotency_key}".encode()
        ).hexdigest()[:16]
        external_id = f"local-dev-{account.platform.value}-{digest}"
        return PublishResult(
            external_publication_id=external_id,
            external_url=f"https://local.socialos.invalid/publications/{external_id}",
            provider_request_id=f"local-request-{digest}",
        )


def _capabilities(platform: Platform) -> SocialProviderCapabilities:
    return SocialProviderCapabilities(
        supports_text=platform == Platform.FACEBOOK,
        supports_single_image=True,
        supports_multiple_images=False,
        supports_video=False,
        supports_reels=False,
        supports_stories=False,
        supports_scheduling=True,
        supports_delete=True,
        max_text_length=2200 if platform == Platform.INSTAGRAM else 5000,
        supported_media_types=("image/jpeg", "image/png"),
        daily_publication_limit=25,
    )
