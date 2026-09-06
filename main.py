import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser


def ensure_package(package):
    try:
        __import__(package.replace("-", "_"))
        return True
    except ImportError:
        return False


def wait_for_server(url, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"{url}/api/health", timeout=2)
            return True
        except Exception:
            time.sleep(0.3)
    return False


def main():
    if not shutil.which("ffmpeg"):
        print("Warning: FFmpeg not found on PATH. Audio extraction (MP3) will fail.")
        print("Install FFmpeg from: https://ffmpeg.org/download.html")

    for package in ["waitress", "flask-limiter"]:
        if not ensure_package(package):
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

    from app import flask_app

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 5000))
    url = f"http://{host}:{port}"

    server_thread = threading.Thread(
        target=lambda: __import__("waitress").serve(
            flask_app, host=host, port=port, threads=8
        ),
        daemon=True,
    )
    server_thread.start()

    if wait_for_server(url):
        print(f"Grabify is running at {url}")
        webbrowser.open(url)
    else:
        print("Failed to start the server. Check the logs above.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down Grabify...")


if __name__ == "__main__":
    main()