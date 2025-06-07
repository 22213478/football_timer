from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from PIL import Image, ImageTk
import time
import re

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
        # 시간/추가시간
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

        # 교체 이벤트면 txt_name을 모두 찾음
        if "교체" in kind or "change" in kind:
            txt_names = block.find_all("span", class_="txt_name")
            for name_tag in txt_names:
                main_name = name_tag.find("span", class_="txt_g")
                player = main_name.get_text(strip=True) if main_name else ""
                # txt_sub가 span, em 어느 쪽이든 잡기
                sub = name_tag.find("span", class_="txt_sub") or name_tag.find("em", class_="txt_sub")
                sub_text = sub.get_text(strip=True) if sub else ""
                if "(IN)" in sub_text:
                    events.append(f"{minute} {player} (IN)")
                elif "(OUT)" in sub_text:
                    events.append(f"    {player} (OUT)")
        else:
            # 득점, 경고, 퇴장 등: txt_g + (txt_sub)
            name_tag = block.find("span", class_="txt_name")
            player = ""
            sub_player = ""
            if name_tag:
                main_name = name_tag.find("span", class_="txt_g")
                player = main_name.get_text(strip=True) if main_name else ""
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
                event_str = f"{minute} {player} (득점)"
                events.append(event_str)
                if sub_player and "도움" in sub_player:
                    # 괄호/도움/공백 등 모두 지우고 선수 이름만 남기기
                    import re
                    clean_name = re.sub(r"[\(\)\s]*도움[\)\(\s]*", "", sub_player)
                    clean_name = clean_name.strip()
                    # 이름이 아예 없으면 그냥 출력 안함
                    if clean_name:
                        events.append(f"    {clean_name} (도움))")

            elif "경고" in kind:
                events.append(f"{minute} {player} (경고)")
            elif "퇴장" in kind:
                events.append(f"{minute} {player} (퇴장)")
            elif player:
                events.append(f"{minute} {player} ({kind})")

    return events

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

def colorize_shirt(template_path, shirt_color, size=(44, 44), threshold=220):
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
                    num = num.strip()
                    name = name.strip()
                else:
                    num, name = "", txt_name
                players.append([num, name])
        teams.append({
            "team_name": team_name,
            "formation": formation,
            "players": players
        })
    return teams[0], teams[1], svg_colors

def visualize_formation_with_shirt(team, top, bottom, canvas, width, shirt_color, shirt_template_path, reverse_order=False):
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

    canvas.create_text(width//2, top+20, text=f"{team['team_name']} ({team['formation']})", fill="#fff", font=("맑은 고딕", 18, "bold"))

    gk_img = colorize_shirt(shirt_template_path, (255, 225, 50), size=(54, 54))
    gk_img_tk = ImageTk.PhotoImage(gk_img)
    x = width // 2
    y = bottom - h_per_line//2
    canvas.create_image(x, y, image=gk_img_tk)
    canvas.create_text(x, y, text=gk[0], fill="black", font=("맑은 고딕", 18, "bold"))
    canvas.create_text(x, y+36, text=gk[1], fill="#fff", font=("맑은 고딕", 13))
    if not hasattr(canvas, 'img_refs'): canvas.img_refs = []
    canvas.img_refs.append(gk_img_tk)

    for i, line in enumerate(reversed(lines)):
        n = len(line)
        y = top + h_per_line*(i+1)
        for j, player in enumerate(line):
            num, name = player
            x = width//(n+1)*(j+1)
            field_img = colorize_shirt(shirt_template_path, shirt_color, size=(44, 44))
            field_img_tk = ImageTk.PhotoImage(field_img)
            canvas.create_image(x, y, image=field_img_tk)
            canvas.create_text(x, y, text=num, fill="black", font=("맑은 고딕", 15, "bold"))
            canvas.create_text(x, y+24, text=name, fill="#fff", font=("맑은 고딕", 10))
            canvas.img_refs.append(field_img_tk)
