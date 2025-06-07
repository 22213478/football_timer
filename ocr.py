import threading
import time
from PIL import ImageGrab
import pytesseract
import cv2
import numpy as np

# Tesseract 경로
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

selected_area = {}
ocr_running = False
ocr_thread = None
ocr_interval = 1
ocr_sync_lock = threading.Lock()

def set_area(coords):
    selected_area["coords"] = coords

def stop_ocr():
    global ocr_running
    ocr_running = False

def start_ocr(on_ocr_result):
    global ocr_running, ocr_thread
    if ocr_running:
        return
    ocr_running = True

    def run_ocr_loop():
        last_ocr_text = None
        while ocr_running:
            coords = selected_area.get("coords")
            if coords:
                x1, y1, x2, y2 = coords
                img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
                open_cv_image = np.array(img)
                gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
                text = pytesseract.image_to_string(thresh, config='--psm 7').strip()
                if is_valid_time_format(text):
                    if text != last_ocr_text:
                        on_ocr_result(text)
                        last_ocr_text = text
            time.sleep(ocr_interval)
            time.sleep(0.01)
    ocr_thread = threading.Thread(target=run_ocr_loop, daemon=True)
    ocr_thread.start()

def is_valid_time_format(text):
    import re
    return re.match(r"^\d{1,2}:\d{2}$", text.strip())

def run_accurate_sync_phase(sync_duration, on_ocr_result):
    global ocr_interval
    if not ocr_sync_lock.acquire(blocking=False):
        return

    coords = selected_area.get("coords")
    if not coords:
        ocr_sync_lock.release()
        return

    def accurate_sync_loop():
        global ocr_interval
        try:
            ocr_interval = 0.15  # 더 빠르게
            start_time = time.time()
            last_success_time = start_time
            last_success_text = None
            ocr_results = []
            while time.time() - start_time < sync_duration:
                x1, y1, x2, y2 = coords
                img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
                open_cv_image = np.array(img)
                gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
                text = pytesseract.image_to_string(thresh, config='--psm 7').strip()
                if is_valid_time_format(text):
                    last_success_time = time.time()
                    last_success_text = text
                    ocr_results.append(text)
                    on_ocr_result(text, sync_mode=True)
                time.sleep(ocr_interval)
                time.sleep(0.005)
            # 동기화 구간이 끝나면, 마지막으로 인식된 OCR값을 한 번 더 강제 반영 (UI타이머 포함)
            if last_success_text:
                on_ocr_result(last_success_text, sync_mode="final")
        finally:
            ocr_interval = 1
            ocr_sync_lock.release()
    threading.Thread(target=accurate_sync_loop, daemon=True).start()
