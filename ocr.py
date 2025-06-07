import threading
import time
import socket
from PIL import ImageGrab
import pytesseract
import cv2
import numpy as np
import re

SOCKET_PORT = 50507
OCR_AREA = (1512, 1218, 1565, 1237)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# 콜백: UI에서 할당할 것!
on_sync_mode_start = None
on_sync_mode_stop = None

# 내부 상태
ocr_running = False
sync_mode = False
drift_over_count = 0
timer_started = False
SYNC_THRESHOLD = 2
SYNC_REQUIRED_COUNT = 2
SYNC_DURATION = 8

def run_single_ocr():
    x1, y1, x2, y2 = OCR_AREA
    img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
    open_cv_image = np.array(img)
    gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    text = pytesseract.image_to_string(thresh, config='--psm 7').strip()
    if re.match(r"^\d{1,2}:\d{2}$", text):
        return text
    return ""

def send_command_to_float_timer(cmd):
    for _ in range(3):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('127.0.0.1', SOCKET_PORT))
                s.sendall(cmd.encode())
            break
        except Exception:
            time.sleep(0.1)

def get_float_timer_time():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            s.connect(('127.0.0.1', SOCKET_PORT))
            s.sendall(b'GET_TIME')
            t = s.recv(64).decode().strip()
            return float(t)
    except Exception:
        return 0

def notify_sync_mode_start():
    if on_sync_mode_start:
        on_sync_mode_start()

def notify_sync_mode_stop():
    if on_sync_mode_stop:
        on_sync_mode_stop()

def periodic_ocr_loop():
    global ocr_running, sync_mode, drift_over_count, timer_started
    timer_started = False
    drift_over_count = 0
    sync_mode = False
    ocr_interval = 1.0
    last_ocr_text = None
    first_sync = False
    while ocr_running:
        text = run_single_ocr()
        if not timer_started and text:
            send_command_to_float_timer(f"START {text}")
            timer_started = True
            # 최초 동기화 진입
            sync_mode = True
            notify_sync_mode_start()
            send_command_to_float_timer("SYNC_ON")
            threading.Thread(target=run_accurate_sync_phase, daemon=True).start()
            first_sync = True
        elif sync_mode:
            if text:
                send_command_to_float_timer(f"CORRECT {text}")
        else:
            if text and text != last_ocr_text:
                vt_time = get_float_timer_time()
                try:
                    m, s = text.split(":")
                    ocr_time = int(m)*60 + float(s)
                    if vt_time != 0:
                        if abs(ocr_time - vt_time) > SYNC_THRESHOLD:
                            drift_over_count += 1
                            if drift_over_count >= SYNC_REQUIRED_COUNT:
                                sync_mode = True
                                notify_sync_mode_start()
                                send_command_to_float_timer("SYNC_ON")
                                threading.Thread(target=run_accurate_sync_phase, daemon=True).start()
                                drift_over_count = 0
                        else:
                            drift_over_count = 0
                except Exception:
                    pass
            last_ocr_text = text
        time.sleep(ocr_interval if not sync_mode else 0.15)
    sync_mode = False
    drift_over_count = 0
    timer_started = False

def run_accurate_sync_phase(duration=5):
    global sync_mode, drift_over_count, timer_started
    end_time = time.time() + duration
    last_text = None
    last_ocr_time = None
    while time.time() < end_time and ocr_running:
        t0 = time.time()
        text = run_single_ocr()
        if text and re.match(r"^\d{1,2}:\d{2}$", text):
            send_command_to_float_timer(f"CORRECT {text}")
            last_text = text
            last_ocr_time = t0
        time.sleep(0.15)
    # 마지막 OCR 시각과 now의 차이를 반영
    if last_text and last_ocr_time:
        m, s = last_text.split(":")
        f_sec = int(m) * 60 + float(s) + (time.time() - last_ocr_time +1)
        m2 = int(f_sec) // 60
        s2 = f_sec % 60
        t_new = f"{m2:02d}:{int(s2):02d}"
        send_command_to_float_timer(f"CORRECT {t_new}")
    send_command_to_float_timer("SYNC_OFF")
    sync_mode = False
    drift_over_count = 0
    timer_started = True
    notify_sync_mode_stop()



def start_ocr():
    global ocr_running
    if ocr_running:
        return
    ocr_running = True
    threading.Thread(target=periodic_ocr_loop, daemon=True).start()

def stop_ocr():
    global ocr_running, sync_mode
    ocr_running = False
    sync_mode = False

def toggle_ocr():
    if ocr_running:
        stop_ocr()
    else:
        start_ocr()

def manual_sync(sync_duration=3):  # ★ 여기 3초로
    send_command_to_float_timer("SYNC_ON")
    global sync_mode
    sync_mode = True
    notify_sync_mode_start()
    threading.Thread(target=lambda: run_accurate_sync_phase(sync_duration), daemon=True).start()
