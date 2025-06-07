# VirtualTimer.py

import time

class VirtualTimer:
    def __init__(self):
        self.start_time = None      # 실제 타이머가 시작된 시스템 시간 (epoch float)
        self.init_sec = 0.0         # 타이머가 시작할 때의 "기준 시각" (초, float)
        self.running = False

    def start(self, start_time_str=None):
        """타이머 시작, start_time_str이 있으면 해당 시간에서 시작"""
        if start_time_str:
            # "mm:ss" or "mm:ss.ss" 모두 지원
            self.init_sec = self._str_to_seconds(start_time_str)
        else:
            self.init_sec = 0.0
        self.start_time = time.time()
        self.running = True

    def correct_time(self, time_str):
        """현재 타이머를 강제로 보정: 입력된 문자열 시각으로 즉시 변경"""
        self.init_sec = self._str_to_seconds(time_str)
        self.start_time = time.time()

    def get_time(self):
        """현재 VirtualTimer의 시각을 mm:ss.ss(소수점 둘째자리) 형태로 반환"""
        if self.start_time is None:
            return "00:00.00"
        elapsed = time.time() - self.start_time
        total_sec = self.init_sec + elapsed
        minute = int(total_sec // 60)
        sec = total_sec % 60
        return f"{minute:02d}:{sec:05.2f}"

    def _str_to_seconds(self, s):
        """'mm:ss' or 'mm:ss.ss' 문자열을 float 초로 변환"""
        try:
            m, s = s.split(":")
            return int(m) * 60 + float(s)
        except Exception:
            return 0.0

    def is_running(self):
        return self.running

    def stop(self):
        self.running = False
        self.start_time = None

# (테스트용 코드: 아래는 실제 사용 환경에서는 필요없음)
if __name__ == "__main__":
    vt = VirtualTimer()
    vt.start("12:34.78")
    for _ in range(10):
        print(vt.get_time())
        time.sleep(0.25)
