import json
from pathlib import Path
from typing import Any

import pytest

from vidgenai.cli import build_parser, format_size, main, resolve_output_path, sanitize_filename
from vidgenai.downloader import DownloadResult, download_media
from vidgenai.errors import (
    CONVERSION_FAILED,
    DOWNLOAD_FAILED,
    FFMPEG_MISSING,
    INVALID_URL,
    PRIVATE_OR_LOGIN_REQUIRED,
    UNSUPPORTED_PLATFORM,
    VidgenError,
)


def test_parser_defaults() -> None:
    parser = build_parser()
    args = parser.parse_args(["https://youtu.be/abc", "--format", "gif"])
    assert args.out == "./downloads"
    assert args.fps == 12
    assert args.width == 480
    assert args.bitrate == 192
    assert args.duration is None
    assert args.start is None
    assert args.cookies is None
    assert args.name is None


def test_sanitize_filename_and_traversal(tmp_path: Path) -> None:
    assert sanitize_filename('My: "Video"/Test?*2026', "mp3") == "My_Video_Test_2026"
    assert sanitize_filename("clip.mp3", "mp3") == "clip"
    assert len(sanitize_filename("a" * 200, "mp4")) <= 100
    assert sanitize_filename("///...", "mp4") == "media"

    out_dir = tmp_path / "downloads"
    first = resolve_output_path(out_dir, "../../etc/passwd", "mp3")
    assert first.parent == out_dir.resolve()
    assert first.suffix == ".mp3"

    first.write_bytes(b"1")
    second = resolve_output_path(out_dir, "../../etc/passwd", "mp3")
    assert second.parent == out_dir.resolve()
    assert second.name != first.name
    assert second.stem.endswith("_1")


def test_format_size() -> None:
    assert format_size(512) == "512 B"
    assert format_size(2048) == "2.0 KB"
    assert format_size(3 * 1024 * 1024) == "3.0 MB"


