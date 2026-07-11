import os
from datetime import timedelta

DOWNLOAD_FOLDER = "downloads"
MUSIC_FOLDER = "downloads/music"

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
os.makedirs(MUSIC_FOLDER, exist_ok=True)


class ProductionConfig:
    SERVER_NAME = None
    PREFERRED_URL_SCHEME = 'http'
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)


def format_duration(seconds):
    if not seconds:
        return '--:--'
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
        return '--'
    if num >= 1000000000:
        return f"{num / 1000000000:.1f}B"
    if num >= 1000000:
        return f"{num / 1000000:.1f}M"
    if num >= 1000:
        return f"{num / 1000:.1f}K"
    return str(num)
