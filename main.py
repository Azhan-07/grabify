import os
import shutil
import sys
import webbrowser

from PyQt5.QtWidgets import QApplication

from ui import GrabifyApp

if __name__ == '__main__':
    if not shutil.which('ffmpeg'):
        print("Warning: FFmpeg not found on PATH. Audio extraction (MP3) will fail.")
        print("Install FFmpeg from: https://ffmpeg.org/download.html")

    required_packages = ['waitress', 'flask-limiter']
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            print(f"Installing {package}...")
            os.system(f'pip install {package}')

    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("Grabify")

    window = GrabifyApp()
    window.show()

    webbrowser.open("http://127.0.0.1:5000")

    sys.exit(qt_app.exec_())
