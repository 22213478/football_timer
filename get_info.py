from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import tkinter as tk
from PIL import Image, ImageTk
import time
import re

# hex → rgb
def hex_to_rgb(hex_color):
    hex_color = hex_color.strip().lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

# SVG에서 path의 fill 색상 추출
def extract_svg_color(svg):
    if svg:
        for path in svg.find_all('path'):
            if path.has_attr("fill") and path["fill"].startswith("#"):
                return path["fill"]
            # style="fill:#xxxxxx"
            if path.has_attr("style"):
                m = re.search(r'fill:\s*(#[0-9a-fA-F]{6})', path["style"])
                if m:
                    return m.group(1)
    return None

# 셔츠 색 입히기 (투명 PNG 템플릿 필요)
def colorize_shirt(template_path, shirt_color, size=(44, 44), threshold=220):
    img = Image.open(template_path).convert("RGBA")
    img = img.resize(size)
    datas = img.getdata()
    newData = []
    for item in datas:
        # 흰색·밝은색은 유니폼 컬러로 덮고, 나머지는 투명/외곽선 유지
        if item[3] == 0:  # 완전 투명
            newData.append(item)
        elif all(x >= threshold for x in item[:3]):  # 밝은 부분
            newData.append(shirt_color + (255,))
        else:
            newData.append(item)
    img.putdata(newData)
    return img

# 라인업 파싱 (SVG 컬러 포함)
def get_lineup_data(url, shirt_template="shirt_transparent.png"):
    # Selenium으로 동적 HTML 렌더링 후 파싱!
    options = Options()
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(2.5)  # JS 렌더 대기
    html = driver.page_source
    driver.quit()
    soup = BeautifulSoup(html, "html.parser")

    lineup_groups = soup.find_all('div', class_='group_lineup')
    if len(lineup_groups) != 2:
        raise Exception("라인업 파싱 실패: 홈/원정팀 정보 부족!")

    teams = []
    svg_colors = []
    for idx, group in enumerate(lineup_groups):
        # 1. 팀명·포메이션
        team_name = group.find('strong', class_='tit_team').text.strip()
        formation_text = group.find('span', class_='txt_lineup').get_text(strip=True)
        formation = re.search(r'(\d+\-\d+(?:\-\d+)*)', formation_text)
        formation = formation.group(1) if formation else "알수없음"

        # 2. SVG 유니폼 색상
        svg = group.find('svg')
        fill = extract_svg_color(svg)
        if fill:
            team_rgb = hex_to_rgb(fill)
        else:
            team_rgb = (220,40,40) if idx == 0 else (30,80,210)  # fallback
        svg_colors.append(team_rgb)

        # 3. 선수명·등번호 파싱 (골키퍼+필드 플레이어)
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

# 포메이션대로 중앙 정렬해서 셔츠/이름 출력
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

    # 팀명, 포메이션
    canvas.create_text(width//2, top+20, text=f"{team['team_name']} ({team['formation']})", fill="#fff", font=("맑은 고딕", 18, "bold"))

    # 골키퍼 셔츠 (노란색)
    gk_img = colorize_shirt(shirt_template_path, (255, 225, 50), size=(54, 54))
    gk_img_tk = ImageTk.PhotoImage(gk_img)
    x = width // 2
    y = bottom - h_per_line//2
    canvas.create_image(x, y, image=gk_img_tk)
    canvas.create_text(x, y, text=gk[0], fill="black", font=("맑은 고딕", 18, "bold"))
    canvas.create_text(x, y+36, text=gk[1], fill="#fff", font=("맑은 고딕", 13))
    if not hasattr(canvas, 'img_refs'): canvas.img_refs = []
    canvas.img_refs.append(gk_img_tk)

    # 필드 플레이어 셔츠
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

def main():
    # url 입력 없이 테스트용 경기 고정!
    url = "https://sports.daum.net/match/80085755?tab=lineup"
    shirt_template = "shirt_transparent.png"  # 투명 PNG 필요

    print("데이터를 가져오는 중... (약 2~4초)")
    home, away, colors = get_lineup_data(url, shirt_template)
    print("라인업 파싱 성공! 시각화 중...")

    width, height = 820, 900
    root = tk.Tk()
    root.title(f"라인업: {home['team_name']} vs {away['team_name']}")
    root.geometry(f"{width}x{height}")
    canvas = tk.Canvas(root, width=width, height=height, bg="#1a273a")
    canvas.pack()
    mid = height // 2

    visualize_formation_with_shirt(home, top=60, bottom=mid-10, canvas=canvas, width=width, shirt_color=colors[0], shirt_template_path=shirt_template, reverse_order=False)
    visualize_formation_with_shirt(away, top=mid+10, bottom=height-60, canvas=canvas, width=width, shirt_color=colors[1], shirt_template_path=shirt_template, reverse_order=True)

    root.mainloop()

if __name__ == "__main__":
    main()
