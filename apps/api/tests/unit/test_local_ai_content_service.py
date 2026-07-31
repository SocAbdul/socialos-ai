import pytest

from socialos.domain.social import Platform
from socialos.infrastructure.ai.content_service import LocalAIContentService


@pytest.mark.asyncio
async def test_local_adaptation_preserves_spanish() -> None:
    service = LocalAIContentService()

    result, _, cost, _ = await service.adapt_for_platform(
        "Kinetic Mobiles ofrece reparaciones rápidas para profesionales en Valencia.",
        Platform.INSTAGRAM,
    )

    assert "Pensado para el feed" in result
    assert "Built for the feed" not in result
    assert cost == "0.000000"


@pytest.mark.asyncio
async def test_local_adaptation_preserves_english() -> None:
    service = LocalAIContentService()

    result, _, cost, _ = await service.adapt_for_platform(
        "Kinetic Mobiles offers same-day repairs for busy professionals.",
        Platform.FACEBOOK,
    )

    assert "A concise update for our community." in result
    assert "Una actualización" not in result
    assert cost == "0.000000"
