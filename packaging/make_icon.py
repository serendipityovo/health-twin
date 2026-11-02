"""生成应用图标：医用蓝圆角方块 + 白十字（Pillow 绘制，避免引入字体/图片资产）。"""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent / "app_icon.ico"


def draw(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 医用蓝渐变近似：底色深蓝，叠加浅蓝圆角层
    radius = int(size * 0.22)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=(37, 99, 235, 255))
    d.rounded_rectangle(
        [int(size * 0.08), int(size * 0.08), size - int(size * 0.30), size - int(size * 0.30)],
        radius=radius, fill=(59, 130, 246, 120),
    )
    # 白十字
    w = int(size * 0.20)   # 臂宽
    l = int(size * 0.22)   # 边距
    d.rounded_rectangle(
        [(size - w) // 2, l, (size + w) // 2, size - l], radius=int(w * 0.3), fill=(255, 255, 255, 255)
    )
    d.rounded_rectangle(
        [l, (size - w) // 2, size - l, (size + w) // 2], radius=int(w * 0.3), fill=(255, 255, 255, 255)
    )
    return img


sizes = [(s, s) for s in (16, 24, 32, 48, 64, 128, 256)]
base = draw(256)
base.save(OUT, format="ICO", sizes=sizes)
print(f"icon -> {OUT}")
