#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generates all Chromium-required Vigil browser icons using pure Pillow.
Dark shield with a prominent vigilant eye. No native dependencies.
"""

import math
import sys
from pathlib import Path

def _bootstrap():
    import subprocess
    try:
        from PIL import Image
    except ImportError:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install',
                               '--break-system-packages', 'Pillow'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

_bootstrap()

from PIL import Image, ImageDraw, ImageFilter

SIZES = [16, 24, 32, 48, 64, 128, 256, 512]
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]


def shield_points(cx, cy, w, h):
    pts = []
    pts.append((cx, cy - h * 0.48))
    for t in [0.1, 0.2, 0.3]:
        pts.append((cx + w * (0.15 + t * 1.1), cy - h * (0.48 - t * 0.95)))
    pts.append((cx + w * 0.48, cy - h * 0.12))
    pts.append((cx + w * 0.47, cy + h * 0.05))
    pts.append((cx + w * 0.42, cy + h * 0.18))
    pts.append((cx + w * 0.34, cy + h * 0.30))
    pts.append((cx + w * 0.22, cy + h * 0.40))
    pts.append((cx, cy + h * 0.50))
    pts.append((cx - w * 0.22, cy + h * 0.40))
    pts.append((cx - w * 0.34, cy + h * 0.30))
    pts.append((cx - w * 0.42, cy + h * 0.18))
    pts.append((cx - w * 0.47, cy + h * 0.05))
    pts.append((cx - w * 0.48, cy - h * 0.12))
    for t in [0.3, 0.2, 0.1]:
        pts.append((cx - w * (0.15 + t * 1.1), cy - h * (0.48 - t * 0.95)))
    return pts


def almond_points(cx, cy, w, h, steps=120):
    pts = []
    for i in range(steps):
        t = i / steps * 2 * math.pi
        x = cx + w * math.cos(t)
        raw_sin = math.sin(t)
        sign = 1 if raw_sin >= 0 else -1
        y = cy - h * sign * abs(raw_sin) ** 1.4
        pts.append((x, y))
    return pts


def draw_vigil_icon(size):
    render_size = size * 2
    img = Image.new('RGBA', (render_size, render_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    s = render_size / 512.0
    cx, cy = render_size / 2, render_size / 2

    # Colors
    shield_blue = (45, 112, 220)
    inner_dark = (16, 24, 44)
    accent = (96, 165, 250)
    core_dark = (10, 16, 32)

    # --- Outer shield ---
    draw.polygon(shield_points(cx, cy, 430 * s, 440 * s), fill=shield_blue)

    # --- Inner shield ---
    draw.polygon(shield_points(cx, cy, 380 * s, 395 * s), fill=inner_dark)

    # --- Eye almond shape ---
    eye_w = 140 * s
    eye_h = 55 * s
    ew = max(2, int(4 * s))
    eye_pts = almond_points(cx, cy, eye_w, eye_h)

    # Dark fill inside the eye shape
    draw.polygon(eye_pts, fill=(12, 22, 50))

    # --- Iris ring (bright blue, the main visual element) ---
    iris_outer = 46 * s
    iris_inner = 22 * s

    # Outer glow ring
    if size >= 48:
        glow = Image.new('RGBA', (render_size, render_size), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gr = iris_outer + 8 * s
        gd.ellipse([cx - gr, cy - gr, cx + gr, cy + gr], fill=(60, 140, 255, 40))
        glow = glow.filter(ImageFilter.GaussianBlur(radius=max(1, int(10 * s))))
        img = Image.alpha_composite(img, glow)
        draw = ImageDraw.Draw(img)

    # Iris gradient - concentric rings from deep blue to bright blue
    for i in range(int(iris_outer), 0, -1):
        t = i / iris_outer
        # Deep blue at edge -> bright electric blue toward center
        r = int(20 + 60 * (1 - t))
        g = int(60 + 110 * (1 - t))
        b = int(180 + 75 * (1 - t))
        draw.ellipse([cx - i, cy - i, cx + i, cy + i], fill=(r, g, b))

    # --- Pupil ---
    draw.ellipse([cx - iris_inner, cy - iris_inner, cx + iris_inner, cy + iris_inner],
                 fill=core_dark)

    # --- Highlights ---
    hl_r = 7 * s
    hl_x, hl_y = cx - 12 * s, cy - 12 * s
    draw.ellipse([hl_x - hl_r, hl_y - hl_r, hl_x + hl_r, hl_y + hl_r],
                 fill=(255, 255, 255, 210))

    hl2_r = 3.5 * s
    hl2_x, hl2_y = cx + 9 * s, cy + 7 * s
    draw.ellipse([hl2_x - hl2_r, hl2_y - hl2_r, hl2_x + hl2_r, hl2_y + hl2_r],
                 fill=(255, 255, 255, 90))

    # --- Eye outline (drawn last, on top) ---
    draw.polygon(eye_pts, outline=accent, width=ew)

    # --- Thin accent line at iris equator for "scanning" effect ---
    if size >= 64:
        lw = max(1, int(1.5 * s))
        draw.line([(cx - eye_w * 0.92, cy), (cx - iris_outer - 4 * s, cy)],
                  fill=(96, 165, 250, 80), width=lw)
        draw.line([(cx + iris_outer + 4 * s, cy), (cx + eye_w * 0.92, cy)],
                  fill=(96, 165, 250, 80), width=lw)

    # Downsample with LANCZOS
    img = img.resize((size, size), Image.LANCZOS)
    return img


def main():
    root = Path(__file__).resolve().parent
    icons_dir = root / 'icons'
    icons_dir.mkdir(exist_ok=True)

    images = {}
    for size in SIZES:
        img = draw_vigil_icon(size)
        images[size] = img
        img.save(icons_dir / f'vigil_{size}.png', 'PNG')
        img.save(icons_dir / f'product_logo_{size}.png', 'PNG')
        print(f'  Generated vigil_{size}.png')

    # Windows .ico
    ico_path = icons_dir / 'vigil.ico'
    ico_imgs = [images[s].copy() for s in ICO_SIZES]
    ico_imgs[0].save(
        ico_path, format='ICO',
        append_images=ico_imgs[1:],
        sizes=[(s, s) for s in ICO_SIZES]
    )
    print(f'  Generated vigil.ico')

    print(f'\nAll icons generated in {icons_dir}/')


if __name__ == '__main__':
    main()
