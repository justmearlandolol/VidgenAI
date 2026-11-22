from pathlib import Path
import shutil
import subprocess

from vidgenai.errors import CONVERSION_FAILED, FFMPEG_MISSING, VidgenError
from vidgenai.formats import DEFAULT_BITRATE, DEFAULT_FPS, DEFAULT_GIF_DURATION, DEFAULT_WIDTH


def ensure_ffmpeg() -> str:
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        raise VidgenError(
            FFMPEG_MISSING,
            "ffmpeg not found. Install via: brew install ffmpeg (macOS), sudo apt install ffmpeg (Linux), or winget install Gyan.FFmpeg (Windows).",
        )
    return ffmpeg_bin


def run_ffmpeg(ffmpeg_bin: str, args: list[str]) -> None:
    completed = subprocess.run(
        [ffmpeg_bin, "-y", *args],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr_lines = [line.strip() for line in completed.stderr.splitlines() if line.strip()]
        detail = stderr_lines[-1] if stderr_lines else f"exit code {completed.returncode}"
        raise VidgenError(CONVERSION_FAILED, f"ffmpeg failed: {detail}")


def build_trim_args(source: Path, start: float | None, duration: float | None) -> list[str]:
    args: list[str] = []
    if start is not None:
        args.extend(["-ss", str(start)])
    args.extend(["-i", str(source)])
    if duration is not None:
        args.extend(["-t", str(duration)])
    return args


def convert_media(
    source: Path,
    destination: Path,
    output_format: str,
    ffmpeg_bin: str,
    start: float | None = None,
    duration: float | None = None,
    fps: int = DEFAULT_FPS,
    width: int = DEFAULT_WIDTH,
    bitrate: int = DEFAULT_BITRATE,
) -> Path:
    if output_format == "mp4":
        if start is None and duration is None and source.suffix.lower() == ".mp4":
            shutil.move(str(source), str(destination))
        else:
            args = [
                *build_trim_args(source, start, duration),
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                str(destination),
            ]
            run_ffmpeg(ffmpeg_bin, args)
    elif output_format == "mp3":
        args = [
            *build_trim_args(source, start, duration),
            "-vn",
            "-c:a",
            "libmp3lame",
            "-b:a",
            f"{bitrate}k",
            str(destination),
        ]
        run_ffmpeg(ffmpeg_bin, args)
    elif output_format == "wav":
        args = [
            *build_trim_args(source, start, duration),
            "-vn",
            "-acodec",
            "pcm_s16le",
            str(destination),
        ]
        run_ffmpeg(ffmpeg_bin, args)
    elif output_format == "gif":
        gif_duration = DEFAULT_GIF_DURATION if duration is None else duration
        filter_graph = (
            f"fps={fps},scale={width}:-1:flags=lanczos,"
            "split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"
        )
        args = [
            *build_trim_args(source, start, gif_duration),
            "-vf",
            filter_graph,
            "-loop",
            "0",
            str(destination),
        ]
        run_ffmpeg(ffmpeg_bin, args)
    else:
        raise VidgenError(CONVERSION_FAILED, f"Unsupported output format: {output_format}")

    if not destination.is_file():
        raise VidgenError(CONVERSION_FAILED, "Expected output file was not created.")
    return destination
