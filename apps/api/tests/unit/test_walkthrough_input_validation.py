from uuid import uuid4

import pytest
from pydantic import ValidationError

from socialos.domain.social import DomainValidationError, MediaAsset, MediaType
from socialos.presentation.api.social import (
    AdaptContentRequest,
    CreateBrandProfileRequest,
    CreateCampaignRequest,
    CreateContentItemRequest,
    RegisterMediaAssetRequest,
)


@pytest.mark.parametrize("value", ["", "   "])
def test_required_walkthrough_values_reject_empty_and_whitespace(value: str) -> None:
    with pytest.raises(ValidationError):
        CreateBrandProfileRequest(name=value, voice="Helpful", audience="Local families")
    with pytest.raises(ValidationError):
        CreateBrandProfileRequest(name="Kinetic", voice=value, audience="Local families")
    with pytest.raises(ValidationError):
        CreateCampaignRequest(brand_profile_id=uuid4(), name=value)
    with pytest.raises(ValidationError):
        CreateContentItemRequest(campaign_id=uuid4(), body=value)
    with pytest.raises(ValidationError):
        AdaptContentRequest(text=value, platform="instagram")


@pytest.mark.parametrize("url", ["not-a-valid-url", "ftp://example.com/image.jpg"])
def test_media_url_rejects_invalid_or_unsupported_urls(url: str) -> None:
    with pytest.raises(ValidationError):
        RegisterMediaAssetRequest(
            media_type="image",
            storage_url=url,
            content_type="image/jpeg",
            checksum_sha256="a" * 64,
        )
    with pytest.raises(DomainValidationError):
        MediaAsset(
            workspace_id=uuid4(),
            uploader_id="user_local",
            media_type=MediaType.IMAGE,
            storage_url=url,
            content_type="image/jpeg",
            checksum_sha256="a" * 64,
        )


def test_validation_failure_constructs_no_domain_entities() -> None:
    created: list[object] = []
    with pytest.raises(ValidationError):
        request = RegisterMediaAssetRequest(
            media_type="image",
            storage_url="not-a-valid-url",
            content_type="image/jpeg",
            checksum_sha256="a" * 64,
        )
        created.append(request)

    assert created == []
