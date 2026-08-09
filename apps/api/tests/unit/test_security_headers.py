import httpx
import pytest

from socialos.main import app


@pytest.mark.asyncio
async def test_api_responses_include_security_headers() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Permissions-Policy"] == (
        "camera=(), microphone=(), geolocation=(), payment=()"
    )
    assert len(response.headers["X-Request-ID"]) == 32


@pytest.mark.asyncio
async def test_valid_correlation_id_is_preserved() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health/live", headers={"X-Request-ID": "request-test-1234"})

    assert response.headers["X-Request-ID"] == "request-test-1234"
