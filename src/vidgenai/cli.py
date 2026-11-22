import argparse
import json
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, NoReturn

from vidgenai.converter import convert_media, ensure_ffmpeg
from vidgenai.downloader import download_media
from vidgenai.errors import CONVERSION_FAILED, DOWNLOAD_FAILED, INVALID_URL, VidgenError
from vidgenai.formats import (
    DEFAULT_BITRATE,
    DEFAULT_FPS,
    DEFAULT_GIF_DURATION,
    DEFAULT_OUT_DIR,
    DEFAULT_WIDTH,
    MIME_TYPES,
    SUPPORTED_FORMATS,
    validate_format,
)
from vidgenai.platforms import detect_platform

ILLEGAL_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
WHITESPACE_RUN = re.compile(r"\s+")
UNDERSCORE_RUN = re.compile(r"_+")


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        code = INVALID_URL if "url" in message.lower() else CONVERSION_FAILED
        raise VidgenError(code, message)


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(prog="vidgenai")
    parser.add_argument("url")
    parser.add_argument("--format", required=True, choices=SUPPORTED_FORMATS)
    parser.add_argument("--out", default=DEFAULT_OUT_DIR)
    parser.add_argument("--start", type=float, default=None)
    parser.add_argument("--duration", type=float, default=None)
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS)
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--bitrate", type=int, default=DEFAULT_BITRATE)
    parser.add_argument("--cookies", default=None)
    parser.add_argument("--name", default=None)
    return parser


def sanitize_filename(raw_name: str, ext: str, max_length: int = 100) -> str:
    cleaned = raw_name.strip()
    suffix = f".{ext.lower()}"
    if cleaned.lower().endswith(suffix):
        cleaned = cleaned[: -len(suffix)]
    cleaned = cleaned.replace("..", "_")
    cleaned = ILLEGAL_FILENAME_CHARS.sub("_", cleaned)
    cleaned = WHITESPACE_RUN.sub("_", cleaned)
    cleaned = UNDERSCORE_RUN.sub("_", cleaned)
    cleaned = cleaned.strip("._")
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip("._")
    return cleaned or "media"


def resolve_output_path(out_dir: Path, raw_name: str, ext: str) -> Path:
    resolved_out = out_dir.resolve()
    resolved_out.mkdir(parents=True, exist_ok=True)
    stem = sanitize_filename(raw_name, ext)
    candidate = (resolved_out / f"{stem}.{ext}").resolve()
    counter = 1
    while candidate.exists():
        candidate = (resolved_out / f"{stem}_{counter}.{ext}").resolve()
        counter += 1
    if candidate.parent != resolved_out:
        raise VidgenError(DOWNLOAD_FAILED, "Resolved output path escapes output directory.")
    return candidate


def format_size(size_bytes: int) -> str:
    value = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            if unit == "B":
                return f"{int(value)} B"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size_bytes} B"


def validate_numeric_args(args: argparse.Namespace) -> None:
    if args.start is not None and args.start < 0:
        raise VidgenError(CONVERSION_FAILED, "--start must be >= 0.")
    if args.duration is not None and args.duration <= 0:
        raise VidgenError(CONVERSION_FAILED, "--duration must be > 0.")
    if args.fps <= 0:
        raise VidgenError(CONVERSION_FAILED, "--fps must be > 0.")
    if args.width <= 0:
        raise VidgenError(CONVERSION_FAILED, "--width must be > 0.")
    if args.bitrate <= 0:
        raise VidgenError(CONVERSION_FAILED, "--bitrate must be > 0.")


def execute(args: argparse.Namespace) -> dict[str, Any]:
    ffmpeg_bin = ensure_ffmpeg()
    platform = detect_platform(args.url)
    output_format = validate_format(args.format)
    validate_numeric_args(args)
    effective_duration = (
        DEFAULT_GIF_DURATION if output_format == "gif" and args.duration is None else args.duration
    )
    cookies = Path(args.cookies).expanduser().resolve() if args.cookies else None
    out_dir = Path(args.out)

    with tempfile.TemporaryDirectory() as tmp:
        temp_dir = Path(tmp)
        downloaded = download_media(
            url=args.url,
            platform=platform,
            output_format=output_format,
            temp_dir=temp_dir,
            cookies=cookies,
        )
        destination = resolve_output_path(out_dir, args.name or downloaded.title, output_format)
        final_path = convert_media(
            source=downloaded.file_path,
            destination=destination,
            output_format=output_format,
            ffmpeg_bin=ffmpeg_bin,
            start=args.start,
            duration=effective_duration,
            fps=args.fps,
            width=args.width,
            bitrate=args.bitrate,
        )

    resolved_path = final_path.resolve()
    size_bytes = resolved_path.stat().st_size
    return {
        "status": "ok",
        "platform": platform,
        "title": downloaded.title,
        "format": output_format,
        "filename": resolved_path.name,
        "path": str(resolved_path),
        "mime": MIME_TYPES[output_format],
        "size_bytes": size_bytes,
        "size_human": format_size(size_bytes),
    }


def main(argv: list[str] | None = None) -> int:
    try:
        parser = build_parser()
        args = parser.parse_args(argv)
        payload = execute(args)
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), file=sys.stdout)
        return 0
    except VidgenError as exc:
        print(json.dumps(exc.to_dict(), ensure_ascii=False, separators=(",", ":")), file=sys.stdout)
        return 1
    except Exception as exc:
        payload = {
            "status": "error",
            "code": DOWNLOAD_FAILED,
            "message": str(exc),
        }
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), file=sys.stdout)
        return 1
