from PIL import Image

def make_shirt_transparent(src_path, save_path, threshold=240):
    img = Image.open(src_path).convert("RGBA")
    datas = img.getdata()
    newData = []
    for item in datas:
        # 거의 흰색(R,G,B 모두 threshold 이상) → 완전 투명
        if all(x >= threshold for x in item[:3]):
            newData.append((255,255,255,0))
        else:
            newData.append(item)
    img.putdata(newData)
    img.save(save_path)

# 사용 예시
make_shirt_transparent("shirt.jpg", "shirt_transparent.png")
