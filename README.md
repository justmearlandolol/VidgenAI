# vidgenAI

CLI skill for AI agents (Claude, Gemini, DeepSeek, Codex, Arena AI, etc.) to download and convert media from TikTok, Instagram, Snapchat, and YouTube into MP3, MP4, WAV, or GIF with single-line JSON output.

## Supported Platforms

- **TikTok**: `tiktok.com`, `vm.tiktok.com`
- **Instagram**: `instagram.com`
- **Snapchat**: `snapchat.com`
- **YouTube**: `youtube.com`, `youtu.be`

URLs outside this whitelist are rejected.

## Installation

### Prerequisites

- Python 3.10+
- `ffmpeg` installed on `PATH`:
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - Windows: `winget install Gyan.FFmpeg`

### Python Dependencies

```bash
pip install -e ".[dev]"
```

Or using `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Usage

```bash
python scripts/download.py "<URL>" --format {mp3,mp4,wav,gif} \
  [--out DIR] [--start SECONDS] [--duration SECONDS] \
  [--fps N] [--width PX] [--bitrate KBPS] \
  [--cookies FILE] [--name FILENAME]
```

After `pip install -e .`, the console entry point `vidgenai` is also available.

### Options

| Flag | Default | Description |
| --- | --- | --- |
| `--format` | *(required)* | Output format: `mp3`, `mp4`, `wav`, or `gif` |
| `--out` | `./downloads` | Output directory |
| `--start` | `None` | Start offset in seconds |
| `--duration` | `6` (for `gif`), `None` otherwise | Clip duration in seconds |
| `--fps` | `12` | GIF frame rate |
| `--width` | `480` | GIF width in pixels (aspect ratio preserved) |
| `--bitrate` | `192` | MP3 bitrate in kbps |
| `--cookies` | `None` | Path to Netscape-format `cookies.txt` |
| `--name` | Video title | Custom output filename (sanitized, overwrite-safe) |

### Examples

Download best MP4 (video + audio merged):
```bash
python scripts/download.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --format mp4
```

Extract 192k MP3 audio:
```bash
python scripts/download.py "https://vm.tiktok.com/ZM123456/" --format mp3
```

Extract 16-bit PCM WAV clip:
```bash
python scripts/download.py "https://youtu.be/dQw4w9WgXcQ" --format wav --start 10 --duration 20
```

Create palette-optimized GIF:
```bash
python scripts/download.py "https://www.tiktok.com/@user/video/123" --format gif --start 2 --duration 6 --fps 12 --width 480
```

Download login-gated Instagram or Snapchat media with cookies:
```bash
python scripts/download.py "https://www.instagram.com/reel/ABC123/" --format mp4 --cookies cookies.txt
```

## JSON Output

Progress logs are written to `stderr`. Final results are always a single-line JSON object on `stdout`.

Success (exit code `0`):
```json
{"status":"ok","platform":"youtube","title":"Example","format":"mp3","filename":"Example.mp3","path":"/abs/path/downloads/Example.mp3","mime":"audio/mpeg","size_bytes":1048576,"size_human":"1.0 MB"}
```

Failure (non-zero exit code):
```json
{"status":"error","code":"FFMPEG_MISSING","message":"ffmpeg not found. Install via: brew install ffmpeg (macOS), sudo apt install ffmpeg (Linux), or winget install Gyan.FFmpeg (Windows)."}
```

### Error Codes

- `INVALID_URL`
- `UNSUPPORTED_PLATFORM`
- `PRIVATE_OR_LOGIN_REQUIRED`
- `FFMPEG_MISSING`
- `DOWNLOAD_FAILED`
- `CONVERSION_FAILED`

## Testing

```bash
pytest
```

All tests run offline using mocks.

## Limitations & Legal Disclaimer

- Downloads a single item per URL (`noplaylist=True`); playlists and full profiles are not downloaded.
- Instagram and Snapchat frequently change their endpoints and may require Netscape-format cookies (`--cookies`); download success is not guaranteed.
- Keep `yt-dlp` updated (`pip install -U yt-dlp`) if extraction fails.
