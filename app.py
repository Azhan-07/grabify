import logging
import os
import secrets
import threading
import time
import traceback
from datetime import datetime

from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import ProductionConfig, format_duration, format_number, is_valid_url, DOWNLOAD_FOLDER, MUSIC_FOLDER
from downloader import DownloadHandler, download_progress, download_complete, active_downloads, cleanup_old_downloads

logger = logging.getLogger(__name__)

flask_app = Flask(__name__)
flask_app.config["SECRET_KEY"] = secrets.token_hex(32)
flask_app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024
flask_app.config.from_object(ProductionConfig)
CORS(flask_app)

limiter = Limiter(
    get_remote_address,
    app=flask_app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

VALID_QUALITIES = {"best", "1080p", "720p", "480p", "360p"}
VALID_BITRATES = {64, 128, 192, 320}


@flask_app.route("/")
def index():
    return render_template("index.html")


@flask_app.route("/api/info", methods=["POST"])
@limiter.limit("10 per minute")
def get_video_info():
    data = request.json
    if not data:
        return jsonify({"success": False, "error": "Invalid request body."}), 400

    url = data.get("url", "").strip() if isinstance(data.get("url"), str) else ""

    if not is_valid_url(url):
        return jsonify({"success": False, "error": "Please provide a valid URL starting with http:// or https://"}), 400

    try:
        import yt_dlp

        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "no_warnings": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            if info is None:
                return jsonify({"success": False, "error": "Could not retrieve video information. The video may be private or unavailable."}), 404

            platform = info.get("extractor", "Unknown")
            platform_map = {
                "youtube": "YouTube",
                "instagram": "Instagram",
                "facebook": "Facebook",
                "tiktok": "TikTok",
            }
            for key, value in platform_map.items():
                if key in platform.lower():
                    platform = value
                    break

            response_data = {
                "success": True,
                "title": info.get("title", "Unknown Title"),
                "thumbnail": info.get("thumbnail", ""),
                "duration": info.get("duration", 0),
                "formatted_duration": format_duration(info.get("duration", 0)),
                "view_count": info.get("view_count", 0),
                "formatted_views": format_number(info.get("view_count", 0)),
                "platform": platform,
                "filesize": info.get("filesize", 0),
            }

            return jsonify(response_data)

    except Exception as e:
        logger.error("Error fetching video info: %s\n%s", str(e), traceback.format_exc())
        error_msg = str(e)
        if "Sign in to confirm" in error_msg or "bot" in error_msg.lower():
            return jsonify({
                "success": False,
                "error": "YouTube is blocking automated access (bot detection). Please try again later or provide a cookies.txt file.",
            }), 403
        return jsonify({"success": False, "error": "Failed to fetch video information. Please check the URL and try again."}), 500


@flask_app.route("/api/download", methods=["POST"])
@limiter.limit("5 per minute")
def download_video():
    data = request.json
    if not data:
        return jsonify({"success": False, "error": "Invalid request body."}), 400

    url = data.get("url", "").strip() if isinstance(data.get("url"), str) else ""
    quality = data.get("quality", "best")
    audio_only = data.get("audio_only", False)
    audio_bitrate = data.get("audio_bitrate", 128)

    if not is_valid_url(url):
        return jsonify({"success": False, "error": "Please provide a valid URL starting with http:// or https://"}), 400

    if quality not in VALID_QUALITIES:
        quality = "best"

    if not isinstance(audio_only, bool):
        audio_only = False

    try:
        audio_bitrate = int(audio_bitrate)
    except (TypeError, ValueError):
        audio_bitrate = 128
    if audio_bitrate not in VALID_BITRATES:
        audio_bitrate = 128

    cleanup_old_downloads()

    download_id = secrets.token_hex(8)
    download_handler = DownloadHandler()

    thread = threading.Thread(
        target=download_handler.download_video,
        args=(url, quality, download_id, audio_only, audio_bitrate),
        daemon=True,
    )
    thread.start()

    active_downloads[download_id] = {
        "thread": thread,
        "start_time": time.time(),
        "handler": download_handler,
    }

    return jsonify({
        "success": True,
        "download_id": download_id,
        "message": "Download started",
    })


@flask_app.route("/api/progress/<download_id>", methods=["GET"])
def get_progress(download_id):
    if not download_id or not isinstance(download_id, str):
        return jsonify({"success": False, "error": "Invalid download ID."}), 400
    progress = download_progress.get(download_id, 0)
    return jsonify({"success": True, "progress": progress})


@flask_app.route("/api/status/<download_id>", methods=["GET"])
def get_status(download_id):
    if not download_id or not isinstance(download_id, str):
        return jsonify({"success": False, "error": "Invalid download ID."}), 400

    if download_id in download_complete:
        result = download_complete[download_id]
        if result["success"]:
            return jsonify({
                "success": True,
                "status": "complete",
                "filename": result["filename"],
                "filepath": result["filepath"],
            })
        else:
            return jsonify({
                "success": False,
                "status": "error",
                "error": result["error"],
            })
    return jsonify({"success": True, "status": "downloading"})


@flask_app.route("/api/download-file/<filename>", methods=["GET"])
def download_file(filename):
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        return jsonify({"success": False, "error": "Invalid filename."}), 400

    video_path = os.path.join(DOWNLOAD_FOLDER, filename)
    music_path = os.path.join(MUSIC_FOLDER, filename)

    if os.path.exists(video_path) and os.path.isfile(video_path):
        return send_file(video_path, as_attachment=True, download_name=filename)
    elif os.path.exists(music_path) and os.path.isfile(music_path):
        return send_file(music_path, as_attachment=True, download_name=filename)
    else:
        return jsonify({"success": False, "error": "File not found. It may have been cleaned up."}), 404


@flask_app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_downloads": len(active_downloads),
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    from waitress import serve
    serve(flask_app, host="0.0.0.0", port=port)
