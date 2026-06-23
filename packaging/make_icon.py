"""Build assets/icon.ico from assets/logo_src.png with the flat background removed.

ponytail: corner flood-fill removes only the connected outer background, so the
white search bar / traffic-light dots inside the windows survive. A global
"white -> transparent" would eat those too. Run: python packaging/make_icon.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
src = Image.open(ROOT / "assets" / "logo_src.png").convert("RGBA")

w, h = src.size
for seed in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
    ImageDraw.floodfill(src, seed, (0, 0, 0, 0), thresh=60)

src = src.crop(src.getbbox())  # trim to the visible logo
side = max(src.size)
square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
square.paste(src, ((side - src.width) // 2, (side - src.height) // 2))

square.save(ROOT / "assets" / "icon.png")
square.save(
    ROOT / "assets" / "icon.ico",
    sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
)
print("wrote assets/icon.ico + assets/icon.png", square.size)
