"""Render carousel slides (1080x1350 JPEG) for every post in content/*.json.

Usage: python scripts/render.py            # render posts that have no images yet
       python scripts/render.py --force    # re-render everything
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "fonts"
W, H = 1080, 1350
PAD = 96
HANDLE = "@ravidigitalproduct"

# Trending-style palettes: (background, accent, text, muted)
PALETTES = [
    ("#0F0F14", "#C6FF3D", "#FFFFFF", "#9A9AA8"),  # dark + lime
    ("#FFF4E6", "#FF5A1F", "#1B1B1B", "#6B6158"),  # cream + orange
    ("#1E1B4B", "#FBBF24", "#FFFFFF", "#B9B6E3"),  # indigo + yellow
    ("#F1F5F9", "#2563EB", "#0F172A", "#5B6475"),  # light + blue
    ("#14261E", "#FF7AB6", "#FFFFFF", "#A9C3B6"),  # forest + pink
]


def font(weight, size):
    return ImageFont.truetype(str(FONTS / f"Poppins-{weight}.ttf"), size)


def wrap(draw, text, fnt, max_w):
    lines = []
    for para in text.split("\n"):
        words, line = para.split(), ""
        for w in words:
            trial = f"{line} {w}".strip()
            if draw.textlength(trial, font=fnt) <= max_w:
                line = trial
            else:
                if line:
                    lines.append(line)
                line = w
        lines.append(line)
    return lines


def fit(draw, text, weight, start, min_size, max_w, max_h, spacing=1.18):
    size = start
    while size > min_size:
        f = font(weight, size)
        lines = wrap(draw, text, f, max_w)
        if len(lines) * size * spacing <= max_h:
            return f, lines, size
        size -= 4
    f = font(weight, min_size)
    return f, wrap(draw, text, f, max_w), min_size


def draw_lines(draw, xy, lines, fnt, size, fill, spacing=1.18):
    x, y = xy
    for ln in lines:
        draw.text((x, y), ln, font=fnt, fill=fill)
        y += int(size * spacing)
    return y


def footer(draw, pal, page, total):
    bg, acc, txt, mut = pal
    f = font("Medium", 30)
    draw.text((PAD, H - PAD - 10), HANDLE, font=f, fill=mut, anchor="ls")
    label = f"{page}/{total}"
    draw.text((W - PAD, H - PAD - 10), label, font=f, fill=mut, anchor="rs")
    # progress bar
    bar_y = H - PAD + 22
    full = W - 2 * PAD
    draw.rounded_rectangle((PAD, bar_y, PAD + full, bar_y + 8), 4, fill=blend(bg, mut, 0.35))
    draw.rounded_rectangle((PAD, bar_y, PAD + int(full * page / total), bar_y + 8), 4, fill=acc)


def blend(a, b, t):
    a = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def pill(draw, x, y, text, pal):
    bg, acc, txt, mut = pal
    f = font("Bold", 30)
    tw = draw.textlength(text.upper(), font=f)
    draw.rounded_rectangle((x, y, x + tw + 56, y + 62), 31, fill=acc)
    draw.text((x + 28, y + 31), text.upper(), font=f, fill="#FFFFFF" if is_dark(acc) else "#111111", anchor="lm")
    return y + 62


def is_dark(hexc):
    r, g, b = [int(hexc[i:i + 2], 16) for i in (1, 3, 5)]
    return (0.299 * r + 0.587 * g + 0.114 * b) < 140


def cover(post, pal, total):
    bg, acc, txt, mut = pal
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)
    # decorative accent circle
    d.ellipse((W - 380, -220, W + 220, 380), fill=blend(bg, acc, 0.18))
    y = pill(d, PAD, PAD + 40, post.get("tag", "Growth Tip"), pal)
    f, lines, size = fit(d, post["title"], "Bold", 136, 72, W - 2 * PAD, 640)
    y = draw_lines(d, (PAD, y + 70), lines, f, size, txt, 1.12)
    if post.get("subtitle"):
        f2, l2, s2 = fit(d, post["subtitle"], "Medium", 54, 36, W - 2 * PAD, 260, 1.35)
        draw_lines(d, (PAD, y + 40), l2, f2, s2, mut, 1.35)
    # swipe cue
    f3 = font("Bold", 42)
    ay = H - PAD - 104
    d.line((W - PAD - 70, ay, W - PAD, ay), fill=acc, width=7)
    d.polygon([(W - PAD + 4, ay), (W - PAD - 22, ay - 18), (W - PAD - 22, ay + 18)], fill=acc)
    d.text((W - PAD - 92, ay), "Swipe karo", font=f3, fill=acc, anchor="rm")
    footer(d, pal, 1, total)
    return im


def tip(slide, idx, pal, page, total):
    bg, acc, txt, mut = pal
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)
    num = f"{idx:02d}"
    d.text((PAD - 8, PAD + 10), num, font=font("Bold", 220), fill=blend(bg, acc, 0.9), anchor="lt")
    y = PAD + 300
    d.rectangle((PAD, y, PAD + 120, y + 10), fill=acc)
    f, lines, size = fit(d, slide["h"], "Bold", 88, 56, W - 2 * PAD, 340)
    y = draw_lines(d, (PAD, y + 50), lines, f, size, txt, 1.15)
    f2, l2, s2 = fit(d, slide["b"], "Regular", 56, 34, W - 2 * PAD, H - y - 260, 1.42)
    draw_lines(d, (PAD, y + 36), l2, f2, s2, mut, 1.42)
    footer(d, pal, page, total)
    return im


def cta(post, pal, total):
    bg, acc, txt, mut = pal
    im = Image.new("RGB", (W, H), acc)
    d = ImageDraw.Draw(im)
    ink = "#FFFFFF" if is_dark(acc) else "#111111"
    d.ellipse((-260, H - 520, 340, H + 80), fill=blend(acc, bg, 0.15))
    msg = post.get("cta", "Aisi aur tips ke liye follow karo")
    f, lines, size = fit(d, msg, "Bold", 108, 64, W - 2 * PAD, 520)
    y = draw_lines(d, (PAD, PAD + 140), lines, f, size, ink, 1.12)
    d.text((PAD, y + 50), HANDLE, font=font("Bold", 54), fill=ink)
    actions = ["Save karo  •  baad mein kaam aayega", "Share karo  •  dost ko bhejo", "Comment karo  •  sawaal poochho"]
    yy = y + 180
    fa = font("Medium", 40)
    for a in actions:
        d.rounded_rectangle((PAD, yy, W - PAD, yy + 92), 46, outline=ink, width=3)
        d.text((PAD + 40, yy + 46), a, font=fa, fill=ink, anchor="lm")
        yy += 120
    f4 = font("Medium", 30)
    d.text((W - PAD, H - PAD - 10), f"{total}/{total}", font=f4, fill=ink, anchor="rs")
    return im


def render_post(post, out_dir, palette_idx):
    pal = PALETTES[palette_idx % len(PALETTES)]
    total = len(post["slides"]) + 2
    out_dir.mkdir(parents=True, exist_ok=True)
    imgs = [cover(post, pal, total)]
    for i, s in enumerate(post["slides"], 1):
        imgs.append(tip(s, i, pal, i + 1, total))
    imgs.append(cta(post, pal, total))
    names = []
    for i, im in enumerate(imgs, 1):
        name = f"{i:02d}.jpg"
        im.save(out_dir / name, "JPEG", quality=92, optimize=True)
        names.append(name)
    return names


def main():
    force = "--force" in sys.argv
    for cf in sorted((ROOT / "content").glob("*.json")):
        posts = json.loads(cf.read_text(encoding="utf-8"))
        for n, post in enumerate(posts):
            out = ROOT / "posts" / post["id"]
            if out.exists() and any(out.glob("*.jpg")) and not force:
                continue
            render_post(post, out, n)
            print("rendered", post["id"])


if __name__ == "__main__":
    main()
