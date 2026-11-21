#!/usr/bin/env python3
"""VELMARA — a travel poster for a place that isn't there.

Writes /output/entry.png (1024x1024, PNG, < 1 MiB).

Design philosophy "Moonlit Tide" (canvas-design method):
- One landmark, one promise: a natural stone arch framing a low golden moon
  over a calm sea, a single sailboat on the moon's light path. The stay it
  promises is a quiet night on a warm, moonlit coast.
- Limited palette: deep indigo sky, violet dusk, teal sea, pale gold moon.
- The name VELMARA is set large, legible, centred in the upper sky — the only
  text on the poster. No quotes, no stars, no other copy.
- Everything is drawn procedurally with Pillow; no network, no downloaded
  assets. The display font is bundled in this repo (SIL OFL).
"""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W = H = 1024
OUT = os.environ.get("OUTPUT_PATH", "/output/entry.png")

# --- palette (limited, purposeful) ---
INK      = (12, 10, 30)      # deep indigo night
SKY_TOP  = (16, 14, 48)
SKY_MID  = (58, 38, 96)
DUSK     = (146, 74, 110)    # violet dusk band
EMBER    = (232, 138, 74)    # warm ember at the horizon
SEA_DEEP = (10, 42, 58)
SEA_LIT  = (24, 84, 96)
MOON     = (250, 222, 158)   # pale gold moon
MOON_CORE = (255, 244, 214)
CREAM    = (250, 238, 214)   # name type
ARCH     = (14, 12, 34)      # rock arch silhouette
GOLD     = (238, 178, 92)

random.seed(20261121)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def vertical_gradient(size, stops):
    """stops: list of (position 0..1, colour). Returns an RGB image."""
    w, h = size
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        for i in range(len(stops) - 1):
            p0, c0 = stops[i]
            p1, c1 = stops[i + 1]
            if p0 <= t <= p1:
                f = 0 if p1 == p0 else (t - p0) / (p1 - p0)
                col = lerp(c0, c1, f)
                break
        else:
            col = stops[-1][1]
        for x in range(w):
            px[x, y] = col
    return img


def draw_stars(draw, n=140):
    for _ in range(n):
        x = random.uniform(0, W)
        y = random.uniform(0, H * 0.42)
        r = random.uniform(0.6, 1.8)
        a = random.randint(90, 230)
        # brighter stars higher up
        if y < H * 0.18 and random.random() < 0.25:
            r = random.uniform(1.6, 2.4)
            a = 255
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(255, 244, 220, a))


def draw_moon(base):
    """Moon with a soft halo, drawn on its own layer and blurred."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy, r = 512, 470, 118
    # halo
    d.ellipse([cx - r * 1.9, cy - r * 1.9, cx + r * 1.9, cy + r * 1.9],
              fill=(250, 210, 130, 46))
    d.ellipse([cx - r * 1.35, cy - r * 1.35, cx + r * 1.35, cy + r * 1.35],
              fill=(250, 214, 140, 70))
    halo = layer.filter(ImageFilter.GaussianBlur(28))
    base.alpha_composite(halo)
    # disc
    d2 = ImageDraw.Draw(base)
    d2.ellipse([cx - r, cy - r, cx + r, cy + r], fill=MOON + (255,))
    d2.ellipse([cx - r * 0.82, cy - r * 0.82, cx + r * 0.82, cy + r * 0.82],
               fill=MOON_CORE + (255,))
    # a few soft maria (darker patches, low alpha) — placed asymmetric so
    # they read as lunar seas, never as a face
    for (mx, my, mr) in [(-58, 6, 22), (44, -38, 17), (18, 52, 14),
                         (-12, -58, 12), (62, 30, 10)]:
        d2.ellipse([cx + mx - mr, cy + my - mr, cx + mx + mr, cy + my + mr],
                   fill=(226, 196, 138, 90))


def draw_arch(draw):
    """Natural stone arch silhouette on the right, framing the moon."""
    # A leaning arch: two pillars + a curved top, drawn as a thick arc band.
    # Outer arc and inner arc (the opening) share a centre below the horizon.
    cx, cy = 830, 640
    outer = 330
    inner = 235
    # pillars down to the sea
    draw.polygon([(cx - outer, cy), (cx - outer + 64, cy),
                  (cx - outer + 88, 640), (cx - outer - 8, 640)], fill=ARCH)
    draw.polygon([(cx + outer - 64, cy), (cx + outer, cy),
                  (cx + outer + 8, 640), (cx + outer - 88, 640)], fill=ARCH)
    # arch band: draw a thick arc by stamping circles along the arc
    for ang in range(180, 361, 2):
        rad = math.radians(ang)
        x = cx + outer * math.cos(rad)
        y = cy - outer * math.sin(rad) * 0.92
        draw.ellipse([x - 34, y - 34, x + 34, y + 34], fill=ARCH)
    # carve the opening (sea + sky show through)
    for ang in range(180, 361, 2):
        rad = math.radians(ang)
        x = cx + inner * math.cos(rad)
        y = cy - inner * math.sin(rad) * 0.92
        draw.ellipse([x - 30, y - 30, x + 30, y + 30], fill=(0, 0, 0, 0))
    # The carve above uses transparent fill which does not erase on RGBA
    # overlay; instead we redraw the opening by compositing a cut layer.
    return (cx, cy, outer, inner)


def draw_sea(base):
    """Sea with the moon's gold light path."""
    sea = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(sea)
    horizon = 640
    # sea body: vertical gradient
    for y in range(horizon, H):
        t = (y - horizon) / (H - horizon)
        col = lerp(SEA_LIT, SEA_DEEP, t)
        d.line([(0, y), (W, y)], fill=col + (255,))
    # horizon glow line
    d.line([(0, horizon), (W, horizon)], fill=(250, 200, 130, 160), width=2)
    # light path: shimmering horizontal dashes under the moon, widening down
    for y in range(horizon + 8, H - 6, 7):
        t = (y - horizon) / (H - horizon)
        half = 26 + t * 150
        cx = 512 + random.uniform(-6, 6)
        # a few dashes per row
        n = random.randint(2, 4)
        for _ in range(n):
            off = random.uniform(-half, half)
            w = random.uniform(14, 52) * (0.5 + t)
            a = random.randint(60, 170)
            x0 = cx + off - w / 2
            x1 = cx + off + w / 2
            d.line([(x0, y), (x1, y)], fill=(250, 206, 130, a), width=3)
    base.alpha_composite(sea)


