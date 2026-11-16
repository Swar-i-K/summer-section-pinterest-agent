import pytest
from agent import article_reader as ar

HTML = """<html><head><title>T</title><link rel="canonical" href="https://example.com/real/">
<meta name="description" content="About draft stoppers"></head><body><h1>Best Draft Stoppers</h1>
<h2>How to choose</h2><p>%s</p><img src="/wp-content/a.jpg"><img data-src="https://cdn.example.com/b.jpg"></body></html>""" % ("Real article words. " * 60)


class R:
    def __init__(self, text): self.text = text
    def raise_for_status(self): pass


def test_extracts_headings_images_canonical(monkeypatch):
    monkeypatch.setattr(ar.requests, "get", lambda *a, **k: R(HTML))
    monkeypatch.setattr(ar.trafilatura, "extract", lambda *a, **k: "Real article words. " * 60)
    art = ar.extract_article("https://example.com/post/")
    assert art["url"] == "https://example.com/real/" and art["submitted_url"] == "https://example.com/post/"
    assert [h["level"] for h in art["headings"]] == ["h1", "h2"]
    assert art["image_urls"] == ["https://example.com/wp-content/a.jpg", "https://cdn.example.com/b.jpg"]


def test_too_little_text_and_bad_url_are_errors(monkeypatch):
    monkeypatch.setattr(ar.requests, "get", lambda *a, **k: R(HTML))
    monkeypatch.setattr(ar.trafilatura, "extract", lambda *a, **k: "short")
    with pytest.raises(RuntimeError, match="too little text"):
        ar.extract_article("https://example.com/post/")
    with pytest.raises(ValueError):
        ar.extract_article("ftp://example.com")
