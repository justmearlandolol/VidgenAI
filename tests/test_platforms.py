import pytest

from vidgenai.errors import INVALID_URL, UNSUPPORTED_PLATFORM, VidgenError
from vidgenai.platforms import detect_platform


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://tiktok.com/@user/video/123", "tiktok"),
        ("https://www.tiktok.com/@user/video/123", "tiktok"),
        ("https://vm.tiktok.com/ZM123456/", "tiktok"),
        ("https://instagram.com/reel/ABC123/", "instagram"),
        ("https://www.instagram.com/p/ABC123/", "instagram"),
        ("https://snapchat.com/spotlight/W7_EDlXWTBiXAEEniNoMPwAAY", "snapchat"),
        ("https://www.snapchat.com/t/abc123", "snapchat"),
        ("https://youtube.com/watch?v=dQw4w9WgXcQ", "youtube"),
        ("https://www.youtube.com/shorts/abc123", "youtube"),
        ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "youtube"),
        ("https://youtu.be/dQw4w9WgXcQ", "youtube"),
        ("http://youtu.be/dQw4w9WgXcQ", "youtube"),
    ],
)
def test_detect_platform_supported(url: str, expected: str) -> None:
    assert detect_platform(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "",
        "   ",
        "not-a-url",
        "ftp://youtube.com/watch?v=1",
        "javascript:alert(1)",
        "https://",
        "https://youtube.com/watch?v=1 extra",
    ],
)
def test_detect_platform_invalid_url(url: str) -> None:
    with pytest.raises(VidgenError) as exc_info:
        detect_platform(url)
    assert exc_info.value.code == INVALID_URL


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/video",
        "https://vimeo.com/123456",
        "https://evil-tiktok.com/@user/video/123",
        "https://tiktok.com.evil.com/@user/video/123",
        "https://notyoutube.com/watch?v=1",
    ],
)
def test_detect_platform_unsupported(url: str) -> None:
    with pytest.raises(VidgenError) as exc_info:
        detect_platform(url)
    assert exc_info.value.code == UNSUPPORTED_PLATFORM
