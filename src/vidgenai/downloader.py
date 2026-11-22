from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

import yt_dlp

from vidgenai.errors import DOWNLOAD_FAILED, PRIVATE_OR_LOGIN_REQUIRED, VidgenError
from vidgenai.formats import build_ydl_options

AUTH_ERROR_MARKERS: tuple[str, ...] = (
    "login required",
    "log in",
    "sign in",
    "private video",
    "is private",
    "private account",
    "cookies",
    "logged-in",
    "authentication",
    "age-restricted",
    "confirm your age",
    "members-only",
    "subscribers-only",
    "http error 401",
    "http error 403",
)

SOCIAL_LOGIN_MARKERS: tuple[str, ...] = (
    "empty media response",
    "requested content is not available",
    "rate-limit reached",
    "login",
)


@dataclass(frozen=True)
class DownloadResult:
    file_path: Path
    title: str


class StderrLogger:
    def debug(self, msg: str) -> None:
        if msg.startswith("[debug] "):
            return
        print(msg, file=sys.stderr)

    def info(self, msg: str) -> None:
        print(msg, file=sys.stderr)

    def warning(self, msg: str) -> None:
        print(msg, file=sys.stderr)

    def error(self, msg: str) -> None:
        print(msg, file=sys.stderr)


def emit_progress(data: dict[str, Any]) -> None:
    status = data.get("status")
    if status == "downloading":
        percent = str(data.get("_percent_str", "")).strip()
        if percent:
            print(f"Downloading: {percent}", file=sys.stderr)
    elif status == "finished":
        print("Download finished, processing output...", file=sys.stderr)


def is_auth_error(message: str, platform: str, has_cookies: bool) -> bool:
    lowered = message.lower()
    if any(marker in lowered for marker in AUTH_ERROR_MARKERS):
        return True
    if platform in {"instagram", "snapchat"} and not has_cookies:
        if any(marker in lowered for marker in SOCIAL_LOGIN_MARKERS):
            return True
    return False


def locate_downloaded_file(ydl: yt_dlp.YoutubeDL, info: dict[str, Any], temp_dir: Path) -> Path:
    requested = info.get("requested_downloads") or []
    for item in requested:
        filepath = item.get("filepath")
        if filepath and Path(filepath).is_file():
            return Path(filepath)
    prepared = Path(ydl.prepare_filename(info))
    if prepared.is_file():
        return prepared
    candidates = [
        path
        for path in sorted(temp_dir.iterdir())
        if path.is_file() and path.suffix.lower() not in {".part", ".ytdl"}
    ]
    if candidates:
        return candidates[0]
    raise VidgenError(DOWNLOAD_FAILED, "Downloaded media file could not be located.")


def download_media(
    url: str,
    platform: str,
    output_format: str,
    temp_dir: Path,
    cookies: Path | None = None,
) -> DownloadResult:
    if cookies is not None and not cookies.is_file():
        raise VidgenError(DOWNLOAD_FAILED, "Cookies file does not exist.")
    options = build_ydl_options(
        output_format=output_format,
        temp_dir=temp_dir,
        cookies=cookies,
        logger=StderrLogger(),
        progress_hook=emit_progress,
    )
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            if not isinstance(info, dict):
                raise VidgenError(DOWNLOAD_FAILED, "No media metadata returned for URL.")
            file_path = locate_downloaded_file(ydl, info, temp_dir)
            title = str(info.get("title") or info.get("id") or "media")
            return DownloadResult(file_path=file_path, title=title)
    except VidgenError:
        raise
    except Exception as exc:
        detail = str(exc)
        if is_auth_error(detail, platform, cookies is not None):
            raise VidgenError(
                PRIVATE_OR_LOGIN_REQUIRED,
                "Media is private or requires login. Retry with --cookies cookies.txt (Netscape format).",
            ) from exc
        raise VidgenError(
            DOWNLOAD_FAILED,
            f"Failed to download media: {detail}",
        ) from exc
