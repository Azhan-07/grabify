import os
import threading

from PyQt5.QtCore import QTimer, QUrl
from PyQt5.QtWidgets import QMainWindow, QMessageBox
from PyQt5.QtWebEngineWidgets import QWebEngineView
from waitress import serve

from app import flask_app


class GrabifyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Grabify - Video & Audio Downloader")
        self.setMinimumSize(400, 700)
        self.resize(1200, 900)

        self.web_view = QWebEngineView()
        self.setCentralWidget(self.web_view)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #0f0c29;
            }
        """)

        self.start_production_server()
        QTimer.singleShot(2000, self.load_interface)

    def start_production_server(self):
        def run_server():
            serve(flask_app, host='127.0.0.1', port=5000, threads=4, channel_timeout=120)

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        print("Production server starting on http://127.0.0.1:5000")

    def load_interface(self):
        self.web_view.setUrl(QUrl("http://127.0.0.1:5000"))

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, 'Exit',
            'Are you sure you want to exit Grabify?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            for file in os.listdir('.'):
                if file.startswith('thumb_') and file.endswith('.jpg'):
                    try:
                        os.remove(file)
                    except:
                        pass
            event.accept()
        else:
            event.ignore()
