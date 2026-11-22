from urllib.parse import urlparse

from vidgenai.errors import INVALID_URL, UNSUPPORTED_PLATFORM, VidgenError

PLATFORM_DOMAINS: dict[str, str] = {
    "tiktok.com": "tiktok",
    "vm.tiktok.com": "tiktok",
    "instagram.com": "instagram",
    "snapchat.com": "snapchat",
    "youtube.com": "youtube",
    "youtu.be": "youtube",
}


def detect_platform(url: str) -> str:
    if not isinstance(url, str):
        raise VidgenError(INVALID_URL, "URL must be a non-empty string.")
    cleaned = url.strip()
    if not cleaned or any(ch.isspace() for ch in cleaned):
        raise VidgenError(INVALID_URL, "Invalid URL format.")
    parsed = urlparse(cleaned)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise VidgenError(INVALID_URL, "URL must use http or https with a valid domain.")
    hostname = parsed.hostname.lower().rstrip(".")
    for domain, platform in PLATFORM_DOMAINS.items():
        if hostname == domain or hostname.endswith(f".{domain}"):
            return platform
    raise VidgenError(
        UNSUPPORTED_PLATFORM,
        f"Unsupported domain '{hostname}'. Supported: tiktok.com, vm.tiktok.com, instagram.com, snapchat.com, youtube.com, youtu.be.",
    )
