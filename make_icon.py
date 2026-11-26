"""生成软件图标 app.ico（渐变圆角 + OT 字样）。仅打包时需要，用 Pillow。"""
import os
from PIL import Image, ImageDraw, ImageFont

SIZE = 256
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# 对角渐变底色
for y in range(SIZE):
    for x in range(SIZE):
        t = (x + y) / (2 * SIZE)
        r = int(0x5B + (0x7C - 0x5B) * t)
        g = int(0x8C + (0x5C - 0x8C) * t)
        b = int(0xFF + (0xFF - 0xFF) * t)
        d.point((x, y), fill=(r, g, b, 255))

# 圆角遮罩
mask = Image.new("L", (SIZE, SIZE), 0)
ImageDraw.Draw(mask).rounded_rectangle((0, 0, SIZE - 1, SIZE - 1), radius=56, fill=255)
img.putalpha(mask)

# OT 文字
try:
    font = ImageFont.truetype("C:/Windows/Fonts/seguisb.ttf", 112)
except OSError:
    font = ImageFont.load_default()
d = ImageDraw.Draw(img)
text = "OT"
box = d.textbbox((0, 0), text, font=font)
w, h = box[2] - box[0], box[3] - box[1]
d.text(((SIZE - w) / 2 - box[0], (SIZE - h) / 2 - box[1] - 6), text,
       font=font, fill=(255, 255, 255, 255))

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.ico")
img.save(out, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
print("saved", out)
