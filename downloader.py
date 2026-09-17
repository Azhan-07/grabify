import logging
import os
import time
import traceback

import yt_dlp

from config import DOWNLOAD_FOLDER, MUSIC_FOLDER, COOKIES_FILE, get_ffmpeg_path

logger = logging.getLogger(__name__)

download_progress = {}
download_complete = {}
active_downloads = {}

MAX_RETRIES = 2

BOT_DETECTION_ERRORS = [
    "Sign in to confirm",
    "bot",
    "unusual traffic",
    "verify you are human",
    "captcha",
    "HTTP Error 403",
    "unable to download",
    "forbidden",
    "too many requests",
]


def _is_bot_detection(error_msg):
    if not error_msg:
        return False
    lower = error_msg.lower()
    return any(phrase in lower for phrase in BOT_DETECTION_ERRORS)


def _get_error_message(exc):
    msg = str(exc)
    if _is_bot_detection(msg):
        return (
            "YouTube is blocking automated downloads (bot detection). "
            "Try placing a cookies.txt file in the project root, or "
            "export cookies from your browser and save as cookies.txt."
        )
    if "Video unavailable" in msg or "Private video" in msg:
        return "This video is unavailable or private."
    if "is not a valid URL" in msg:
        return "The provided URL is not valid."
    if " Unsupported URL" in msg:
        return "This URL is not supported."
    return "An error occurred while processing your request. Please try again."


def _build_ydl_opts(url, quality, download_id, audio_only=False, audio_bitrate=128, outdir=None):
    if outdir:
        video_dir = outdir
        music_dir = os.path.join(outdir, "music")
        os.makedirs(outdir, exist_ok=True)
        os.makedirs(music_dir, exist_ok=True)
    else:
        video_dir = DOWNLOAD_FOLDER
        music_dir = MUSIC_FOLDER

    if audio_only:
        format_code = "bestaudio/best"
        outtmpl = os.path.join(music_dir, "%(title)s.%(ext)s")
        postprocessors = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": str(audio_bitrate),
            }
        ]
    else:
        if quality == "best":
            format_code = "bestvideo+bestaudio/best"
        else:
            quality_num = quality.replace("p", "")
            format_code = f"bestvideo[height<={quality_num}]+bestaudio/best"
        outtmpl = os.path.join(video_dir, "%(title)s.%(ext)s")
        postprocessors = []

    opts = {
        "format": format_code,
        "outtmpl": outtmpl,
        "progress_hooks": [],
        "quiet": True,
        "noplaylist": True,
        "postprocessors": postprocessors,
        "ignoreerrors": False,
        "no_warnings": True,
        "extract_flat": False,
        "concurrent_fragment_downloads": 4,
        "socket_timeout": 30,
        "retries": 5,
        "fragment_retries": 5,
    }

    if COOKIES_FILE and os.path.isfile(COOKIES_FILE):
        opts["cookiefile"] = COOKIES_FILE
        logger.info("Using cookies from %s", COOKIES_FILE)

    ffmpeg_path = get_ffmpeg_path()
    if ffmpeg_path:
        opts["ffmpeg_location"] = ffmpeg_path
        logger.info("Using ffmpeg binary at %s", ffmpeg_path)
    else:
        logger.warning("ffmpeg not found - MP3 extraction and stream merging will be unavailable")

    return opts


