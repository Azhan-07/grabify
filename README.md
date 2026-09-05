
# 🎬 Grabify — Video & Audio Downloader

> **Download videos or extract audio from YouTube, Instagram, Facebook, TikTok & more — right from your browser or a sleek desktop app.**

Grabify is a lightweight, self-hosted media downloader built with **Flask**, **yt-dlp**, and **PyQt5**. Paste any supported link, choose your quality or bitrate, and download instantly. It ships as both a **web app** and a **desktop app** (PyQt wrapper), with async progress tracking and bot-detection handling.

---

## ✨ Features

- **Multi-platform support** — YouTube, Instagram, Facebook, TikTok, and everything else `yt-dlp` supports.
- **Video downloads** — choose from `best`, `1080p`, `720p`, `480p`, or `360p`.
- **Audio extraction** — convert to MP3 with bitrates of `64`, `128`, `192`, or `320 kbps`.
- **Live progress tracking** — real-time download percentage via the API.
- **Video info preview** — title, thumbnail, duration, view count, and platform before downloading.
- **Async downloads** — background threads keep the UI responsive for multiple downloads.
- **Automatic retry logic** — smart retries with backoff when YouTube bot detection kicks in.
- **Cookie support** — drop a `cookies.txt` file to bypass bot/age-restriction blocks.
- **Cleanup on exit** — temp thumbnails and stale downloads are cleaned automatically.
- **Deployable anywhere** — ready-made `Dockerfile` for Hugging Face Spaces / any Docker host.

---

## 🚀 Quick Start

### 1. Web App

```bash
# Install dependencies
pip install -r requirements.txt

# Optional: install FFmpeg for MP3 audio extraction
#   Windows: https://ffmpeg.org/download.html

# Run the server
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

### 2. Desktop App (PyQt5 wrapper)

```bash
pip install -r requirements.txt
python main.py
```

This launches the web UI inside a native PyQt window and opens the interface in your default browser too.

---

## 🐳 Run with Docker

```bash
docker build -t grabify .
docker run -p 7860:7860 grabify
```

Then visit **http://127.0.0.1:7860**. The image uses `ffmpeg` out of the box so audio extraction works immediately.

---

## ⚙️ Configuration

| Environment Variable | Default | Description |
| --- | --- | --- |
| `PORT` | `5000` (web) / `7860` (Docker) | Port the server listens on |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, etc.) |
| `GRABIFY_COOKIES_FILE` | `cookies.txt` | Path to a browser-cookies file for bot/age-restriction workarounds |

---

## 🧠 Bot Detection & Cookies

YouTube may block automated access. If you hit **"Sign in to confirm you're not a bot"**, Grabify retries automatically and reports a helpful message.

To resolve it permanently, export your browser cookies as **Netscape format** and save the file as `cookies.txt` in the project root (or point `GRABIFY_COOKIES_FILE` at it). Use a browser extension like *Get cookies.txt LOCALLY*, then `pip install yt-dlp[default]` to keep extractors up to date.

---

## 🔌 API Reference

All endpoints accept/return JSON.

### `POST /api/info`
Fetch metadata for a URL.

```bash
curl -X POST http://127.0.0.1:5000/api/info \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtube.com/watch?v=..."}'
```

**Response:** `title`, `thumbnail`, `duration`, `formatted_duration`, `view_count`, `formatted_views`, `platform`, `filesize`.

### `POST /api/download`
Start a download (non-blocking).

```bash
curl -X POST http://127.0.0.1:5000/api/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtube.com/watch?v=...", "quality": "720p", "audio_only": false, "audio_bitrate": 128}'
```

**Response:** `download_id` and `message`.

| Field | Values | Default |
| --- | --- | --- |
| `quality` | `best`, `1080p`, `720p`, `480p`, `360p` | `best` |
| `audio_only` | `true` / `false` | `false` |
| `audio_bitrate` | `64`, `128`, `192`, `320` | `128` |

### `GET /api/progress/<download_id>`
Poll download progress (`0`–`100`).

### `GET /api/status/<download_id>`
Check state — returns `downloading`, `complete` (with `filename`/`filepath`), or `error`.

### `GET /api/download-file/<filename>`
Download a finished file.

### `GET /api/health`
Health check — returns status, timestamp, and active download count.

---

## 📂 Project Structure

```
grabify/
├── app.py            # Flask server, routes, rate limiting
├── downloader.py     # yt-dlp wrapper, progress hooks, retry logic
├── config.py         # Paths, config, helpers (URL validation, formatting)
├── main.py           # PyQt5 desktop entry point
├── ui.py             # PyQt5 window / embedded web view
├── templates/
│   └── index.html    # Web UI
├── requirements.txt  # Full deps (incl. PyQt5 desktop)
├── requirements-hf.txt  # Server-only deps (Docker / HF Spaces)
└── Dockerfile
```

---

## 🛠️ Troubleshooting

- **MP3 extraction fails** → Make sure `ffmpeg` is installed and on your `PATH`.
- **Audio/video file not found after download** → Check the `downloads/` and `downloads/music/` folders; stale files are cleaned up hourly.
- **YouTube bot detection** → Follow the [cookies](#-bot-detection--cookies) section above.
- **Unsupported URL message** → Try updating `yt-dlp` (`pip install -U yt-dlp`); extractors change frequently.

---

## ⚠️ Disclaimer

Only download content you have the rights to access and use. Respect the terms of service of the platforms you download from and applicable copyright laws.

---

## 📄 License

This project is for personal and educational use. See the repository for license details.
