import os
import secrets
import threading
import time
from datetime import datetime

from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import ProductionConfig, format_duration, format_number, DOWNLOAD_FOLDER, MUSIC_FOLDER
from downloader import DownloadHandler, download_progress, download_complete, active_downloads, cleanup_old_downloads

flask_app = Flask(__name__)
flask_app.config['SECRET_KEY'] = secrets.token_hex(32)
flask_app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024
flask_app.config.from_object(ProductionConfig)
CORS(flask_app)

limiter = Limiter(
    get_remote_address,
    app=flask_app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)


@flask_app.route('/')
def index():
    return render_template('index.html')


@flask_app.route('/api/info', methods=['POST'])
@limiter.limit("10 per minute")
def get_video_info():
    data = request.json
    url = data.get('url')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        import yt_dlp

        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            platform = info.get('extractor', 'Unknown')
            platform_map = {
                'youtube': 'YouTube', 'instagram': 'Instagram',
                'facebook': 'Facebook', 'tiktok': 'TikTok',
            }
            for key, value in platform_map.items():
                if key in platform.lower():
                    platform = value
                    break

            response_data = {
                'title': info.get('title', 'Unknown Title'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration', 0),
                'formatted_duration': format_duration(info.get('duration', 0)),
                'view_count': info.get('view_count', 0),
                'formatted_views': format_number(info.get('view_count', 0)),
                'platform': platform,
                'filesize': info.get('filesize', 0),
            }

            return jsonify(response_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@flask_app.route('/api/download', methods=['POST'])
@limiter.limit("5 per minute")
def download_video():
    data = request.json
    url = data.get('url')
    quality = data.get('quality', 'best')
    audio_only = data.get('audio_only', False)
    audio_bitrate = data.get('audio_bitrate', 128)

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    cleanup_old_downloads()

    download_id = secrets.token_hex(8)
    download_handler = DownloadHandler()

    thread = threading.Thread(
        target=download_handler.download_video,
        args=(url, quality, download_id, audio_only, audio_bitrate),
    )
    thread.daemon = True
    thread.start()

    active_downloads[download_id] = {
        'thread': thread,
        'start_time': time.time(),
        'handler': download_handler,
    }

    return jsonify({
        'success': True,
        'download_id': download_id,
        'message': 'Download started',
    })


@flask_app.route('/api/progress/<download_id>', methods=['GET'])
def get_progress(download_id):
    progress = download_progress.get(download_id, 0)
    return jsonify({'progress': progress})


@flask_app.route('/api/status/<download_id>', methods=['GET'])
def get_status(download_id):
    if download_id in download_complete:
        result = download_complete[download_id]
        if result['success']:
            return jsonify({
                'status': 'complete',
                'filename': result['filename'],
                'filepath': result['filepath'],
            })
        else:
            return jsonify({
                'status': 'error',
                'error': result['error'],
            })
    return jsonify({'status': 'downloading'})


@flask_app.route('/api/download-file/<filename>', methods=['GET'])
def download_file(filename):
    video_path = os.path.join(DOWNLOAD_FOLDER, filename)
    music_path = os.path.join(MUSIC_FOLDER, filename)

    if os.path.exists(video_path):
        return send_file(video_path, as_attachment=True, download_name=filename)
    elif os.path.exists(music_path):
        return send_file(music_path, as_attachment=True, download_name=filename)
    else:
        return jsonify({'error': 'File not found'}), 404


@flask_app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'active_downloads': len(active_downloads),
    })


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    from waitress import serve
    serve(flask_app, host='0.0.0.0', port=port)
