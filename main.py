#!/usr/bin/env python3
"""VELMARA — a travel poster for a place that isn't there.

Writes /output/entry.png (1024x1024, PNG, < 1 MiB).

PURE PYTHON STANDARD LIBRARY ONLY. The grader image is vanilla
python:3.13-slim: it ships no Pillow, no image libraries, no network.
So this program draws on a raw RGB pixel buffer and encodes the PNG
itself (zlib + struct + binascii, all stdlib). The display type is a
hand-set 5x7 bitmap font, scaled up — no font file needed.

Design philosophy "Moonlit Tide" (canvas-design method):
- One landmark, one promise: a low golden moon over a calm sea, a single
  sailboat on the moon's light path. The stay it promises is a quiet night
  on a warm, moonlit coast.
- Limited palette: deep indigo sky, violet dusk, teal sea, pale gold moon.
- The name VELMARA is set large, legible, centred in the upper sky — the
  only text on the poster. No quotes, no stars, no other copy.
"""
import binascii
import math
import os
import random
import struct
import zlib

W = H = 1024
OUT = os.environ.get("OUTPUT_PATH", "/output/entry.png")

INK = (12, 10, 30)
SKY_TOP = (16, 14, 48)
SKY_MID = (58, 38, 96)
DUSK = (146, 74, 110)
EMBER = (232, 138, 74)
SEA_DEEP = (10, 42, 58)
SEA_LIT = (24, 84, 96)
MOON = (250, 222, 158)
MOON_CORE = (255, 244, 214)
CREAM = (250, 238, 214)
GOLD = (238, 178, 92)

random.seed(20261121)

# --- pixel buffer -------------------------------------------------------
buf = bytearray(W * H * 3)


def set_px(x, y, col):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i] = col[0]
        buf[i + 1] = col[1]
        buf[i + 2] = col[2]


def blend_px(x, y, col, a):
    """Alpha-blend col over the pixel (a: 0..255)."""
    if 0 <= x < W and 0 <= y < H and a > 0:
        i = (y * W + x) * 3
        inv = 255 - a
        buf[i] = (col[0] * a + buf[i] * inv) // 255
        buf[i + 1] = (col[1] * a + buf[i + 1] * inv) // 255
        buf[i + 2] = (col[2] * a + buf[i + 2] * inv) // 255


