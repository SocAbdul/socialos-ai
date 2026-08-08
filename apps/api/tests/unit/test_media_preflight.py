from uuid import uuid4

import httpx
import pytest

from socialos.config import Settings
from socialos.domain.social import MediaAsset, MediaType
from socialos.infrastructure.storage.media import HTTPMediaPreflightService


def media(url: str = "https://preview.example.test/media/opaque.png") -> MediaAsset:
    return MediaAsset(
        workspace_id=uuid4(),
        uploader_id="user_1",
        media_type=MediaType.IMAGE,
        storage_url=url,
        content_type="image/png",
        checksum_sha256="a" * 64,
        storage_key="opaque.png",
        size_bytes=68,
    )


@pytest.mark.asyncio
async def test_preflight_accepts_matching_public_https_media() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, headers={"content-type": "image/png", "content-length": "68"}, request=request
        )
    )
    service = HTTPMediaPreflightService(
        Settings(media_public_base_url="https://preview.example.test/media"), transport
    )

    await service.validate(media())


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("url", "status", "content_type", "length", "message"),
    [
        ("http://preview.example.test/media/x.png", 200, "image/png", "68", "approved"),
        ("https://evil.example.test/x.png", 200, "image/png", "68", "approved"),
        ("https://preview.example.test/media/x.png", 404, "image/png", "68", "accessible"),
        ("https://preview.example.test/media/x.png", 200, "text/html", "68", "Content-Type"),
        ("https://preview.example.test/media/x.png", 200, "image/png", "99", "size"),
    ],
)
async def test_preflight_rejects_inaccessible_or_mismatched_media(
    url: str, status: int, content_type: str, length: str, message: str
) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            status,
            headers={"content-type": content_type, "content-length": length},
            request=request,
        )
    )
    service = HTTPMediaPreflightService(
        Settings(media_public_base_url="https://preview.example.test/media"), transport
    )

    with pytest.raises(ValueError, match=message):
        await service.validate(media(url))
