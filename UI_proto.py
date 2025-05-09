import tkinter as tk
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
def start_area_selection():
    selection_window = tk.Toplevel()
    selection_window.overrideredirect(True)
    selection_window.attributes("-topmost", True)
    selection_window.geometry("300x150+300+200")
    selection_window.config(bg='white')
    selection_window.attributes("-alpha", 0.3)

    canvas = tk.Canvas(selection_window, bg='white', highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    border = canvas.create_rectangle(0, 0, 300, 150, outline="black", width=2)

    def start_move(event):
        selection_window._start_x = event.x
        selection_window._start_y = event.y

    def do_move(event):
        x = event.x_root - selection_window._start_x
        y = event.y_root - selection_window._start_y
        selection_window.geometry(f"+{x}+{y}")

    canvas.bind("<Button-1>", start_move)
    canvas.bind("<B1-Motion>", do_move)

    grip_size = 15
    grip = canvas.create_rectangle(285, 135, 300, 150, fill="gray", outline="black")

    def do_resize(event):
        width = max(event.x, 100)
        height = max(event.y, 50)
        selection_window.geometry(f"{width}x{height}")
        canvas.coords(border, 0, 0, width, height)
        canvas.coords(grip, width - grip_size, height - grip_size, width, height)

    canvas.tag_bind(grip, "<B1-Motion>", do_resize)

# ▶ 플로팅 타이머 창
def show_timer():
    floating = tk.Toplevel()
    floating.geometry("200x60+600+100")
    floating.overrideredirect(True)
    floating.attributes('-topmost', True)
    floating_label = tk.Label(floating, text="00:00", font=("Helvetica", 24))
    floating_label.pack(expand=True, fill="both")

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
tk.Button(root, text="타이머 출력", command=show_timer).pack(pady=10)

root.mainloop()
