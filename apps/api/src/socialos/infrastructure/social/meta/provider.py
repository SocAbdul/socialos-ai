import json
import secrets
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
    supports_video=False,
    supports_reels=False,
    supports_stories=False,
    supports_scheduling=False,
    supports_delete=False,
    max_text_length=63_206,
    supported_media_types=("image/jpeg", "image/png"),
    daily_publication_limit=None,
)

INSTAGRAM_CAPABILITIES = SocialProviderCapabilities(
    supports_text=False,
    supports_single_image=True,
    supports_multiple_images=False,
    supports_video=False,
    supports_reels=False,
    supports_stories=False,
    supports_scheduling=False,
    supports_delete=False,
    max_text_length=2_200,
    supported_media_types=("image/jpeg", "image/png"),
    daily_publication_limit=100,
)


class MetaProviderConfigurationError(RuntimeError):
    """Raised when Meta credentials are missing."""


class MetaProviderError(RuntimeError):
    """Raised when Meta Graph API rejects an operation."""

    def __init__(
        self,
        message: str,
        *,
        retryable: bool = False,
        error_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.error_code = error_code


META_REQUIRED_SCOPES = frozenset(
    {
        "business_management",
        "pages_show_list",
        "pages_read_engagement",
        "pages_manage_posts",
        "instagram_basic",
        "instagram_content_publish",
    }
)


class MetaPermissionError(MetaProviderError):
    """Raised when the fixed Meta configuration did not grant its required package."""


class MetaPageCandidate:
    def __init__(
        self,
        *,
        candidate_id: str,
        page_id: str,
        page_name: str,
        page_access_token: str,
        page_avatar_url: str | None,
        page_tasks: list[str],
        instagram: dict[str, str] | None,
    ) -> None:
        self.candidate_id = candidate_id
        self.page_id = page_id
        self.page_name = page_name
        self.page_access_token = page_access_token
        self.page_avatar_url = page_avatar_url
        self.page_tasks = page_tasks
        self.instagram = instagram

    def safe_dict(self) -> dict[str, object]:
        instagram = self.instagram
        return {
            "candidate_id": self.candidate_id,
            "page_name": self.page_name,
            "masked_page_id": _mask_identifier(self.page_id),
            "page_avatar_url": _safe_https_url(self.page_avatar_url),
            "instagram_username": instagram.get("username") if instagram else None,
            "instagram_display_name": instagram.get("name") if instagram else None,
            "instagram_account_type": instagram.get("account_type") if instagram else None,
            "instagram_avatar_url": (
                _safe_https_url(instagram.get("profile_picture_url")) if instagram else None
            ),
            "masked_instagram_id": (
                _mask_identifier(instagram["id"]) if instagram and instagram.get("id") else None
            ),
            "linked_page_name": self.page_name,
            "compatible": instagram is not None,
            "compatibility_message": (
                "Facebook Page and professional Instagram account are available."
                if instagram
                else "No professional Instagram account is linked to this Page."
            ),
        }

    def secret_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "page_id": self.page_id,
            "page_name": self.page_name,
            "page_access_token": self.page_access_token,
            "page_avatar_url": _safe_https_url(self.page_avatar_url),
            "page_tasks": self.page_tasks,
            "instagram": self.instagram,
        }


