
from tkinter import ttk

# 샘플 로그 데이터
sample_log = """12:45 제이미 바디 득점
1:0
45:58 제이미 바디 득점
2:0
45:14 로메로 옐로
78:02 로메로 레드
추가시간 +6
91:22 제이미 바디 득점
경기종료"""

# ▶ 영역 지정 (이동 + 크기 조절 + 테두리 표시)
import tkinter as tk
import pyautogui
import threading
import time
from PIL import ImageGrab
import pytesseract
import cv2
import numpy as np

# (설치 경로에 따라 수정)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def ocr_loop():
    coords = selected_area.get("coords")
    if not coords:
        output_box.insert("end", "[오류] 영역이 지정되지 않았습니다.\n")
        return

    def run_ocr():
        while True:
            x1, y1, x2, y2 = coords
            img = ImageGrab.grab(bbox=(x1, y1, x2, y2))

            # 전처리: OpenCV → Grayscale
            open_cv_image = np.array(img)
            gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

            # OCR 처리
            text = pytesseract.image_to_string(thresh, config='--psm 7')  # 한 줄 텍스트 인식
            if is_valid_time_format(text):
                update_timer_label(text)
            else:
                output_box.insert("end", f"[EVENT] {text.strip()}\n")


            # 출력
            output_box.insert("end", f"[OCR] {text.strip()}\n")
            output_box.see("end")

            time.sleep(2)  # 2초마다 갱신

    # OCR 쓰레드 실행
    t = threading.Thread(target=run_ocr, daemon=True)
    t.start()
ocr_running = False
ocr_thread = None

def toggle_ocr():
    global ocr_running, ocr_thread

    if ocr_running:
        ocr_running = False
        output_box.insert("end", "[OCR 중지됨]\n")
    else:
        ocr_running = True

        def run_ocr_loop():
            while ocr_running:
                coords = selected_area.get("coords")
                if coords:
                    x1, y1, x2, y2 = coords
                    img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
                    # 전처리 (OCR 정확도 향상)
                    open_cv_image = np.array(img)
                    gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
                    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
                    text = pytesseract.image_to_string(thresh, config='--psm 7').strip()
                    
                    # 시간 포맷만 타이머에, 그 외는 이벤트로 출력
                    if is_valid_time_format(text):
                        update_timer_label(text)
                    elif text:
                        output_box.insert("end", f"[EVENT] {text}\n")
                    
                    # OCR 로그(디버그용, 필요 없으면 삭제 가능)
                    output_box.insert("end", f"[OCR] {text}\n")
                    output_box.see("end")
                time.sleep(2)

        ocr_thread = threading.Thread(target=run_ocr_loop, daemon=True)
        ocr_thread.start()
        output_box.insert("end", "[OCR 시작됨]\n")



def is_valid_time_format(text):
    import re
    return re.match(r"^\d{1,2}:\d{2}$", text.strip())

def update_timer_label(ocr_text):
    if is_valid_time_format(ocr_text):
        if floating_label:  # 플로팅 타이머가 떠 있을 때만
            floating_label.config(text=ocr_text.strip())

selected_area = {}

def start_area_selection():
    start_x = start_y = 0
    rect_id = None

    def on_mouse_down(event):
        nonlocal start_x, start_y, rect_id
        start_x, start_y = event.x, event.y
        if rect_id:
            canvas.delete(rect_id)

    def on_mouse_drag(event):
        nonlocal rect_id
        if rect_id:
            canvas.delete(rect_id)
        rect_id = canvas.create_rectangle(
            start_x, start_y, event.x, event.y,
            outline="red", width=2, fill="gray", stipple="gray25"
        )

    def on_mouse_up(event):
        end_x, end_y = event.x, event.y
        x1 = min(start_x, end_x)
        y1 = min(start_y, end_y)
        x2 = max(start_x, end_x)
        y2 = max(start_y, end_y)
        selected_area["coords"] = (x1, y1, x2, y2)
        print("지정된 영역 좌표:", selected_area["coords"])
        coord_str = f"지정된 영역 좌표: {selected_area['coords']}\n"
        output_box.insert("end", coord_str)
        overlay.destroy()

    screen_w, screen_h = pyautogui.size()
    overlay = tk.Toplevel()
    overlay.attributes('-fullscreen', True)
    overlay.attributes('-alpha', 0.3)
    overlay.attributes('-topmost', True)
    overlay.config(bg='black')

    # 투명 배경 위에 캔버스는 색 없음
    canvas = tk.Canvas(overlay, bg='lightgray', highlightthickness=0)

    canvas.pack(fill=tk.BOTH, expand=True)
    canvas.bind("<ButtonPress-1>", on_mouse_down)
    canvas.bind("<B1-Motion>", on_mouse_drag)
    canvas.bind("<ButtonRelease-1>", on_mouse_up)



# ▶ 플로팅 타이머 창
floating_label = None
floating_window = None
timer_visible = False  # 토글 상태 변수

def toggle_timer():
    global floating_window, floating_label, timer_visible

    if timer_visible:
        if floating_window:
            floating_window.destroy()
            floating_window = None
        timer_visible = False
    else:
        floating_window = tk.Toplevel()
        floating_window.geometry("200x60+600+100")
        floating_window.overrideredirect(True)
        floating_window.attributes('-topmost', True)

        floating_label = tk.Label(floating_window, text="00:00", font=("Helvetica", 24), bg="black", fg="white")
        floating_label.pack(expand=True, fill="both")

        def start_move(event):
            floating_window._x = event.x
            floating_window._y = event.y

        def do_move(event):
            x = event.x_root - floating_window._x
            y = event.y_root - floating_window._y
            floating_window.geometry(f"+{x}+{y}")

        floating_label.bind("<Button-1>", start_move)
        floating_label.bind("<B1-Motion>", do_move)

        timer_visible = True





# ▶ 메인 창
root = tk.Tk()
root.title("축구 타이머 시스템")
root.geometry("500x500")

# 상단 버튼
top_frame = tk.Frame(root)
top_frame.pack(pady=10)

tk.Button(top_frame, text="영역 지정", command=start_area_selection).pack(side="left", padx=5)

league_var = tk.StringVar(value="프리미어리그")
ttk.Combobox(top_frame, textvariable=league_var, values=["프리미어리그", "챔피언스리그"]).pack(side="left", padx=5)

tk.Button(top_frame, text="보정").pack(side="left", padx=5)

# 텍스트 출력 박스
output_box = tk.Text(root, height=15, width=60)
output_box.pack(pady=10)
output_box.insert("end", sample_log)

# 타이머 출력 버튼
tk.Button(root, text="타이머", command=toggle_timer).pack(pady=5)


tk.Button(root, text="OCR", command=toggle_ocr).pack(pady=5)



root.mainloop()
