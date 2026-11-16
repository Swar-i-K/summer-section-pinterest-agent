import json
from agent import main as m
from agent.config import Settings
from pathlib import Path

BRAND = json.loads((Path(__file__).resolve().parents[1] / "brand/summer_section.json").read_text())


def test_identical_images_are_flagged(tmp_path, monkeypatch):
    # two pins with the same number would render the same image
    pins = [{"number": 1, "headline": "Same", "title": "T", "description": "D", "board": "B"},
            {"number": 1, "headline": "Same", "title": "T", "description": "D", "board": "B"}]
    plan = {"article_analysis": {}, "keyword_suggestions": {}, "board_suggestions": [], "pins": pins}
    settings = Settings("key", "m", "u", "", "g", False, 2, 9000, tmp_path,
                        Path(__file__).resolve().parents[1] / "brand/summer_section.json")
    monkeypatch.setattr(m, "load_settings", lambda: settings)
    monkeypatch.setattr(m, "extract_article", lambda url: {"url": "https://e.com/", "title": "T", "image_urls": []})
    monkeypatch.setattr(m, "analyze_and_plan", lambda *a, **k: plan)
    assert m.run() == 2
