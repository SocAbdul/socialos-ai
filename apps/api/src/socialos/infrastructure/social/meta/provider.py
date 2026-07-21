import json
from collections.abc import Mapping, Sequence
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from urllib.parse import urlencode

import httpx

from socialos.application.social.ports import (
    OAuthConnectionCandidate,
    PublishResult,
    SocialProviderCapabilities,
)
from socialos.config import Settings
from socialos.domain.social import Platform, PlatformConnection, SocialAccount, SocialAccountType
from socialos.infrastructure.security.token_cipher import FernetTokenCipher

FACEBOOK_CAPABILITIES = SocialProviderCapabilities(
    supports_text=True,
    supports_single_image=True,
    supports_multiple_images=False,
    supports_video=True,
    supports_reels=False,
    supports_stories=False,
    supports_scheduling=False,
    supports_delete=True,
    max_text_length=63_206,
    supported_media_types=("image/jpeg", "image/png", "video/mp4"),
    daily_publication_limit=None,
)

INSTAGRAM_CAPABILITIES = SocialProviderCapabilities(
    supports_text=False,
    supports_single_image=True,
    supports_multiple_images=True,
    supports_video=True,
    supports_reels=True,
    supports_stories=True,
    supports_scheduling=False,
    supports_delete=False,
    max_text_length=2_200,
    supported_media_types=("image/jpeg", "image/png", "video/mp4"),
    daily_publication_limit=100,
)


class MetaProviderConfigurationError(RuntimeError):
    """Raised when Meta credentials are missing."""


class MetaProviderError(RuntimeError):
    """Raised when Meta Graph API rejects an operation."""