def draw_boat(draw):
    """One small sailboat silhouette on the light path."""
    bx, by = 512, 792
    # hull
    draw.polygon([(bx - 34, by), (bx + 34, by), (bx + 22, by + 14),
                  (bx - 22, by + 14)], fill=(8, 8, 22))
    # mast
    draw.line([(bx, by), (bx, by - 62)], fill=(8, 8, 22), width=4)
    # sails (pale, catching the moon)
    draw.polygon([(bx + 3, by - 58), (bx + 3, by - 6), (bx + 30, by - 6)],
                 fill=(250, 232, 200))
    draw.polygon([(bx - 3, by - 48), (bx - 3, by - 6), (bx - 24, by - 6)],
                 fill=(232, 206, 168))
    # reflection
    draw.line([(bx - 20, by + 20), (bx + 20, by + 20)], fill=(250, 206, 130, 120), width=2)


def draw_name(draw):
    """The place name — the only text. Large, legible, upper sky."""
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "fonts", "BigShoulders-Bold.ttf"),
        os.path.join(here, "BigShoulders-Bold.ttf"),
    ]
    font = None
    for path in candidates:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, 148)
                break
            except Exception:
                pass
    if font is None:
        font = ImageFont.load_default()
    name = "VELMARA"
    # letter-spacing: draw letter by letter for a wide, poster feel
    spacing = 26
    widths = []
    total = 0
    for ch in name:
        bbox = draw.textbbox((0, 0), ch, font=font)
        w = bbox[2] - bbox[0]
        widths.append(w)
        total += w
    total += spacing * (len(name) - 1)
    x = (W - total) // 2
    y = 96
    # soft shadow for legibility against the sky
    for ch, w in zip(name, widths):
        draw.text((x + 3, y + 5), ch, font=font, fill=(10, 8, 26))
        x += w + spacing
    x = (W - total) // 2
    for ch, w in zip(name, widths):
        draw.text((x, y), ch, font=font, fill=CREAM)
        x += w + spacing
    # thin gold rule under the name
    rule_y = y + 168
    draw.line([(W // 2 - 90, rule_y), (W // 2 + 90, rule_y)],
              fill=GOLD + (255,), width=3)


def main():
    # sky
    img = vertical_gradient((W, H), [
        (0.0, SKY_TOP), (0.38, SKY_MID), (0.55, DUSK),
        (0.62, EMBER), (0.625, SEA_DEEP),
    ]).convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    draw_stars(d)
    img.alpha_composite(overlay)

    draw_moon(img)

    # arch: draw on a layer, then cut the opening with a mask
    arch_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ad = ImageDraw.Draw(arch_layer)
    draw_arch(ad)
    # cut the opening: erase an inner arch-shaped region
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    cx, cy, outer, inner = 830, 640, 330, 235
    for ang in range(180, 361, 2):
        rad = math.radians(ang)
        x = cx + inner * math.cos(rad)
        y = cy - inner * math.sin(rad) * 0.92
        md.ellipse([x - 30, y - 30, x + 30, y + 30], fill=255)
    # also clear below the inner arch down to the horizon (the opening)
    md.polygon([(cx - inner, cy), (cx + inner, cy),
                (cx + inner, 640), (cx - inner, 640)], fill=255)
    arch_layer.putalpha(Image.composite(
        Image.new("L", (W, H), 0), arch_layer.split()[3], mask))
    img.alpha_composite(arch_layer)

    draw_sea(img)

    # foreground silhouette: low headland at the bottom corners
    fd = ImageDraw.Draw(img)
    fd.polygon([(0, H), (0, 968), (180, 930), (330, 962), (300, H)], fill=(8, 8, 20))
    fd.polygon([(W, H), (W, 972), (880, 940), (760, 966), (720, H)], fill=(8, 8, 20))

    draw_boat(fd)
    draw_name(fd)

    # gentle vignette
    vig = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vig)
    vd.ellipse([-220, -220, W + 220, H + 220], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(180))
    black = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    img = Image.composite(img, Image.composite(img, black, vig), vig)
    # simpler: darken edges by compositing black with inverted vignette
    inv = Image.new("L", (W, H), 0)
    # (vignette already soft; keep the image as is)

    out = img.convert("RGB")
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    out.save(OUT, "PNG", optimize=True)
    print("wrote", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
