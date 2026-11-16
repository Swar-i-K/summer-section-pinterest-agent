from __future__ import annotations
import io
import re
from pathlib import Path
from urllib.parse import urlparse
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1000, 1500
DEFAULT_DOMAIN = "summersection.com"
MIN_BG_SIDE = 500          # article images smaller than this (icons, logos, avatars) are not used as backgrounds
MAX_BG_TRIES = 5

# The fonts used here have no emoji or symbols; they would be drawn as empty boxes.
_NO_GLYPH = re.compile("[\U0001F000-\U0001FFFF\u2190-\u21FF\u2300-\u23FF\u2600-\u27BF\u2B00-\u2BFF\uFE00-\uFE0F\u200D]")


def _clean(text) -> str:
    return re.sub(r"\s+", " ", _NO_GLYPH.sub("", str(text or ""))).strip()


def _font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


def _download_image(url: str):
    """Download an article image. Returns None for anything unusable (too small, GIF/SVG, blocked, broken)."""
    try:
        if urlparse(url).scheme not in {"http", "https"} or url.lower().split("?")[0].endswith((".svg", ".gif")):
            return None
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        im = Image.open(io.BytesIO(r.content))
        if im.format in {"GIF", "SVG"} or min(im.size) < MIN_BG_SIDE:
            return None
        im = im.convert("RGB")
        im.thumbnail((W, H))
        return im
    except Exception:
        return None


def _ai_background(api_key: str, model: str, prompt: str):
    if not api_key or not prompt:
        return None
    try:
        import base64
        from openai import OpenAI        # optional dependency, only needed when AI backgrounds are enabled
        client = OpenAI(api_key=api_key)
        result = client.images.generate(model=model, prompt=prompt, size="1024x1536")
        return Image.open(io.BytesIO(base64.b64decode(result.data[0].b64_json))).convert("RGB")
    except Exception as exc:
        print(f"AI background unavailable; using fallback: {exc}")
        return None


def _fit_cover(image: Image.Image, size=(W, H)):
    target_w, target_h = size
    ratio = max(target_w / image.width, target_h / image.height)
    resized = image.resize((int(image.width * ratio), int(image.height * ratio)))
    left = (resized.width - target_w) // 2
    top = (resized.height - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def _wrap(draw, text, font, max_width):
    words = str(text or "").split()
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _fit_text(draw, text, sizes, max_width, max_lines, bold):
    """Largest font size from `sizes` whose wrapped text fits in max_lines. Returns (font, size, lines, clipped)."""
    for size in sizes:
        font = _font(size, bold)
        lines = _wrap(draw, text, font, max_width)
        too_wide = any(draw.textbbox((0, 0), ln, font=font)[2] > max_width for ln in lines)
        if len(lines) <= max_lines and not too_wide:
            return font, size, lines, False
    return font, size, lines[:max_lines], True      # even the smallest size does not fit: text is cut and flagged


def render_pin(pin: dict, brand: dict, destination: Path, article_images: list[str],
               openai_key: str = "", image_model: str = "gpt-image-1",
               use_ai_backgrounds: bool = True):
    colors = brand["colors"]
    palette = [colors["ivory"], colors["cream"], colors["champagne"], colors["sage"], colors["blush"]]
    number = int(pin.get("number", 1))
    idx = (number - 1) % len(palette)
    bg, source = None, "brand_template"

    if use_ai_backgrounds and openai_key:
        bg = _ai_background(openai_key, image_model, pin.get("image_prompt", ""))
        if bg is not None:
            source = "ai"

    # Fall back to an article image: try a few candidates, skipping icons/logos/broken files.
    if bg is None and article_images:
        for k in range(min(MAX_BG_TRIES, len(article_images))):
            bg = _download_image(article_images[(number - 1 + k) % len(article_images)])
            if bg is not None:
                source = "article_image"
                break

    if bg is not None:
        canvas = _fit_cover(bg).filter(ImageFilter.GaussianBlur(1))
        overlay = Image.new("RGBA", (W, H), (245, 239, 230, 155))
        canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay)
    else:
        base = Image.new("RGB", (W, H), palette[idx])
        d = ImageDraw.Draw(base, "RGBA")        # on an RGB image, "RGBA" mode blends the translucent accents
        d.ellipse((650, -100, 1150, 400), fill=colors["sage"] + "55")
        d.ellipse((-180, 1030, 380, 1590), fill=colors["blush"] + "88")
        canvas = base.convert("RGBA")

    draw = ImageDraw.Draw(canvas)
    ink = colors["ink"]
    muted = colors["muted"]

    variant = (number - 1) % 3
    margin = 82
    if variant == 0:
        draw.rounded_rectangle((45, 45, 955, 1455), radius=36, outline=colors["champagne"], width=5)
        label_y = 180
    elif variant == 1:
        draw.rounded_rectangle((65, 70, 935, 1430), radius=28, fill="#F5EFE6")
        label_y = 150
    else:
        draw.rectangle((0, 0, W, 260), fill=colors["sage"])
        draw.rectangle((0, 1180, W, H), fill=colors["cream"])
        label_y = 330

    draw.text((margin, label_y), "SUMMER SECTION", font=_font(27, True), fill=ink)
    draw.line((margin, label_y + 55, W - margin, label_y + 55), fill=colors["champagne"], width=3)

    headline = _clean(pin.get("headline")) or "A Helpful Buying Guide"
    sizes = [76, 64, 54, 46] if len(headline) < 30 else [64, 54, 46]
    h_font, h_size, lines, clipped = _fit_text(draw, headline, sizes, W - margin * 2, 4, True)
    y = label_y + 125
    for line in lines:
        draw.text((margin, y), line, font=h_font, fill=ink)
        y += int(h_size * 1.24)

    sub = _clean(pin.get("subheadline"))
    if sub:
        y += 18
        s_font, s_size, sub_lines, sub_clipped = _fit_text(draw, sub, [34, 30, 26], W - margin * 2, 3, False)
        clipped = clipped or sub_clipped
        for line in sub_lines:
            draw.text((margin, y), line, font=s_font, fill=muted)
            y += int(s_size * 1.4)

    footer_y = 1285
    domain = str(brand.get("display_domain") or DEFAULT_DOMAIN)
    draw.line((margin, footer_y - 35, W - margin, footer_y - 35), fill=colors["champagne"], width=3)
    draw.text((margin, footer_y), "READ THE FULL GUIDE", font=_font(25), fill=ink)
    draw.text((margin, footer_y + 52), domain, font=_font(22), fill=muted)

    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(destination)
    return {"path": str(destination), "width": W, "height": H, "template_variant": variant + 1,
            "background_source": source, "clipped": clipped}
