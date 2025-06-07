# floatTimer.py
import sys
import socket
import time
import threading
import os
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer

SOCKET_PORT = 50507
SYNC_SIGNAL_PORT = 50508   # <--- 동기화 신호 전용 소켓 포트

class FloatingTimer(QWidget):
    def __init__(self):
        super().__init__()
        self.label = QLabel("00:00.00", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet(
            "QLabel { background: black; color: white; font-size: 28px; padding: 20px; border-radius: 15px; }"
        )
        self.resize(260, 80)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.move(700, 100)
        self.show()

        self._drag_active = False
        self._drag_offset = (0, 0)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.main_loop)
        self.timer.start(50)  # 0.05초마다 메인 루프

        self.syncing = False
        self.current_time_sec = 0.0
        self.last_update = time.time()
        self.sock = None
        self.buffer = b""
        self.last_synced_time_sec = 0.0  # 오차 없는 마지막 서버 시각

        # 동기화 신호 감지(소켓) 스레드
        threading.Thread(target=self.sync_signal_watcher, daemon=True).start()

    def sync_signal_watcher(self):
        # SYNC_SIGNAL_PORT로 계속 listening (IPC)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(('127.0.0.1', SYNC_SIGNAL_PORT))
            server.listen(1)
            while True:
                conn, addr = server.accept()
                with conn:
                    signal = conn.recv(32).decode().strip()
                    if signal == "SYNC":
                        self.syncing = True
                        self.connect_socket()
                    elif signal == "NOSYNC":
                        self.syncing = False
                        self.disconnect_socket()
                        # 동기화 끝날 때, 소켓에서 받은 마지막 float 그대로 저장
                        self.current_time_sec = self.last_synced_time_sec
                        self.last_update = time.time()

    def connect_socket(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect(('127.0.0.1', SOCKET_PORT))
            self.sock.setblocking(False)
        except Exception:
            self.sock = None

    def disconnect_socket(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def main_loop(self):
        if self.syncing:
            # 동기화 중: 서버에서 값 수신
            if self.sock:
                try:
                    while True:
                        chunk = self.sock.recv(128)
                        if not chunk:
                            self.sock = None
                            return
                        self.buffer += chunk
                        while b"\n" in self.buffer:
                            line, self.buffer = self.buffer.split(b"\n", 1)
                            text = line.decode().strip()
                            self.label.setText(text)
                            self.current_time_sec = self._str_to_seconds(text)
                            self.last_synced_time_sec = self.current_time_sec  # 정확한 float값 저장
                            self.last_update = time.time()
                except BlockingIOError:
                    pass
            else:
                # 재연결 시도
                self.connect_socket()
        else:
            # 자체적으로 실시간 누적
            now = time.time()
            elapsed = now - self.last_update
            if elapsed > 0.01:
                self.current_time_sec += elapsed
                self.last_update = now
            self.label.setText(self._seconds_to_str(self.current_time_sec))

    def _str_to_seconds(self, text):
        try:
            parts = text.split(":")
            if len(parts) == 2:
                minute, sec = parts
                return int(minute) * 60 + float(sec)
        except Exception:
            return 0.0

    def _seconds_to_str(self, sec):
        sec = max(0, sec)
        minute = int(sec // 60)
        second = sec % 60
        return f"{minute:02d}:{second:05.2f}"

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_active = True
            self._drag_offset = (event.x(), event.y())
    def mouseMoveEvent(self, event):
        if self._drag_active:
            x = event.globalX() - self._drag_offset[0]
            y = event.globalY() - self._drag_offset[1]
            self.move(x, y)
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_active = False

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = FloatingTimer()
    sys.exit(app.exec_())