class DownloadHandler:
    def __init__(self):
        self.current_download = None
        self.download_id = None

    def progress_hook(self, d):
        try:
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded = d.get("downloaded_bytes", 0)
                if total and total > 0:
                    percent = (downloaded / total) * 100
                    download_progress[self.download_id] = min(percent, 99.9)
        except Exception:
            logger.debug("Progress hook error", exc_info=True)

    def download_video(self, url, quality, download_id, audio_only=False, audio_bitrate=128):
        self.download_id = download_id
        download_progress[download_id] = 0
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                ydl_opts = _build_ydl_opts(url, quality, download_id, audio_only, audio_bitrate)
                ydl_opts["progress_hooks"] = [self.progress_hook]

                logger.info("Download attempt %d/%d for %s", attempt, MAX_RETRIES, url)

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)

                    if info is None:
                        raise RuntimeError(
                            "Could not extract video info. "
                            "The video may be private, age-restricted, or unavailable."
                        )

                    if isinstance(info, list):
                        info = info[0] if info else None
                        if info is None:
                            raise RuntimeError("No video data returned.")

                    if audio_only:
                        title = info.get("title", "audio")
                        if title:
                            title = title.replace("/", "_").replace("\\", "_")
                        filename = os.path.join(MUSIC_FOLDER, f"{title}.mp3")
                    else:
                        filename = ydl.prepare_filename(info)
                        if not os.path.exists(filename):
                            base_name = os.path.splitext(filename)[0]
                            for ext in [".mp4", ".mkv", ".webm", ".mp3"]:
                                test_path = base_name + ext
                                if os.path.exists(test_path):
                                    filename = test_path
                                    break

                    if not os.path.exists(filename):
                        raise RuntimeError(
                            "Download completed but the file could not be found on disk."
                        )

                    download_complete[download_id] = {
                        "success": True,
                        "filename": os.path.basename(filename),
                        "filepath": filename,
                    }
                    download_progress[download_id] = 100
                    logger.info("Download complete: %s", filename)
                    return

            except Exception as e:
                last_error = e
                logger.warning(
                    "Download attempt %d failed: %s\n%s",
                    attempt,
                    str(e),
                    traceback.format_exc(),
                )
                if attempt < MAX_RETRIES and _is_bot_detection(str(e)):
                    logger.info("Bot detected, retrying after delay...")
                    time.sleep(2 * attempt)
                    continue
                if attempt < MAX_RETRIES:
                    continue
                break

        error_msg = _get_error_message(last_error)
        download_complete[download_id] = {
            "success": False,
            "error": error_msg,
        }
        logger.error("Download failed after %d attempts: %s", MAX_RETRIES, last_error)


class DownloadError(Exception):
    pass


def download_file_sync(url, quality, audio_only=False, audio_bitrate=128, outdir=None):
    """Synchronous download for serverless runtimes.

    Downloads the media into ``outdir`` (or the configured download
    folders when ``outdir`` is None) and returns the final path on disk.
    Raises :class:`DownloadError` with a user-friendly message on failure.
    """
    if outdir:
        os.makedirs(outdir, exist_ok=True)

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            ydl_opts = _build_ydl_opts(
                url, quality, "sync", audio_only, audio_bitrate, outdir=outdir
            )
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

                if info is None:
                    raise RuntimeError("No video data returned.")
                if isinstance(info, list):
                    info = info[0] if info else None
                    if info is None:
                        raise RuntimeError("No video data returned.")

                if audio_only:
                    title = info.get("title", "audio")
                    if title:
                        title = title.replace("/", "_").replace("\\", "_")
                    music_dir = os.path.join(outdir, "music") if outdir else MUSIC_FOLDER
                    filename = os.path.join(music_dir, f"{title}.mp3")
                else:
                    filename = ydl.prepare_filename(info)
                    if not os.path.exists(filename):
                        base_name = os.path.splitext(filename)[0]
                        for ext in [".mp4", ".mkv", ".webm", ".mp3", ".m4a"]:
                            test_path = base_name + ext
                            if os.path.exists(test_path):
                                filename = test_path
                                break

                if not os.path.exists(filename):
                    raise RuntimeError(
                        "Download completed but the file could not be found on disk."
                    )

                logger.info("Sync download complete: %s", filename)
                return filename

        except Exception as e:
            last_error = e
            logger.warning("Sync download attempt %d failed: %s", attempt, e)
            if attempt < MAX_RETRIES:
                time.sleep(attempt)
                continue
            break

    raise DownloadError(_get_error_message(last_error))


def cleanup_old_downloads():
    current_time = time.time()
    to_remove = []
    for dl_id, info in active_downloads.items():
        if current_time - info["start_time"] > 3600:
            to_remove.append(dl_id)

    for dl_id in to_remove:
        active_downloads.pop(dl_id, None)
        download_progress.pop(dl_id, None)
        download_complete.pop(dl_id, None)