def test_cli_success_mp3(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("vidgenai.cli.ensure_ffmpeg", lambda: "/usr/bin/ffmpeg")

    def fake_download(
        url: str,
        platform: str,
        output_format: str,
        temp_dir: Path,
        cookies: Path | None = None,
    ) -> DownloadResult:
        src = temp_dir / "raw.webm"
        src.write_bytes(b"audio-stream")
        return DownloadResult(file_path=src, title="Sample: Track/01")

    def fake_convert(
        source: Path,
        destination: Path,
        output_format: str,
        ffmpeg_bin: str,
        **kwargs: Any,
    ) -> Path:
        destination.write_bytes(b"x" * 4096)
        return destination

    monkeypatch.setattr("vidgenai.cli.download_media", fake_download)
    monkeypatch.setattr("vidgenai.cli.convert_media", fake_convert)

    exit_code = main(
        ["https://www.youtube.com/watch?v=abc123", "--format", "mp3", "--out", str(tmp_path)]
    )
    captured = capsys.readouterr()
    assert exit_code == 0
    lines = captured.out.strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["status"] == "ok"
    assert payload["platform"] == "youtube"
    assert payload["title"] == "Sample: Track/01"
    assert payload["format"] == "mp3"
    assert payload["mime"] == "audio/mpeg"
    assert payload["filename"] == "Sample_Track_01.mp3"
    assert Path(payload["path"]).is_absolute()
    assert Path(payload["path"]).is_file()
    assert payload["size_bytes"] == 4096
    assert payload["size_human"] == "4.0 KB"


def test_cli_gif_default_duration(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("vidgenai.cli.ensure_ffmpeg", lambda: "/usr/bin/ffmpeg")
    seen_kwargs: dict[str, Any] = {}

    def fake_download(
        url: str,
        platform: str,
        output_format: str,
        temp_dir: Path,
        cookies: Path | None = None,
    ) -> DownloadResult:
        src = temp_dir / "vid.mp4"
        src.write_bytes(b"video")
        return DownloadResult(file_path=src, title="Funny Clip")

    def fake_convert(
        source: Path,
        destination: Path,
        output_format: str,
        ffmpeg_bin: str,
        **kwargs: Any,
    ) -> Path:
        seen_kwargs.update(kwargs)
        destination.write_bytes(b"GIF89a")
        return destination

    monkeypatch.setattr("vidgenai.cli.download_media", fake_download)
    monkeypatch.setattr("vidgenai.cli.convert_media", fake_convert)

    exit_code = main(
        ["https://vm.tiktok.com/ZM123/", "--format", "gif", "--out", str(tmp_path)]
    )
    assert exit_code == 0
    assert seen_kwargs["duration"] == 6.0
    assert seen_kwargs["fps"] == 12
    assert seen_kwargs["width"] == 480
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["platform"] == "tiktok"
    assert payload["mime"] == "image/gif"


def test_cli_ffmpeg_missing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("vidgenai.converter.shutil.which", lambda _: None)
    exit_code = main(["https://youtu.be/abc", "--format", "mp3"])
    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["status"] == "error"
    assert payload["code"] == FFMPEG_MISSING


def test_cli_invalid_and_unsupported_urls(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("vidgenai.cli.ensure_ffmpeg", lambda: "/usr/bin/ffmpeg")

    assert main(["not-a-url", "--format", "mp4"]) == 1
    assert json.loads(capsys.readouterr().out.strip())["code"] == INVALID_URL

    assert main(["https://vimeo.com/12345", "--format", "mp4"]) == 1
    assert json.loads(capsys.readouterr().out.strip())["code"] == UNSUPPORTED_PLATFORM


def test_cli_private_login_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("vidgenai.cli.ensure_ffmpeg", lambda: "/usr/bin/ffmpeg")

    def fake_download(*args: Any, **kwargs: Any) -> DownloadResult:
        raise VidgenError(PRIVATE_OR_LOGIN_REQUIRED, "Login required")

    monkeypatch.setattr("vidgenai.cli.download_media", fake_download)

    exit_code = main(
        ["https://www.instagram.com/reel/abc/", "--format", "mp4", "--out", str(tmp_path)]
    )
    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["status"] == "error"
    assert payload["code"] == PRIVATE_OR_LOGIN_REQUIRED


def test_cli_conversion_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("vidgenai.cli.ensure_ffmpeg", lambda: "/usr/bin/ffmpeg")

    def fake_download(
        url: str,
        platform: str,
        output_format: str,
        temp_dir: Path,
        cookies: Path | None = None,
    ) -> DownloadResult:
        src = temp_dir / "raw.mp4"
        src.write_bytes(b"data")
        return DownloadResult(file_path=src, title="Clip")

    def fake_convert(*args: Any, **kwargs: Any) -> Path:
        raise VidgenError(CONVERSION_FAILED, "ffmpeg failed")

    monkeypatch.setattr("vidgenai.cli.download_media", fake_download)
    monkeypatch.setattr("vidgenai.cli.convert_media", fake_convert)

    exit_code = main(
        ["https://www.snapchat.com/spotlight/abc", "--format", "wav", "--out", str(tmp_path)]
    )
    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["code"] == CONVERSION_FAILED


def test_downloader_maps_instagram_login_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class FakeYDL:
        def __init__(self, opts: dict[str, Any]) -> None:
            self.opts = opts

        def __enter__(self) -> "FakeYDL":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def extract_info(self, url: str, download: bool = True) -> dict[str, Any]:
            raise RuntimeError("Instagram sent an empty media response. Login required.")

    monkeypatch.setattr("vidgenai.downloader.yt_dlp.YoutubeDL", FakeYDL)
    with pytest.raises(VidgenError) as exc_info:
        download_media(
            url="https://www.instagram.com/reel/abc/",
            platform="instagram",
            output_format="mp4",
            temp_dir=tmp_path,
            cookies=None,
        )
    assert exc_info.value.code == PRIVATE_OR_LOGIN_REQUIRED


def test_downloader_missing_cookies_file(tmp_path: Path) -> None:
    with pytest.raises(VidgenError) as exc_info:
        download_media(
            url="https://www.instagram.com/reel/abc/",
            platform="instagram",
            output_format="mp4",
            temp_dir=tmp_path,
            cookies=tmp_path / "missing.txt",
        )
    assert exc_info.value.code == DOWNLOAD_FAILED
