import pytest

from socialos.application.social.use_cases import _validated_image_content


def test_accepts_real_png_and_jpeg_signatures() -> None:
    assert (
        _validated_image_content("image.png", "image/png", b"\x89PNG\r\n\x1a\nbody") == "image/png"
    )
    assert _validated_image_content("image.jpeg", "image/jpeg", b"\xff\xd8\xffbody") == "image/jpeg"


@pytest.mark.parametrize(
    ("filename", "content_type", "content", "message"),
    [
        ("image.png", "image/png", b"", "empty"),
        ("image.png", "image/png", b"not-png", "does not match"),
        ("image.jpg", "image/png", b"\x89PNG\r\n\x1a\n", "extension"),
        ("../../token.svg", "image/svg+xml", b"<svg/>", "Only JPEG and PNG"),
    ],
)
def test_rejects_empty_spoofed_or_unsupported_images(
    filename: str, content_type: str, content: bytes, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        _validated_image_content(filename, content_type, content)
