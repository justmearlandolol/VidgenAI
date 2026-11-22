from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from vidgenai.converter import convert_media, ensure_ffmpeg
from vidgenai.errors import CONVERSION_FAILED, FFMPEG_MISSING, VidgenError
from vidgenai.formats import MIME_TYPES, SUPPORTED_FORMATS, build_ydl_options, validate_format


@pytest.mark.parametrize("fmt", SUPPORTED_FORMATS)
def test_validate_format_valid(fmt: str) -> None:
    assert validate_format(fmt) == fmt
    assert validate_format(fmt.upper()) == fmt
    assert fmt in MIME_TYPES


def test_validate_format_invalid() -> None:
    with pytest.raises(VidgenError) as exc_info:
        validate_format("avi")
    assert exc_info.value.code == CONVERSION_FAILED


def test_build_ydl_options_mp4(tmp_path: Path) -> None:
    opts = build_ydl_options("mp4", tmp_path)
    assert opts["noplaylist"] is True
    assert opts["merge_output_format"] == "mp4"
    assert "cookiefile" not in opts


def test_build_ydl_options_audio_and_cookies(tmp_path: Path) -> None:
    cookies = tmp_path / "cookies.txt"
    opts_mp3 = build_ydl_options("mp3", tmp_path, cookies=cookies)
    opts_wav = build_ydl_options("wav", tmp_path)
    assert opts_mp3["noplaylist"] is True
    assert opts_mp3["format"] == "bestaudio/best"
    assert opts_mp3["cookiefile"] == str(cookies)
    assert opts_wav["format"] == "bestaudio/best"
    assert "merge_output_format" not in opts_mp3


def test_build_ydl_options_gif(tmp_path: Path) -> None:
    opts = build_ydl_options("gif", tmp_path)
    assert opts["noplaylist"] is True
    assert "bestvideo" in opts["format"]


def test_ensure_ffmpeg_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("vidgenai.converter.shutil.which", lambda _: None)
    with pytest.raises(VidgenError) as exc_info:
        ensure_ffmpeg()
    assert exc_info.value.code == FFMPEG_MISSING


def test_convert_media_mp3_and_wav(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "source.webm"
    source.write_bytes(b"audio")
    recorded: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> SimpleNamespace:
        recorded.append((cmd, kwargs))
        Path(cmd[-1]).write_bytes(b"converted")
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr("vidgenai.converter.subprocess.run", fake_run)

    mp3_out = tmp_path / "out.mp3"
    convert_media(source, mp3_out, "mp3", "/usr/bin/ffmpeg", start=1.5, duration=10, bitrate=192)
    mp3_cmd, mp3_kwargs = recorded[0]
    assert mp3_kwargs.get("shell") is not True
    assert "libmp3lame" in mp3_cmd
    assert "192k" in mp3_cmd
    assert "-ss" in mp3_cmd and "-t" in mp3_cmd

    wav_out = tmp_path / "out.wav"
    convert_media(source, wav_out, "wav", "/usr/bin/ffmpeg")
    wav_cmd, _ = recorded[1]
    assert "pcm_s16le" in wav_cmd


def test_convert_media_gif_uses_palette(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"video")
    captured: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> SimpleNamespace:
        captured.append(cmd)
        Path(cmd[-1]).write_bytes(b"GIF89a")
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr("vidgenai.converter.subprocess.run", fake_run)
    gif_out = tmp_path / "out.gif"
    convert_media(source, gif_out, "gif", "/usr/bin/ffmpeg", start=2, duration=5, fps=15, width=320)

    cmd = captured[0]
    vf_value = cmd[cmd.index("-vf") + 1]
    assert "fps=15" in vf_value
    assert "scale=320:-1:flags=lanczos" in vf_value
    assert "palettegen" in vf_value
    assert "paletteuse" in vf_value
    assert cmd[cmd.index("-ss") + 1] == "2"
    assert cmd[cmd.index("-t") + 1] == "5"


def test_convert_media_mp4_direct_move(tmp_path: Path) -> None:
    source = tmp_path / "clip.mp4"
    source.write_bytes(b"mp4data")
    dest = tmp_path / "final.mp4"
    result = convert_media(source, dest, "mp4", "/usr/bin/ffmpeg")
    assert result == dest
    assert dest.read_bytes() == b"mp4data"


def test_convert_media_ffmpeg_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"data")
    fake = MagicMock(return_value=SimpleNamespace(returncode=1, stderr="Invalid data found"))
    monkeypatch.setattr("vidgenai.converter.subprocess.run", fake)
    with pytest.raises(VidgenError) as exc_info:
        convert_media(source, tmp_path / "out.mp3", "mp3", "/usr/bin/ffmpeg")
    assert exc_info.value.code == CONVERSION_FAILED