class MetaAuthorizationExchange:
    def __init__(
        self,
        *,
        candidates: list[MetaPageCandidate],
        granted_scopes: list[str],
        declined_scopes: list[str],
        expires_at: datetime | None,
    ) -> None:
        self.candidates = candidates
        self.granted_scopes = granted_scopes
        self.declined_scopes = declined_scopes
        self.expires_at = expires_at


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
            "config_id": self._settings.meta_login_config_id,
            "response_type": "code",
        }
        return f"https://www.facebook.com/{self._settings.meta_graph_api_version}/dialog/oauth?{urlencode(params)}"

    async def exchange_authorization(self, code: str) -> MetaAuthorizationExchange:
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
            permissions = await self._get(client, "/me/permissions", {"access_token": access_token})
            granted, declined = _permission_sets(permissions)
            pages = await self._get(
                client,
                "/me/accounts",
                {
                    "fields": (
                        "id,name,access_token,tasks,picture{url},"
                        "instagram_business_account{"
                        "id,username,name,account_type,profile_picture_url}"
                    ),
                    "access_token": access_token,
                },
            )
            candidates: list[MetaPageCandidate] = []
            for page in cast(list[dict[str, Any]], pages.get("data", [])):
                picture = cast(dict[str, Any], page.get("picture") or {})
                picture_data = cast(dict[str, Any], picture.get("data") or {})
                raw_instagram = page.get("instagram_business_account")
                instagram = (
                    {key: str(value) for key, value in raw_instagram.items() if value is not None}
                    if isinstance(raw_instagram, dict)
                    else None
                )
                candidates.append(
                    MetaPageCandidate(
                        candidate_id=secrets.token_urlsafe(24),
                        page_id=str(page["id"]),
                        page_name=str(page.get("name") or page["id"]),
                        page_access_token=str(page["access_token"]),
                        page_avatar_url=(
                            str(picture_data["url"]) if picture_data.get("url") else None
                        ),
                        page_tasks=[str(task) for task in page.get("tasks", [])],
                        instagram=instagram,
                    )
                )
            return MetaAuthorizationExchange(
                candidates=candidates,
                granted_scopes=granted,
                declined_scopes=declined,
                expires_at=expires_at,
            )

    async def exchange_code(self, code: str) -> Sequence[OAuthConnectionCandidate]:
        result = await self.exchange_authorization(code)
        candidates: list[OAuthConnectionCandidate] = []
        for page in result.candidates:
            page_token = page.page_access_token
            candidates.append(
                OAuthConnectionCandidate(
                    platform=Platform.FACEBOOK,
                    account_type=SocialAccountType.FACEBOOK_PAGE,
                    external_account_id=page.page_id,
                    external_account_name=page.page_name,
                    username=None,
                    parent_external_account_id=None,
                    access_token=page_token,
                    expires_at=result.expires_at,
                    scopes=result.granted_scopes,
                    capabilities=FACEBOOK_CAPABILITIES,
                    safe_metadata={},
                )
            )
            ig_account = page.instagram
            if ig_account:
                candidates.append(
                    OAuthConnectionCandidate(
                        platform=Platform.INSTAGRAM,
                        account_type=SocialAccountType.INSTAGRAM_BUSINESS,
                        external_account_id=str(ig_account["id"]),
                        external_account_name=str(
                            ig_account.get("username") or ig_account.get("name") or ig_account["id"]
                        ),
                        username=(
                            str(ig_account["username"]) if ig_account.get("username") else None
                        ),
                        parent_external_account_id=page.page_id,
                        access_token=page_token,
                        expires_at=result.expires_at,
                        scopes=result.granted_scopes,
                        capabilities=INSTAGRAM_CAPABILITIES,
                        safe_metadata={"parent_page_id": page.page_id},
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
            media = await self._get(
                client,
                f"/{media_id}",
                {"fields": "id,permalink", "access_token": credentials["access_token"]},
            )
            return PublishResult(
                external_publication_id=media_id,
                external_url=str(media.get("permalink")) if media.get("permalink") else None,
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
        raise MetaProviderError("Video publishing is not enabled for verified Meta capabilities")

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
        if (
            not self._settings.meta_app_id
            or not self._settings.meta_app_secret
            or not self._settings.meta_login_config_id
        ):
            raise MetaProviderConfigurationError(
                "META_APP_ID, META_APP_SECRET and META_LOGIN_CONFIG_ID are required"
            )

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
        message = (
            error.get("message", "Meta rejected the request")
            if isinstance(error, dict)
            else "Meta rejected the request"
        )
        raw_code = error.get("code") if isinstance(error, dict) else None
        error_code = str(raw_code) if raw_code is not None else None
        raise MetaProviderError(
            str(message),
            retryable=_is_retryable_meta_error(response.status_code, error_code),
            error_code=error_code,
        )
    return cast(dict[str, object], payload)


def _is_retryable_meta_error(status_code: int, error_code: str | None) -> bool:
    if status_code >= 500:
        return True
    return error_code in {"1", "2", "4", "17", "32", "613"}


def _expires_at(expires_in: object) -> datetime | None:
    if expires_in is None:
        return None
    if isinstance(expires_in, int | str):
        return datetime.now(UTC) + timedelta(seconds=int(expires_in))
    return None


def _permission_sets(payload: Mapping[str, object]) -> tuple[list[str], list[str]]:
    granted: list[str] = []
    declined: list[str] = []
    for item in cast(list[dict[str, Any]], payload.get("data", [])):
        permission = str(item.get("permission") or "")
        status = str(item.get("status") or "")
        if permission and status == "granted":
            granted.append(permission)
        elif permission:
            declined.append(permission)
    return sorted(set(granted)), sorted(set(declined))


def _mask_identifier(value: str) -> str:
    return f"••••••{value[-4:]}" if len(value) > 4 else "••••"


def _safe_https_url(value: str | None) -> str | None:
    if not value or not value.startswith("https://"):
        return None
    return value
