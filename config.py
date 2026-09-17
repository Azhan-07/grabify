import logging
import os
import shutil
from datetime import timedelta

SERVERLESS = bool(
    os.environ.get("VERCEL")
    or os.environ.get("VERCEL_ENV")
    or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
)

BASE_DIR = "/tmp" if SERVERLESS else os.getcwd()
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, "downloads")
MUSIC_FOLDER = os.path.join(DOWNLOAD_FOLDER, "music")
COOKIES_FILE = os.environ.get("GRABIFY_COOKIES_FILE", "cookies.txt")

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
os.makedirs(MUSIC_FOLDER, exist_ok=True)

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_ffmpeg_path():
    """Return a usable ffmpeg/avconv binary path or None.

    Prefers a system binary, falls back to the statically bundled
    imageio-ffmpeg binary so audio extraction and format merging work
    even inside serverless runtimes without ffmpeg installed.
    """
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


class ProductionConfig:
    SERVER_NAME = None
    PREFERRED_URL_SCHEME = "https" if SERVERLESS else "http"
    SESSION_COOKIE_SECURE = SERVERLESS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)


def format_duration(seconds):
    if not seconds:
        return "--:--"
    seconds = int(seconds)
    minutes = seconds // 60
    secs = seconds % 60
    if minutes >= 60:
        hours = minutes // 60
        minutes = minutes % 60
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_number(num):
    if not num:
        return "--"
    if num >= 1_000_000_000:
        return f"{num / 1_000_000_000:.1f}B"
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    if num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)


def is_valid_url(url):
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    if len(url) > 2048:
        return False
    return url.startswith("http://") or url.startswith("https://")