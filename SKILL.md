---
name: vidgenAI
description: Use this skill whenever the user asks to download, extract, or convert video, audio (MP3/WAV), or GIF from a TikTok, Instagram, Snapchat, or YouTube URL.
---

# vidgenAI

CLI media downloader and converter for TikTok, Instagram, Snapchat, and YouTube. Outputs a single-line JSON object to `stdout` and progress logs to `stderr`.

## CLI Usage

```bash
python scripts/download.py "<URL>" --format {mp3,mp4,wav,gif} \
  [--out DIR] [--start SECONDS] [--duration SECONDS] \
  [--fps N] [--width PX] [--bitrate KBPS] \
  [--cookies FILE] [--name FILENAME]
```

Defaults: `--out ./downloads`, `--fps 12`, `--width 480`, `--bitrate 192`, `--duration 6` (GIF only).

## Examples

```bash
python scripts/download.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --format mp3
python scripts/download.py "https://vm.tiktok.com/ZM123456/" --format mp4 --out ./downloads
python scripts/download.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --format wav --start 10 --duration 15
python scripts/download.py "https://www.tiktok.com/@user/video/123" --format gif --start 2 --duration 5 --fps 12 --width 480
python scripts/download.py "https://www.instagram.com/reel/ABC123/" --format mp4 --cookies cookies.txt --name my_reel
```

## JSON Output

Read `stdout` only (progress logs go to `stderr`).

Success (exit code `0`):
```json
{"status":"ok","platform":"youtube","title":"Video Title","format":"mp3","filename":"Video_Title.mp3","path":"/absolute/path/Video_Title.mp3","mime":"audio/mpeg","size_bytes":2451200,"size_human":"2.3 MB"}
```

Error (non-zero exit code):
```json
{"status":"error","code":"PRIVATE_OR_LOGIN_REQUIRED","message":"Media is private or requires login. Retry with --cookies cookies.txt (Netscape format)."}
```

## Error Codes

| Code | Meaning | Suggested Fix |
| --- | --- | --- |
| `INVALID_URL` | Missing/malformed `http`/`https` URL | Ask user for a complete `http://` or `https://` URL |
| `UNSUPPORTED_PLATFORM` | Domain not in whitelist (`tiktok.com`, `vm.tiktok.com`, `instagram.com`, `snapchat.com`, `youtube.com`, `youtu.be`) | Inform user which 4 platforms are supported |
| `PRIVATE_OR_LOGIN_REQUIRED` | Content is private, age-restricted, or requires authentication | Ask user to supply Netscape-format cookies via `--cookies cookies.txt` |
| `FFMPEG_MISSING` | `ffmpeg` binary not found in `PATH` | Install `ffmpeg` (`brew install ffmpeg`, `sudo apt install ffmpeg`, or `winget install Gyan.FFmpeg`) |
| `DOWNLOAD_FAILED` | Extraction or network failure | Update `yt-dlp` (`pip install -U yt-dlp`) and verify URL is accessible |
| `CONVERSION_FAILED` | `ffmpeg` failed or invalid conversion option | Check `--start`/`--duration`/`--fps`/`--width`/`--bitrate` values or retry |

## Delivering the File to the User (Mandatory)

Never stop after printing JSON. Always deliver the file at `path` (guaranteed absolute and existing):

1. **Claude**: Copy `path` into `/mnt/user-data/outputs/<filename>` and call `present_files`.
2. **Agents with file/chat attachment (Gemini, Codex, Arena AI, etc.)**: Attach/present the file directly; if attachment is unavailable, provide the absolute `path` and `filename`.
3. **Agents without user filesystem access (DeepSeek, etc.)**: Return `filename`, `size_human`, absolute `path`, and a short command to open it (e.g. `open "<path>"` or `xdg-open "<path>"`).
4. **Final message**: Keep it to 1–3 concise lines containing only filename, format, size, and location. Do not narrate internal steps.
5. **Large files (> 25 MB / `size_bytes > 26214400`)**: Note the file size and offer a lighter alternative (`mp3` or a shorter/smaller `gif`).
6. **On error**: Explain `message` in plain language and give one concrete fix step.

## Limitations

- Single media item per URL (`noplaylist=True`).
- Public content or content the user is authorized to download only.
- Instagram and Snapchat frequently change and may require `--cookies`; success is not guaranteed.
- Update `yt-dlp` periodically (`pip install -U yt-dlp`) when downloads fail.
- Never log, echo, or commit cookie contents.
- The user is responsible for copyright compliance and platform Terms of Service.
