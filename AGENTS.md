# AGENTS.md — vidgenAI

Instructions for AI agents (Codex, Gemini, DeepSeek, Arena AI, Claude, etc.) operating `vidgenAI`.

## Setup

```bash
pip install -r requirements.txt
```

Requires Python 3.10+ and `ffmpeg` available on `PATH`.

## Invocation

```bash
python scripts/download.py "<URL>" --format {mp3,mp4,wav,gif} \
  [--out DIR] [--start SECONDS] [--duration SECONDS] \
  [--fps N] [--width PX] [--bitrate KBPS] \
  [--cookies FILE] [--name FILENAME]
```

Defaults: `--out ./downloads`, `--fps 12`, `--width 480`, `--bitrate 192`, `--duration 6` (GIF only).

Examples:
```bash
python scripts/download.py "https://youtu.be/dQw4w9WgXcQ" --format mp3
python scripts/download.py "https://www.tiktok.com/@user/video/123" --format gif --start 3 --duration 5
python scripts/download.py "https://www.instagram.com/reel/ABC123/" --format mp4 --cookies cookies.txt
```

## Parsing Output

- **stdout**: Always a single-line JSON object. Parse `stdout` only.
- **stderr**: Progress and diagnostic logs. Do not parse `stderr` as JSON.
- **Exit code**: `0` on `status == "ok"`, non-zero on `status == "error"`.

Success fields: `status`, `platform`, `title`, `format`, `filename`, `path` (absolute, file exists), `mime`, `size_bytes`, `size_human`.
Error fields: `status`, `code`, `message`.

Error codes: `INVALID_URL`, `UNSUPPORTED_PLATFORM`, `PRIVATE_OR_LOGIN_REQUIRED`, `FFMPEG_MISSING`, `DOWNLOAD_FAILED`, `CONVERSION_FAILED`.

## File Delivery Rules (Mandatory)

After `status == "ok"`, deliver the actual file to the user instead of printing raw JSON:

- **Claude**: Copy `path` to `/mnt/user-data/outputs/<filename>`, then call `present_files`.
- **Agents with file attachment tools (Gemini, Codex, Arena AI, etc.)**: Attach or present the file directly (e.g., `present_file`). If attachment is not supported, share the absolute `path` and `filename`.
- **Agents without user filesystem access (DeepSeek, etc.)**: Share `filename`, `size_human`, absolute `path`, and a short command to open it (`open "<path>"` on macOS, `xdg-open "<path>"` on Linux, `start "" "<path>"` on Windows).
- **Response length**: 1–3 lines only — filename, format, size, and location. Omit process narration.
- **Large files (> 25 MB)**: Alert the user and offer a smaller format (`mp3` or a shorter `gif`).
- **On error**: State `message` simply and suggest one fix (`--cookies cookies.txt`, `pip install -U yt-dlp`, or installing `ffmpeg`).

## Constraints & Security

- Downloads a single item per URL (`noplaylist=True`).
- Never inspect, log, print, or store the contents of `--cookies` files.
- Public or user-authorized content only. Instagram and Snapchat may require cookies and are not guaranteed to succeed.
- Users are responsible for copyright and platform Terms of Service.
