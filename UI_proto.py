import tkinter as tk
import threading
import time
import subprocess
from get_info import get_events_data, get_lineup_data, visualize_formation_with_shirt
import ocr

def show_sync_mode_start():
    output_box.insert("end", "[INFO] 타이머 동기화 모드 진입\n")
    output_box.see("end")

def show_sync_mode_stop():
    output_box.insert("end", "[INFO] 동기화 모드 종료\n")
    output_box.see("end")

# 콜백 할당
ocr.on_sync_mode_start = show_sync_mode_start
ocr.on_sync_mode_stop = show_sync_mode_stop

def on_toggle_timer():
    subprocess.Popen(["python", "floatTimer.py"])

def on_toggle_ocr():
    ocr.toggle_ocr()
    output_box.insert("end", "[INFO] OCR " + ("실행\n" if ocr.ocr_running else "종료\n"))
    output_box.see("end")

def on_manual_sync():
    ocr.manual_sync()
    # 메시지는 콜백으로 자동 출력됨

# ---- get_info, formation, event fetch 유지! ----
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

def on_fetch_info():
    output_box.insert("end", "[INFO] 정보 수집 시작\n")
    output_box.see("end")
    show_formation_window()
    start_event_fetch_loop(interval=1)

def start_area_selection():
    output_box.insert("end", "지정된 영역 좌표: (1512, 1218, 1565, 1237)\n")
    output_box.see("end")

def get_current_url():
    return url_var.get().split("?")[0]

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
output_box.insert("end", "샘플 로그\n")

bottom_frame = tk.Frame(root)
bottom_frame.pack(pady=20)

tk.Button(bottom_frame, text="타이머", command=on_toggle_timer).pack(side="left", padx=10)
tk.Button(bottom_frame, text="영역 지정", command=start_area_selection).pack(side="left", padx=10)
tk.Button(bottom_frame, text="OCR", command=on_toggle_ocr).pack(side="left", padx=10)
tk.Button(bottom_frame, text="보정", command=on_manual_sync).pack(side="left", padx=10)

if __name__ == "__main__":
    root.mainloop()
