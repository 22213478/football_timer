import tkinter as tk
import pyautogui

selected_area = {}

def on_mouse_down(event):
    global start_x, start_y
    start_x, start_y = event.x, event.y
    canvas.delete("selection")

def on_mouse_drag(event):
    canvas.delete("selection")
    canvas.create_rectangle(start_x, start_y, event.x, event.y, outline="red", tag="selection")

def on_mouse_up(event):
    end_x, end_y = event.x, event.y
    x1 = min(start_x, end_x)
    y1 = min(start_y, end_y)
    x2 = max(start_x, end_x)
    y2 = max(start_y, end_y)
    selected_area["coords"] = (x1, y1, x2, y2)
    print("지정된 영역 좌표:", selected_area["coords"])
    root.destroy()

# 전체 화면 정보 가져오기
screen_w, screen_h = pyautogui.size()

# 전체 화면을 덮는 투명 창
root = tk.Tk()
root.attributes('-fullscreen', True)
root.attributes('-alpha', 0.3)
root.attributes('-topmost', True)

canvas = tk.Canvas(root, bg='black')
canvas.pack(fill=tk.BOTH, expand=True)
canvas.bind("<ButtonPress-1>", on_mouse_down)
canvas.bind("<B1-Motion>", on_mouse_drag)
canvas.bind("<ButtonRelease-1>", on_mouse_up)

root.mainloop()

# 결과 확인
if "coords" in selected_area:
    print("최종 영역:", selected_area["coords"])
