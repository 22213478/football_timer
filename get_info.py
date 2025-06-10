from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from PIL import Image, ImageTk, ImageDraw
import tkinter as tk
import numpy as np
import time
import re


SHIRT_SIZE = (60, 60)
ICON_SIZE = (32, 32)
NAME_FONT_SIZE = 18
NAME_Y_SHIFT = SHIRT_SIZE[1]//2 + 16  
ICON_GAP = 2


def resize_with_aspect(image, max_size):
    iw, ih = image.size
    mw, mh = max_size
    scale = min(mw / iw, mh / ih)
    new_size = (int(iw * scale), int(ih * scale))
    return image.resize(new_size, Image.LANCZOS)

def draw_shirt_with_real_border(img, border_color=(50,255,40), border_width=4):
    alpha = img.split()[-1]
    arr = np.array(alpha)
    h, w = arr.shape
    mask = (arr > 0).astype(np.uint8) * 255
    edge = np.zeros_like(mask)
    edge[:-1,:] |= mask[:-1,:] != mask[1:,:]
    edge[1:,:] |= mask[:-1,:] != mask[1:,:]
    edge[:,:-1] |= mask[:,:-1] != mask[:,1:]
    edge[:,1:] |= mask[:,:-1] != mask[:,1:]
    yx = np.argwhere(edge)
    if yx.size == 0:
        return img
    bordered = img.copy()
    for y, x in yx:
        for dx in range(-border_width//2, border_width//2+1):
            for dy in range(-border_width//2, border_width//2+1):
                xx, yy = x+dx, y+dy
                if 0<=xx<w and 0<=yy<h:
                    bordered.putpixel((xx,yy), border_color + (255,))
    return bordered

def make_card_icon(color, size=(28, 36)):
    img = Image.new("RGBA", size, (0,0,0,0))
    draw = ImageDraw.Draw(img)
    draw.rectangle([2,2,size[0]-2,size[1]-2], fill=color, outline=(0,0,0))
    return img

# ====== 파싱 ======
def get_events_data(url):
    event_url = url.split('?')[0] + "?tab=record"
    options = Options()
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)
    driver.get(event_url)
    time.sleep(2.5)
    html = driver.page_source
    driver.quit()
    soup = BeautifulSoup(html, "html.parser")
    events = []
    timeline_blocks = soup.find_all("div", class_="item_timeline")
    for block in timeline_blocks:
        time_tag = block.find("span", class_="txt_time")
        info_tag = block.find("span", class_="txt_info")
        minute = ""
        extra_minute = False
        if time_tag:
            minute = time_tag.get_text(strip=True)
        elif info_tag and "추가시간" in info_tag.get_text():
            minute = "추가시간 +" + info_tag.get_text(strip=True).replace("추가시간", "").replace(" ", "")
            extra_minute = True

        kind_tag = block.find("span", class_=lambda c: c and c.startswith("ico_gamecenter"))
        kind = kind_tag.get_text(strip=True) if kind_tag else ""

        if "교체" in kind or "change" in kind:
            txt_names = block.find_all("span", class_="txt_name")
            for name_tag in txt_names:
                main_name = name_tag.find("span", class_="txt_g")
                player = main_name.get_text(strip=True) if main_name else ""
                sub = name_tag.find("span", class_="txt_sub") or name_tag.find("em", class_="txt_sub")
                sub_text = sub.get_text(strip=True) if sub else ""
                num = ""
                if '.' in player:
                    num, name = player.split('.', 1)
                    num = num.strip(); name = name.strip()
                else:
                    name = player.strip()
                if "(IN)" in sub_text:
                    events.append(f"{minute} {num} {name} (IN)")
                elif "(OUT)" in sub_text:
                    events.append(f"{minute} {num} {name} (OUT)")
        else:
            name_tag = block.find("span", class_="txt_name")
            player = ""
            sub_player = ""
            num = ""
            if name_tag:
                main_name = name_tag.find("span", class_="txt_g")
                player = main_name.get_text(strip=True) if main_name else ""
                if '.' in player:
                    num, name = player.split('.', 1)
                    num = num.strip(); name = name.strip()
                else:
                    name = player.strip()
                sub = name_tag.find("span", class_="txt_sub") or name_tag.find("em", class_="txt_sub")
                if sub:
                    sub_player = sub.get_text(strip=True)
            else:
                if kind in ("경기종료", "전반종료"):
                    events.append(f"[{kind}]")
                    continue

            if kind in ("경기종료", "전반종료"):
                events.append(f"[{kind}]")
            elif extra_minute and "추가시간" in minute:
                events.append(minute)
            elif kind == "골":
                event_str = f"{minute} {num} {name} (득점)"
                events.append(event_str)
                if sub_player and "도움" in sub_player:
                    import re
                    clean_name = re.sub(r"[\(\)\s]*도움[\)\(\s]*", "", sub_player)
                    clean_name = clean_name.strip()
                    if clean_name:
                        events.append(f"    {clean_name} (도움)")
            elif "경고" in kind:
                events.append(f"{minute} {num} {name} (경고)")
            elif "퇴장" in kind:
                events.append(f"{minute} {num} {name} (퇴장)")
            elif player:
                events.append(f"{minute} {num} {name} ({kind})")
    return events

def map_player_events(events):
    event_map = {}
    for evt in events:
        m = re.match(r".*?(\d*)\s*([^\s]+)\s*\((.*?)\)", evt)
        if not m:
            continue
        num, name, kind = m.groups()
        name = name.replace("(", "").replace(")", "").strip()
        if "득점" in kind:
            event_map.setdefault(name, []).append("goal")
        elif "도움" in kind:
            event_map.setdefault(name, []).append("assist")
        elif "경고" in kind:
            event_map.setdefault(name, []).append("yellow")
        elif "퇴장" in kind:
            event_map.setdefault(name, []).append("red")
    return event_map

def extract_substitutions(events):
    subs = []
    in_queue = []
    out_queue = []
    for evt in events:
        m = re.match(r"(.*?)(\d*)\s*([^\s]+)\s*\((IN|OUT)\)", evt)
        if not m: continue
        minute, num, name, kind = m.groups()
        name = name.replace("(", "").replace(")", "").strip()
        if kind == "OUT":
            out_queue.append((name, num, minute))
        elif kind == "IN":
            in_queue.append((name, num, minute))
        if len(in_queue) and len(out_queue):
            out_name, out_num, minute_out = out_queue.pop(0)
            in_name, in_num, minute_in = in_queue.pop(0)
            subs.append((out_name, out_num, in_name, in_num, minute_in))
    sub_in_players = {in_name for (_,_,in_name,_,_) in subs}
    return subs, sub_in_players

def hex_to_rgb(hex_color):
    hex_color = hex_color.strip().lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def extract_svg_color(svg):
    if svg:
        for path in svg.find_all('path'):
            if path.has_attr("fill") and path["fill"].startswith("#"):
                return path["fill"]
            if path.has_attr("style"):
                m = re.search(r'fill:\s*(#[0-9a-fA-F]{6})', path["style"])
                if m:
                    return m.group(1)
    return None

def colorize_shirt(template_path, shirt_color, size=SHIRT_SIZE, threshold=220):
    img = Image.open(template_path).convert("RGBA")
    img = img.resize(size)
    datas = img.getdata()
    newData = []
    for item in datas:
        if item[3] == 0:
            newData.append(item)
        elif all(x >= threshold for x in item[:3]):
            newData.append(shirt_color + (255,))
        else:
            newData.append(item)
    img.putdata(newData)
    return img

def get_lineup_data(url, shirt_template="shirt_transparent.png"):
    options = Options()
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(2.5)
    html = driver.page_source
    driver.quit()
    soup = BeautifulSoup(html, "html.parser")

    lineup_groups = soup.find_all('div', class_='group_lineup')
    if len(lineup_groups) != 2:
        raise Exception("라인업 파싱 실패: 홈/원정팀 정보 부족!")

    teams = []
    svg_colors = []
    for idx, group in enumerate(lineup_groups):
        team_name = group.find('strong', class_='tit_team').text.strip()
        formation_text = group.find('span', class_='txt_lineup').get_text(strip=True)
        formation = re.search(r'(\d+\-\d+(?:\-\d+)*)', formation_text)
        formation = formation.group(1) if formation else "알수없음"
        svg = group.find('svg')
        fill = extract_svg_color(svg)
        if fill:
            team_rgb = hex_to_rgb(fill)
        else:
            team_rgb = (220,40,40) if idx == 0 else (30,80,210)
        svg_colors.append(team_rgb)
        players = []
        player_blocks = group.find_all('div', class_='lineup_player')
        for block in player_blocks:
            for li in block.find_all('li', attrs={'data-tiara-layer': 'player'}):
                txt_name = li.find('span', class_='txt_name').text.strip()
                if '.' in txt_name:
                    num, name = txt_name.split('.', 1)
                    num = num.strip(); name = name.strip()
                else:
                    num, name = "", txt_name
                players.append([num, name])
        teams.append({
            "team_name": team_name,
            "formation": formation,
            "players": players
        })
    return teams[0], teams[1], svg_colors

def apply_substitutions(players, subs):
    players_new = players[:]
    for (out_name, out_num, in_name, in_num, min_str) in subs:
        idx = next((k for k, v in enumerate(players_new) if v[1] == out_name), None)
        if idx is not None:
            num = in_num if in_num else ""
            players_new[idx] = [num, in_name]
    return players_new


def draw_event_icons_on_shirt(canvas, x, y, events, icon_imgs, icon_size=ICON_SIZE):
    icon_start_x = x + SHIRT_SIZE[0]//2 + 2
    icon_start_y = y - SHIRT_SIZE[1]//2 + 2
    for i, evt in enumerate(events):
        this_icon_size = (int(icon_size[0]*1.5), int(icon_size[1]*1.5)) if evt == "assist" else icon_size
        img = icon_imgs[evt]
        img_resized = resize_with_aspect(img, this_icon_size)
        img_tk = ImageTk.PhotoImage(img_resized)
        icon_x = icon_start_x
        icon_y = icon_start_y + i * (img_resized.height + ICON_GAP)
        canvas.create_image(icon_x, icon_y, image=img_tk, anchor='nw')
        if not hasattr(canvas, 'event_img_refs'):
            canvas.event_img_refs = []
        canvas.event_img_refs.append(img_tk)

# ====== 포메이션 그리기 ======
def visualize_formation_with_shirt(team, top, bottom, canvas, width, shirt_color, shirt_template_path, reverse_order, event_map, icon_imgs, sub_in_players):
    formation_list = [int(x) for x in team["formation"].split('-')]
    players = team["players"]
    if not players or len(players) < sum(formation_list)+1:
        return
    gk = players[0]
    outfield = players[1:]

    idx = 0
    lines = []
    for cnt in formation_list:
        line = outfield[idx:idx+cnt]
        if reverse_order:
            line = list(reversed(line))
        lines.append(line)
        idx += cnt

    n_lines = len(lines) + 1
    h_per_line = (bottom - top) // (n_lines + 1)

    canvas.create_text(width//2, top+8, text=f"{team['team_name']} ({team['formation']})", fill="#fff", font=("맑은 고딕", 18, "bold"))

    # 골키퍼
    x = width // 2
    y = bottom - h_per_line//2
    gk_img = colorize_shirt(shirt_template_path, (255, 225, 50), size=SHIRT_SIZE)
    if gk[1] in sub_in_players:
        gk_img = draw_shirt_with_real_border(gk_img)
    gk_img_tk = ImageTk.PhotoImage(gk_img)
    canvas.create_image(x, y, image=gk_img_tk)
    canvas.create_text(x, y, text=gk[0], fill="black", font=("맑은 고딕", 18, "bold"))
    canvas.create_text(x, y+NAME_Y_SHIFT, text=gk[1], fill="#fff", font=("맑은 고딕", NAME_FONT_SIZE))
    if not hasattr(canvas, 'img_refs'): canvas.img_refs = []
    canvas.img_refs.append(gk_img_tk)

    for i, line in enumerate(reversed(lines)):
        n = len(line)
        y = top + h_per_line*(i+1)
        for j, player in enumerate(line):
            num, name = player
            x = width//(n+1)*(j+1)
            img = colorize_shirt(shirt_template_path, shirt_color, size=SHIRT_SIZE)
            if name in sub_in_players:
                img = draw_shirt_with_real_border(img)
            img_tk = ImageTk.PhotoImage(img)
            canvas.create_image(x, y, image=img_tk)
            canvas.create_text(x, y, text=num, fill="black", font=("맑은 고딕", 15, "bold"))
            canvas.create_text(x, y+NAME_Y_SHIFT, text=name, fill="#fff", font=("맑은 고딕", NAME_FONT_SIZE))
            canvas.img_refs.append(img_tk)
            events = event_map.get(name, [])
            draw_event_icons_on_shirt(canvas, x, y, events, icon_imgs)


if __name__ == "__main__":
    url = "https://sports.news.naver.com/wfootball/gamecenter/index?gameId=202406080123"
    shirt_template_path = "shirt_transparent.png"
    goal_path = "goal.png"
    assist_path = "assist.png"

    team1, team2, svg_colors = get_lineup_data(url, shirt_template_path)
    events = get_events_data(url)
    subs, sub_in_players = extract_substitutions(events)
    team1["players"] = apply_substitutions(team1["players"], subs)
    team2["players"] = apply_substitutions(team2["players"], subs)
    event_map = map_player_events(events)

    icon_imgs = {
        "goal": Image.open(goal_path),
        "assist": Image.open(assist_path),
        "yellow": make_card_icon((255, 235, 59)),
        "red": make_card_icon((230, 20, 20))
    }

    width, height = 10000, 16000
    root = tk.Tk()
    root.geometry(f"{width}x{height}")  
    c = tk.Canvas(root, width=width, height=height, bg="#1a273a")
    c.pack()

    mid = height // 2

    visualize_formation_with_shirt(
    team1, top=100, bottom=mid-100, canvas=c, width=width,
    shirt_color=svg_colors[0], shirt_template_path=shirt_template_path,
    reverse_order=False, event_map=event_map, icon_imgs=icon_imgs, sub_in_players=sub_in_players
    )
    visualize_formation_with_shirt(
        team2, top=mid+100, bottom=height-100, canvas=c, width=width,
        shirt_color=svg_colors[1], shirt_template_path=shirt_template_path,
        reverse_order=True, event_map=event_map, icon_imgs=icon_imgs, sub_in_players=sub_in_players
    )

    root.mainloop()