def lerp(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def fill_circle(cx, cy, r, col, alpha=255):
    r2 = r * r
    for y in range(int(cy - r), int(cy + r) + 1):
        dy = y - cy
        dx = int(math.sqrt(max(r2 - dy * dy, 0)))
        for x in range(int(cx - dx), int(cx + dx) + 1):
            if alpha >= 255:
                set_px(x, y, col)
            else:
                blend_px(x, y, col, alpha)


def fill_poly(points, col):
    """Scanline fill of a simple polygon (list of (x, y))."""
    if not points:
        return
    ys = [p[1] for p in points]
    y0, y1 = int(min(ys)), int(max(ys))
    n = len(points)
    for y in range(y0, y1 + 1):
        xs = []
        for i in range(n):
            x0, ya = points[i]
            x1, yb = points[(i + 1) % n]
            if ya == yb:
                continue
            if (ya <= y < yb) or (yb <= y < ya):
                xs.append(x0 + (y - ya) * (x1 - x0) / (yb - ya))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            for x in range(int(xs[i]), int(xs[i + 1]) + 1):
                set_px(x, y, col)


def hline(x0, x1, y, col, alpha=255):
    for x in range(int(x0), int(x1) + 1):
        if alpha >= 255:
            set_px(x, y, col)
        else:
            blend_px(x, y, col, alpha)


# --- 5x7 bitmap font (only the letters VELMARA needs) -------------------
GLYPHS = {
    "V": ["#   #", "#   #", "#   #", "#   #", "#   #", " # # ", "  #  "],
    "E": ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#####"],
    "L": ["#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"],
    "M": ["#   #", "## ##", "# # #", "# # #", "#   #", "#   #", "#   #"],
    "A": [" ### ", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    "R": ["#### ", "#   #", "#   #", "#### ", "# #  ", "#  # ", "#   #"],
}


def draw_text(text, x0, y0, scale, col):
    x = x0
    for ch in text:
        g = GLYPHS.get(ch)
        if g is None:
            x += 6 * scale
            continue
        for row in range(7):
            for c in range(5):
                if g[row][c] == "#":
                    for dy in range(scale):
                        for dx in range(scale):
                            set_px(x + c * scale + dx, y0 + row * scale + dy, col)
        x += 6 * scale


def text_width(text, scale):
    return len(text) * 6 * scale - scale


# --- PNG encoder (stdlib only) ------------------------------------------
def png_chunk(typ, data):
    out = struct.pack(">I", len(data)) + typ + data
    out += struct.pack(">I", binascii.crc32(typ + data) & 0xFFFFFFFF)
    return out


def write_png(path, width, height, rgb):
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)  # filter: none
        raw += rgb[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    data = b"\x89PNG\r\n\x1a\n"
    data += png_chunk(b"IHDR", ihdr)
    data += png_chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    data += png_chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


# --- the poster ----------------------------------------------------------
def main():
    horizon = 640
    # sky gradient (per row)
    stops = [(0.0, SKY_TOP), (0.38, SKY_MID), (0.55, DUSK),
             (0.62, EMBER), (0.625, SEA_DEEP)]
    for y in range(H):
        t = y / (H - 1)
        col = stops[-1][1]
        for i in range(len(stops) - 1):
            p0, c0 = stops[i]
            p1, c1 = stops[i + 1]
            if p0 <= t <= p1:
                f = 0 if p1 == p0 else (t - p0) / (p1 - p0)
                col = lerp(c0, c1, f)
                break
        for x in range(W):
            set_px(x, y, col)

    # stars
    for _ in range(150):
        x = random.uniform(0, W)
        y = random.uniform(0, H * 0.42)
        r = random.uniform(0.6, 1.7)
        a = random.randint(90, 230)
        if y < H * 0.18 and random.random() < 0.25:
            r = random.uniform(1.6, 2.4)
            a = 255
        fill_circle(x, y, r, (255, 244, 220), a)

    # moon halo + disc (centre 512, 470, radius 118)
    cx, cy, r = 512, 470, 118
    fill_circle(cx, cy, r * 1.9, (250, 210, 130), 18)
    fill_circle(cx, cy, r * 1.35, (250, 214, 140), 30)
    fill_circle(cx, cy, r, MOON)
    fill_circle(cx, cy, r * 0.82, MOON_CORE)
    # maria: asymmetric, never a face
    for (mx, my, mr) in [(-58, 6, 22), (44, -38, 17), (18, 52, 14),
                         (-12, -58, 12), (62, 30, 10)]:
        fill_circle(cx + mx, cy + my, mr, (226, 196, 138), 90)

    # sea: gradient + horizon glow + light path
    for y in range(horizon, H):
        t = (y - horizon) / (H - horizon)
        col = lerp(SEA_LIT, SEA_DEEP, t)
        for x in range(W):
            set_px(x, y, col)
    hline(0, W - 1, horizon, (250, 200, 130), 160)
    for y in range(horizon + 8, H - 6, 7):
        t = (y - horizon) / (H - horizon)
        half = 26 + t * 150
        ccx = 512 + random.uniform(-6, 6)
        for _ in range(random.randint(2, 4)):
            off = random.uniform(-half, half)
            w = random.uniform(14, 52) * (0.5 + t)
            a = random.randint(60, 170)
            hline(ccx + off - w / 2, ccx + off + w / 2, y,
                  (250, 206, 130), a)

    # small rocky islet under the moon (the arch's top, kept as an island)
    fill_circle(512, 652, 26, (8, 8, 20))

    # foreground headlands, bottom corners
    fill_poly([(0, H), (0, 968), (180, 930), (330, 962), (300, H)], (8, 8, 20))
    fill_poly([(W, H), (W, 972), (880, 940), (760, 966), (720, H)], (8, 8, 20))

    # sailboat on the light path
    bx, by = 512, 792
    fill_poly([(bx - 34, by), (bx + 34, by), (bx + 22, by + 14),
               (bx - 22, by + 14)], (8, 8, 22))
    for y in range(by - 62, by + 1):
        set_px(bx, y, (8, 8, 22))
    fill_poly([(bx + 3, by - 58), (bx + 3, by - 6), (bx + 30, by - 6)],
              (250, 232, 200))
    fill_poly([(bx - 3, by - 48), (bx - 3, by - 6), (bx - 24, by - 6)],
              (232, 206, 168))
    hline(bx - 20, bx + 20, by + 20, (250, 206, 130), 120)

    # the name — the only text. Large, legible, upper sky.
    scale = 20
    name = "VELMARA"
    tw = text_width(name, scale)
    x0 = (W - tw) // 2
    y0 = 96
    draw_text(name, x0 + 4, y0 + 6, scale, (10, 8, 26))  # shadow
    draw_text(name, x0, y0, scale, CREAM)
    # thin gold rule under the name
    for y in range(y0 + 7 * scale + 22, y0 + 7 * scale + 25):
        hline(W // 2 - 90, W // 2 + 90, y, GOLD)

    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    n = write_png(OUT, W, H, buf)
    print("wrote", OUT, n, "bytes")


if __name__ == "__main__":
    main()
