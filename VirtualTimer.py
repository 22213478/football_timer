import time
import threading
import socket

SOCKET_PORT = 50507

class VirtualTimer:
    def __init__(self):
        self.init_sec = 0.0
        self.start_time = None
        self.running = False
        threading.Thread(target=self.listen_command, daemon=True).start()

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
            return "00:00.00"
        elapsed = time.time() - self.start_time
        total_sec = self.init_sec + elapsed
        minute = int(total_sec // 60)
        sec = total_sec % 60
        return f"{minute:02d}:{sec:05.2f}"

    def _str_to_seconds(self, s):
        try:
            m, s = s.split(":")
            return int(m) * 60 + float(s)
        except Exception:
            return 0.0

    def listen_command(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(('127.0.0.1', SOCKET_PORT))
            server.listen(5)
            while True:
                conn, addr = server.accept()
                with conn:
                    cmd = conn.recv(64).decode().strip()
                    if cmd.startswith("START"):
                        _, t = cmd.split(" ", 1)
                        self.start(t)
                    elif cmd.startswith("CORRECT"):
                        _, t = cmd.split(" ", 1)
                        self.correct_time(t)
                    elif cmd == "STOP":
                        self.running = False
                        self.start_time = None

def timer_socket_server(vtimer):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('127.0.0.1', 50508))  # 타이머 값 전달용 별도 포트!
        s.listen(1)
        while True:
            conn, addr = s.accept()
            with conn:
                while True:
                    try:
                        value = vtimer.get_time() + "\n"
                        conn.sendall(value.encode())
                        time.sleep(0.01)  # 100Hz 전송(매우 부드럽게)
                    except Exception:
                        break

if __name__ == '__main__':
    vtimer = VirtualTimer()
    threading.Thread(target=timer_socket_server, args=(vtimer,), daemon=True).start()
    while True:
        time.sleep(10)  # 메인 스레드 블록(서브 스레드만 동작)
