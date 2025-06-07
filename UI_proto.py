import tkinter as tk
import threading
import time
import subprocess
import socket
import os
from get_info import get_events_data, get_lineup_data, visualize_formation_with_shirt
from VirtualTimer import VirtualTimer
import ocr

floating_window = None
floating_label = None
timer_visible = False
virtual_timer = VirtualTimer()
sync_in_progress = False

SOCKET_PORT = 50507
SYNC_SIGNAL_PORT = 50508  # 동기화 신호 소켓

# ----- 동기화 신호를 소켓으로 전송 -----
def set_sync_state_socket(state):
    # state: "SYNC" or "NOSYNC"
    for _ in range(3):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('127.0.0.1', SYNC_SIGNAL_PORT))
                s.sendall(state.encode())
            break
        except Exception:
            time.sleep(0.1)

def timer_socket_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('127.0.0.1', SOCKET_PORT))
        s.listen(1)
        while True:
            conn, addr = s.accept()
            with conn:
                while True:
                    try:
                        value = virtual_timer.get_time() + "\n"
                        conn.sendall(value.encode())
                        time.sleep(0.1)
                    except Exception:
                        break

def run_accurate_sync_phase(sync_duration=8):
    global sync_in_progress
    if sync_in_progress:
        return
    sync_in_progress = True
    set_sync_state_socket("SYNC")
    output_box.insert("end", "[INFO] 타이머 정밀 동기화 구간 시작\n")
    ocr.run_accurate_sync_phase(sync_duration, on_ocr_result)

def on_ocr_result(time_str, sync_mode=False):
    global sync_in_progress
    if not virtual_timer.running:
        virtual_timer.start(time_str)
        if not sync_mode:
            run_accurate_sync_phase(sync_duration=8)
    else:
        vtime = virtual_timer.get_time()
        ocr_sec = virtual_timer._str_to_seconds(time_str)
        vtime_sec = virtual_timer._str_to_seconds(vtime)
        if abs(ocr_sec - vtime_sec) >= 2 and not sync_mode and not sync_in_progress:
            run_accurate_sync_phase(sync_duration=8)
        else:
            virtual_timer.correct_time(time_str)
            if sync_mode == "final" and sync_in_progress:
                output_box.insert("end", "[INFO] 타이머 정밀 동기화 구간 종료\n")
                sync_in_progress = False
                set_sync_state_socket("NOSYNC")

def show_formation_window():
    try:
        url = get_current_url() + "?tab=lineup"
        home, away, colors = get_lineup_data(url, shirt_template="shirt_transparent.png")
    except Exception as e:
        root.after(0, lambda: output_box.insert("end", f"[오류] 포메이션 정보를 가져오지 못했습니다: {e}\n"))
        return
    width, height = 820, 900
    formation_win = tk.Toplevel()
    formation_win.title(f"라인업: {home['team_name']} vs {away['team_name']}")
    formation_win.geometry(f"{width}x{height}")
    canvas = tk.Canvas(formation_win, width=width, height=height, bg="#1a273a")
    canvas.pack()
    mid = height // 2
    visualize_formation_with_shirt(home, top=60, bottom=mid-10, canvas=canvas, width=width, shirt_color=colors[0], shirt_template_path="shirt_transparent.png", reverse_order=False)
    visualize_formation_with_shirt(away, top=mid+10, bottom=height-60, canvas=canvas, width=width, shirt_color=colors[1], shirt_template_path="shirt_transparent.png", reverse_order=True)

event_thread = None
last_event_set = set()
def start_event_fetch_loop(interval=1):
    global event_thread, last_event_set
    if event_thread and event_thread.is_alive():
        return
    last_event_set = set()
    def run():
        global last_event_set
        while True:
            url = get_current_url() + "?tab=record"
            events = get_events_data(url)
            new_events = [ev for ev in events if ev not in last_event_set]
            for ev in new_events:
                root.after(0, lambda ev=ev: output_box.insert("end", f"[EVENT] {ev}\n"))
                root.after(0, lambda: output_box.see("end"))
            last_event_set.update(new_events)
            time.sleep(interval)
    event_thread = threading.Thread(target=run, daemon=True)
    event_thread.start()

def on_fetch_info():
    root.after(0, lambda: output_box.insert("end", f"[INFO] 정보 수집 시작\n"))
    show_formation_window()
    start_event_fetch_loop(interval=1)

def start_area_selection():
    import pyautogui
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
        ocr.set_area((x1, y1, x2, y2))
        coord_str = f"지정된 영역 좌표: {(x1, y1, x2, y2)}\n"
        root.after(0, lambda: output_box.insert("end", coord_str))
        overlay.destroy()
    screen_w, screen_h = pyautogui.size()
    overlay = tk.Toplevel()
    overlay.attributes('-fullscreen', True)
    overlay.attributes('-alpha', 0.3)
    overlay.attributes('-topmost', True)
    overlay.config(bg='black')
    canvas = tk.Canvas(overlay, bg='lightgray', highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)
    canvas.bind("<ButtonPress-1>", on_mouse_down)
    canvas.bind("<B1-Motion>", on_mouse_drag)
    canvas.bind("<ButtonRelease-1>", on_mouse_up)

def toggle_ocr():
    if ocr.ocr_running:
        ocr.stop_ocr()
        output_box.insert("end", "[OCR 중지됨]\n")
    else:
        ocr.start_ocr(lambda text: on_ocr_result(text, sync_mode=False))
        output_box.insert("end", "[OCR 시작됨]\n")

def toggle_timer():
    global timer_visible
    if timer_visible:
        timer_visible = False
    else:
        timer_visible = True
        subprocess.Popen(["python", "floatTimer.py"])

def get_current_url():
    return url_var.get().split("?")[0]

sample_log = """12:45 제이미 바디 득점
1:0
45:58 제이미 바디 득점
2:0
45:14 로메로 옐로
78:02 로메로 레드
추가시간 +6
91:22 제이미 바디 득점
경기종료"""

root = tk.Tk()
root.title("축구 타이머 시스템")
root.geometry("500x500")

top_frame = tk.Frame(root)
top_frame.pack(pady=10)

url_var = tk.StringVar(value="https://sports.daum.net/match/80085755?tab=lineup")
tk.Entry(top_frame, textvariable=url_var, width=45).pack(side="left", padx=5)
tk.Button(top_frame, text="정보 가져오기", command=on_fetch_info).pack(side="left", padx=5)

output_box = tk.Text(root, height=15, width=60)
output_box.pack(pady=10)
output_box.insert("end", sample_log)

bottom_frame = tk.Frame(root)
bottom_frame.pack(pady=20)

tk.Button(bottom_frame, text="타이머", command=toggle_timer).pack(side="left", padx=10)
tk.Button(bottom_frame, text="영역 지정", command=start_area_selection).pack(side="left", padx=10)
tk.Button(bottom_frame, text="OCR", command=toggle_ocr).pack(side="left", padx=10)
tk.Button(bottom_frame, text="보정", command=lambda: run_accurate_sync_phase(sync_duration=8)).pack(side="left", padx=10)

threading.Thread(target=timer_socket_server, daemon=True).start()
set_sync_state_socket("NOSYNC")  # 시작 시 NOSYNC 신호 송신

if __name__ == "__main__":
    root.mainloop()
