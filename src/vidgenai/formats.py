from collections.abc import Callable
from pathlib import Path
from typing import Any

from vidgenai.errors import CONVERSION_FAILED, VidgenError

SUPPORTED_FORMATS: tuple[str, ...] = ("mp3", "mp4", "wav", "gif")

MIME_TYPES: dict[str, str] = {
    "mp3": "audio/mpeg",
    "mp4": "video/mp4",
    "wav": "audio/wav",
    "gif": "image/gif",
}

DEFAULT_OUT_DIR = "./downloads"
DEFAULT_FPS = 12
DEFAULT_WIDTH = 480
DEFAULT_GIF_DURATION = 6.0
DEFAULT_BITRATE = 192


def validate_format(output_format: str) -> str:
    normalized = output_format.strip().lower()
    if normalized not in SUPPORTED_FORMATS:
        raise VidgenError(
            CONVERSION_FAILED,
            f"Unsupported format '{output_format}'. Choose from: {', '.join(SUPPORTED_FORMATS)}.",
        )
    return normalized


def build_ydl_options(
    output_format: str,
    temp_dir: Path,
    cookies: Path | None = None,
    logger: object | None = None,
    progress_hook: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    fmt = validate_format(output_format)
    options: dict[str, Any] = {
        "noplaylist": True,
        "quiet": True,
        "no_warnings": False,
        "noprogress": True,
        "outtmpl": str(temp_dir / "%(id)s.%(ext)s"),
    }
    if fmt == "mp4":
        options["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
        options["merge_output_format"] = "mp4"
    elif fmt in {"mp3", "wav"}:
        options["format"] = "bestaudio/best"
    elif fmt == "gif":
        options["format"] = "bestvideo[ext=mp4]/best[ext=mp4]/best"
    if cookies is not None:
        options["cookiefile"] = str(cookies)
    if logger is not None:
        options["logger"] = logger
    if progress_hook is not None:
        options["progress_hooks"] = [progress_hook]
    return options
