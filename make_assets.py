#!/usr/bin/env python3
"""Draw the favicon set and OG card into static/ (needs Pillow). Rerun only when the mark changes."""
import os
from PIL import Image, ImageDraw, ImageFont

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
GREEN, WHITE, INK, SLATE = (4, 120, 87), (255, 255, 255), (15, 23, 42), (71, 85, 105)
FONTS = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/HelveticaNeue.ttc",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
# paw print on a 64-unit grid: (cx, cy, rx, ry)
PAW = [(32, 41, 12, 10), (16, 29, 5, 6.5), (26, 19, 5, 6.5), (38, 19, 5, 6.5), (48, 29, 5, 6.5)]

SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#047857"/>'
       + "".join(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="#fff"/>' for x, y, rx, ry in PAW) + "</svg>\n")


def font(size):
    for p in FONTS:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def mark(px):
    s = px * 4
    u = s / 64
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=int(14 * u), fill=GREEN)
    for x, y, rx, ry in PAW:
        d.ellipse([(x - rx) * u, (y - ry) * u, (x + rx) * u, (y + ry) * u], fill=WHITE)
    return img.resize((px, px), Image.LANCZOS)


def main():
    open(os.path.join(STATIC, "favicon.svg"), "w").write(SVG)
    for name, px in (("apple-touch-icon.png", 180), ("icon-192.png", 192), ("icon-512.png", 512)):
        mark(px).save(os.path.join(STATIC, name), optimize=True)
    mark(48).save(os.path.join(STATIC, "favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48)])
    og = Image.new("RGB", (1200, 630), (236, 253, 245))
    d = ImageDraw.Draw(og)
    d.rectangle([0, 0, 1200, 14], fill=GREEN)
    og.paste(mark(132), (90, 96), mark(132))
    d.text((250, 110), "Animal", font=font(100), fill=INK)
    d.text((250 + d.textlength("Animal", font=font(100)), 110), "Stats", font=font(100), fill=GREEN)
    d.text((90, 300), "Animal facts, in numbers", font=font(64), fill=INK)
    for i, label in enumerate(("LIFESPAN", "SIZE", "SPEED", "STATUS")):
        x = 90 + i * 258
        d.rounded_rectangle([x, 420, x + 236, 530], radius=22, fill=WHITE, outline=GREEN, width=4)
        d.text((x + 118, 475), label, font=font(36), fill=GREEN, anchor="mm")
    d.text((90, 560), "animalstats.org", font=font(34), fill=SLATE)
    og.save(os.path.join(STATIC, "og-default.png"), optimize=True)
    print("assets written")


if __name__ == "__main__":
    main()
