from PIL import Image
from agent.image_designer import render_pin, _clean

BRAND = {"colors": {"ivory": "#F5EFE6", "cream": "#EFE5D7", "champagne": "#D8C7AE", "sage": "#A8B5A0",
                    "blush": "#E8CFCB", "ink": "#34332F", "muted": "#77736C"}, "display_domain": "example.com"}


def pin(n, headline="Keep Cold Air Out", sub=""):
    return {"number": n, "headline": headline, "subheadline": sub}


def test_all_three_layouts_render_at_pinterest_size(tmp_path):
    for n in (1, 2, 3):
        meta = render_pin(pin(n), BRAND, tmp_path / f"p{n}.png", [])
        with Image.open(tmp_path / f"p{n}.png") as im:
            assert im.size == (1000, 1500)
        assert meta["template_variant"] == n and meta["background_source"] == "brand_template"
        assert meta["clipped"] is False


def test_emoji_removed_from_image_text():
    assert _clean("Keep the cold out 🏠❄️ today") == "Keep the cold out today"


def test_soft_accent_is_blended_not_solid(tmp_path):
    render_pin(pin(1), BRAND, tmp_path / "p.png", [])
    r, g, b = Image.open(tmp_path / "p.png").getpixel((850, 100))
    # ivory (245,239,230) blended ~33% with sage (168,181,160) is about (219,220,207); a solid sage would be (168,181,160)
    assert abs(r - 219) <= 4 and abs(g - 220) <= 4 and abs(b - 207) <= 4, (r, g, b)


def test_long_headline_shrinks_and_extreme_text_is_flagged(tmp_path):
    ok = render_pin(pin(1, "How to stop cold air coming in under every exterior door this winter"), BRAND, tmp_path / "a.png", [])
    assert ok["clipped"] is False
    bad = render_pin(pin(1, " ".join(["Supercalifragilistic" * 3] * 12)), BRAND, tmp_path / "b.png", [])
    assert bad["clipped"] is True


def test_background_skips_unusable_images_and_reports_source(tmp_path, monkeypatch):
    import io
    import agent.image_designer as d

    def big():
        buf = io.BytesIO()
        Image.new("RGB", (900, 1200), "#99aa88").save(buf, "PNG")
        return buf.getvalue()

    def small():
        buf = io.BytesIO()
        Image.new("RGB", (64, 64), "#000").save(buf, "PNG")
        return buf.getvalue()

    class R:
        def __init__(self, content): self.content = content
        def raise_for_status(self): pass

    monkeypatch.setattr(d.requests, "get", lambda url, **k: R(small() if "logo" in url else big()))
    meta = render_pin(pin(1), BRAND, tmp_path / "p.png",
                      ["https://example.com/logo.png", "https://example.com/photo.png"])
    assert meta["background_source"] == "article_image"
    meta2 = render_pin(pin(2), BRAND, tmp_path / "q.png", ["https://example.com/logo.png"])
    assert meta2["background_source"] == "brand_template"
