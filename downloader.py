import os
import time

import yt_dlp

from config import DOWNLOAD_FOLDER, MUSIC_FOLDER

download_progress = {}
download_complete = {}
active_downloads = {}


class DownloadHandler:
    def __init__(self):
        self.current_download = None
        self.download_id = None

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            if total:
                percent = (downloaded / total) * 100
                download_progress[self.download_id] = percent

    def download_video(self, url, quality, download_id, audio_only=False, audio_bitrate=128):
        self.download_id = download_id
        download_progress[download_id] = 0

        try:
            if audio_only:
                format_code = 'bestaudio/best'
                outtmpl = os.path.join(MUSIC_FOLDER, '%(title)s.%(ext)s')
                postprocessors = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': str(audio_bitrate),
                }]
            else:
                if quality == 'best':
                    format_code = 'bestvideo+bestaudio/best'
                else:
                    quality_num = quality.replace('p', '')
                    format_code = f'bestvideo[height<={quality_num}]+bestaudio/best'
                outtmpl = os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s')
                postprocessors = []

            ydl_opts = {
                'format': format_code,
                'outtmpl': outtmpl,
                'progress_hooks': [self.progress_hook],
                'quiet': True,
                'noplaylist': True,
                'postprocessors': postprocessors,
                'ignoreerrors': True,
                'no_warnings': True,
                'extract_flat': False,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

                if audio_only:
                    filename = outtmpl.replace('%(title)s', info.get('title', 'audio').replace('/', '_'))
                    filename = filename.replace('%(ext)s', 'mp3')
                else:
                    filename = ydl.prepare_filename(info)

                if not os.path.exists(filename):
                    base_name = os.path.splitext(filename)[0]
                    for ext in ['.mp4', '.mkv', '.webm', '.mp3']:
                        test_path = base_name + ext
                        if os.path.exists(test_path):
                            filename = test_path
                            break

                download_complete[download_id] = {
                    'success': True,
                    'filename': os.path.basename(filename),
                    'filepath': filename,
                }
                download_progress[download_id] = 100

        except Exception as e:
            download_complete[download_id] = {
                'success': False,
                'error': str(e),
            }


def cleanup_old_downloads():
    current_time = time.time()
    to_remove = []
    for download_id, info in active_downloads.items():
        if current_time - info['start_time'] > 3600:
            to_remove.append(download_id)

    for download_id in to_remove:
        del active_downloads[download_id]
        if download_id in download_progress:
            del download_progress[download_id]
        if download_id in download_complete:
            del download_complete[download_id]
