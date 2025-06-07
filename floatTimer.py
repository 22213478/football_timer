import sys
import time
import threading
import socket
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from PyQt5.QtCore import Qt, QTimer

SOCKET_PORT = 50507

class FloatingTimer(QWidget):
    def __init__(self):
        super().__init__()
        self.init_sec = 0.0
        self.start_time = None
        self.running = False
        self.sync_mode = False

        self.label = QLabel("00:00", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet(
            "QLabel { background: black; color: white; font-size: 32px; padding: 20px; border-radius: 15px; }"
        )
        self.resize(230, 80)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.move(700, 100)
        self.show()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(100)  # 0.1초마다 UI 갱신

        threading.Thread(target=self.listen_command, daemon=True).start()

        self._drag_active = False
        self._drag_offset = (0, 0)

    def start(self, start_time_str=None):
        if start_time_str:
            self.init_sec = self._str_to_seconds(start_time_str)
        else:
            self.init_sec = 0.0
        self.start_time = time.time()
        self.running = True

    def correct_time(self, time_str):
        self.init_sec = self._str_to_seconds(time_str)
        self.start_time = time.time()
        self.running = True

    def get_time(self):
        if self.start_time is None or not self.running:
            return "00:00"
        elapsed = time.time() - self.start_time
        total_sec = int(self.init_sec + elapsed)
        minute = total_sec // 60
        sec = total_sec % 60
        return f"{minute:02d}:{sec:02d}"  # 소수점 없이 00:00

    def get_time_float(self):
        # GET_TIME 응답은 float 유지 (내부 통신용)
        if self.start_time is None or not self.running:
            return 0.0
        return self.init_sec + (time.time() - self.start_time)

    def _str_to_seconds(self, s):
        try:
            m, s = s.split(":")
            return int(m) * 60 + float(s)
        except Exception:
            return 0.0

    def update_time(self):
        self.label.setText(self.get_time())

    def listen_command(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(('127.0.0.1', SOCKET_PORT))
            server.listen(5)
            while True:
                conn, addr = server.accept()
                with conn:
                    cmd = conn.recv(64).decode().strip()
                    if cmd == "SYNC_ON":
                        self.sync_mode = True
                    elif cmd == "SYNC_OFF":
                        self.sync_mode = False
                    elif cmd.startswith("START"):
                        parts = cmd.split(" ", 1)
                        if len(parts) == 2:
                            _, t = parts
                            self.start(t)
                    elif cmd.startswith("CORRECT"):
                        parts = cmd.split(" ", 1)
                        if len(parts) == 2:
                            _, t = parts
                            if self.sync_mode:
                                self.correct_time(t)
                    elif cmd == "STOP":
                        self.running = False
                        self.start_time = None
                        self.label.setText("00:00")
                    elif cmd == "GET_TIME":
                        t = str(self.get_time_float())
                        conn.sendall(t.encode())

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