class MetaSocialProvider:
    provider_name = "meta"

    def __init__(
        self,
        settings: Settings,
        cipher: FernetTokenCipher,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._cipher = cipher
        self._client = client
        self._base_url = f"https://graph.facebook.com/{settings.meta_graph_api_version}"

    def authorize(self, state: str, scopes: Sequence[str]) -> str:
        self._require_configured()
        params = {
            "client_id": self._settings.meta_app_id,
            "redirect_uri": self._settings.meta_redirect_uri,
            "state": state,
            "scope": ",".join(scopes),
            "response_type": "code",
        }
        return f"https://www.facebook.com/{self._settings.meta_graph_api_version}/dialog/oauth?{urlencode(params)}"

    async def exchange_code(self, code: str) -> Sequence[OAuthConnectionCandidate]:
        self._require_configured()
        async with self._http_client() as client:
            short_token = await self._get(
                client,
                "/oauth/access_token",
                {
                    "client_id": self._settings.meta_app_id,
                    "client_secret": self._settings.meta_app_secret,
                    "redirect_uri": self._settings.meta_redirect_uri,
                    "code": code,
                },
            )
            long_token = await self._get(
                client,
                "/oauth/access_token",
                {
                    "grant_type": "fb_exchange_token",
                    "client_id": self._settings.meta_app_id,
                    "client_secret": self._settings.meta_app_secret,
                    "fb_exchange_token": str(short_token["access_token"]),
                },
            )
            access_token = str(long_token["access_token"])
            expires_at = _expires_at(long_token.get("expires_in"))
            pages = await self._get(
                client,
                "/me/accounts",
                {
                    "fields": "id,name,access_token,instagram_business_account{id,username,name}",
                    "access_token": access_token,
                },
            )
            candidates: list[OAuthConnectionCandidate] = []
            page_items = cast(list[dict[str, Any]], pages.get("data", []))
            for page in page_items:
                page_token = str(page["access_token"])
                candidates.append(
                    OAuthConnectionCandidate(
                        platform=Platform.FACEBOOK,
                        account_type=SocialAccountType.FACEBOOK_PAGE,
                        external_account_id=str(page["id"]),
                        external_account_name=str(page.get("name") or page["id"]),
                        username=None,
                        parent_external_account_id=None,
                        access_token=page_token,
                        expires_at=expires_at,
                        scopes=[],
                        capabilities=FACEBOOK_CAPABILITIES,
                        safe_metadata={},
                    )
                )
                ig_account = page.get("instagram_business_account")
                if ig_account:
                    candidates.append(
                        OAuthConnectionCandidate(
                            platform=Platform.INSTAGRAM,
                            account_type=SocialAccountType.INSTAGRAM_BUSINESS,
                            external_account_id=str(ig_account["id"]),
                            external_account_name=str(
                                ig_account.get("username")
                                or ig_account.get("name")
                                or ig_account["id"]
                            ),
                            username=(
                                str(ig_account["username"]) if ig_account.get("username") else None
                            ),
                            parent_external_account_id=str(page["id"]),
                            access_token=page_token,
                            expires_at=expires_at,
                            scopes=[],
                            capabilities=INSTAGRAM_CAPABILITIES,
                            safe_metadata={"parent_page_id": str(page["id"])},
                        )
                    )
            return candidates

    async def refresh_credentials(self, encrypted_credentials: str) -> str:
        credentials = self._credentials(encrypted_credentials)
        token = credentials["access_token"]
        async with self._http_client() as client:
            refreshed = await self._get(
                client,
                "/oauth/access_token",
                {
                    "grant_type": "fb_exchange_token",
                    "client_id": self._settings.meta_app_id,
                    "client_secret": self._settings.meta_app_secret,
                    "fb_exchange_token": token,
                },
            )
        return self._cipher.encrypt(json.dumps({"access_token": refreshed["access_token"]}))

    async def validate_connection(self, encrypted_credentials: str) -> bool:
        credentials = self._credentials(encrypted_credentials)
        async with self._http_client() as client:
            response = await client.get(
                f"{self._base_url}/me",
                params={"access_token": credentials["access_token"]},
            )
        return bool(response.status_code == 200)

    async def publish_text(
        self,
        connection: PlatformConnection,
        account: SocialAccount,
        caption: str,
        *,
        idempotency_key: str,
    ) -> PublishResult:
        if account.platform != Platform.FACEBOOK:
            raise MetaProviderError("Text-only publishing is not supported for this platform")
        credentials = self._credentials(connection.encrypted_credentials)
        async with self._http_client() as client:
            payload = await self._post(
                client,
                f"/{account.external_account_id}/feed",
                {"message": caption, "access_token": credentials["access_token"]},
            )
        post_id = str(payload["id"])
        return PublishResult(
            external_publication_id=post_id,
            external_url=f"https://www.facebook.com/{post_id}",
            provider_request_id=idempotency_key,
        )

    async def publish_image(
        self,
        connection: PlatformConnection,
        account: SocialAccount,
        caption: str,
        media_url: str,
        *,
        idempotency_key: str,
    ) -> PublishResult:
        credentials = self._credentials(connection.encrypted_credentials)
        async with self._http_client() as client:
            if account.platform == Platform.FACEBOOK:
                payload = await self._post(
                    client,
                    f"/{account.external_account_id}/photos",
                    {
                        "url": media_url,
                        "caption": caption,
                        "access_token": credentials["access_token"],
                    },
                )
                photo_id = str(payload["id"])
                return PublishResult(
                    external_publication_id=photo_id,
                    external_url=f"https://www.facebook.com/{photo_id}",
                    provider_request_id=idempotency_key,
                )
            container = await self._post(
                client,
                f"/{account.external_account_id}/media",
                {
                    "image_url": media_url,
                    "caption": caption,
                    "access_token": credentials["access_token"],
                },
            )
            container_id = str(container["id"])
            await self._poll_container_ready(client, container_id, credentials["access_token"])
            published = await self._post(
                client,
                f"/{account.external_account_id}/media_publish",
                {
                    "creation_id": container_id,
                    "access_token": credentials["access_token"],
                },
            )
            media_id = str(published["id"])
            return PublishResult(
                external_publication_id=media_id,
                external_url=f"https://www.instagram.com/p/{media_id}/",
                provider_request_id=idempotency_key,
            )

    async def publish_video(
        self,
        connection: PlatformConnection,
        account: SocialAccount,
        caption: str,
        media_url: str,
        *,
        idempotency_key: str,
    ) -> PublishResult:
        credentials = self._credentials(connection.encrypted_credentials)
        if account.platform != Platform.INSTAGRAM:
            raise MetaProviderError("Video publishing for Facebook is not enabled in this slice")
        async with self._http_client() as client:
            container = await self._post(
                client,
                f"/{account.external_account_id}/media",
                {
                    "media_type": "REELS",
                    "video_url": media_url,
                    "caption": caption,
                    "access_token": credentials["access_token"],
                },
            )
            container_id = str(container["id"])
            await self._poll_container_ready(client, container_id, credentials["access_token"])
            published = await self._post(
                client,
                f"/{account.external_account_id}/media_publish",
                {"creation_id": container_id, "access_token": credentials["access_token"]},
            )
        media_id = str(published["id"])
        return PublishResult(
            external_publication_id=media_id,
            external_url=f"https://www.instagram.com/p/{media_id}/",
            provider_request_id=idempotency_key,
        )

    async def get_publication_status(
        self,
        connection: PlatformConnection,
        account: SocialAccount,
        external_publication_id: str,
    ) -> str:
        credentials = self._credentials(connection.encrypted_credentials)
        async with self._http_client() as client:
            await self._get(
                client,
                f"/{external_publication_id}",
                {"fields": "id", "access_token": credentials["access_token"]},
            )
        return "available"

    async def delete_publication(
        self, connection: PlatformConnection, external_publication_id: str
    ) -> None:
        if not bool(connection.capabilities.get("supports_delete")):
            raise MetaProviderError("Delete is not supported for this platform")
        credentials = self._credentials(connection.encrypted_credentials)
        async with self._http_client() as client:
            await self._post(
                client,
                f"/{external_publication_id}",
                {"access_token": credentials["access_token"], "method": "delete"},
            )

    async def _poll_container_ready(
        self,
        client: httpx.AsyncClient,
        container_id: str,
        access_token: str,
        *,
        max_polls: int = 12,
    ) -> str:
        for _ in range(max_polls):
            payload = await self._get(
                client,
                f"/{container_id}",
                {"fields": "status_code", "access_token": access_token},
            )
            status_code = str(payload.get("status_code") or "")
            if status_code == "FINISHED":
                return status_code
            if status_code in {"ERROR", "EXPIRED"}:
                raise MetaProviderError(f"Instagram media container status is {status_code}")
        raise TimeoutError("Instagram media container did not become ready before timeout")

    def get_capabilities(self, platform: Platform) -> SocialProviderCapabilities:
        return INSTAGRAM_CAPABILITIES if platform == Platform.INSTAGRAM else FACEBOOK_CAPABILITIES

    def _credentials(self, encrypted_credentials: str) -> dict[str, str]:
        return cast(dict[str, str], json.loads(self._cipher.decrypt(encrypted_credentials)))

    def _require_configured(self) -> None:
        if not self._settings.meta_app_id or not self._settings.meta_app_secret:
            raise MetaProviderConfigurationError("META_APP_ID and META_APP_SECRET are required")

    def _http_client(self) -> AbstractAsyncContextManager[httpx.AsyncClient]:
        if self._client is not None:
            return _BorrowedAsyncClient(self._client)
        return httpx.AsyncClient(timeout=30)

    async def _get(
        self,
        client: httpx.AsyncClient,
        path: str,
        params: Mapping[str, str | int | float | bool | None],
    ) -> dict[str, object]:
        response = await client.get(f"{self._base_url}{path}", params=params)
        return _json_or_raise(response)

    async def _post(
        self, client: httpx.AsyncClient, path: str, data: dict[str, object]
    ) -> dict[str, object]:
        response = await client.post(f"{self._base_url}{path}", data=data)
        return _json_or_raise(response)


class _BorrowedAsyncClient:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def __aenter__(self) -> httpx.AsyncClient:
        return self._client

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


def _json_or_raise(response: httpx.Response) -> dict[str, object]:
    payload = cast(dict[str, Any], response.json())
    if response.status_code >= 400:
        error = payload.get("error", {})
        message = error.get("message", response.text) if isinstance(error, dict) else response.text
        raise MetaProviderError(str(message))
    return cast(dict[str, object], payload)


def _expires_at(expires_in: object) -> datetime | None:
    if expires_in is None:
        return None
    if isinstance(expires_in, int | str):
        return datetime.now(UTC) + timedelta(seconds=int(expires_in))
    return None
