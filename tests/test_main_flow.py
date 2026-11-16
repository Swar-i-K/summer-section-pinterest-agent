import json
from agent import main as m
from agent.config import Settings


def make_settings(tmp_path):
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    return Settings("key", "model", "https://example.com/post/", "", "gpt-image-1", False, 10, 9000,
                    tmp_path / "out", root / "brand/summer_section.json")


ARTICLE = {"url": "https://example.com/post/", "submitted_url": "https://example.com/post/", "title": "Best Draft Stoppers",
           "headings": [], "text": "x" * 500, "image_urls": [], "description": ""}


def fake_plan(*a, **k):
    n = a[4] if len(a) > 4 else 10
    return {"article_analysis": {"topic": "t"}, "keyword_suggestions": {"phrases": []}, "board_suggestions": ["Home"],
            "pins": [{"number": i, "angle": "a", "headline": f"Pin headline {i}", "subheadline": "", "title": f"T{i}",
                      "description": "D", "board": "Home", "keywords": [], "hashtags": []} for i in range(1, n + 1)]}


def test_full_run_writes_ten_pins_and_all_files(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "load_settings", lambda: make_settings(tmp_path))
    monkeypatch.setattr(m, "extract_article", lambda url: ARTICLE)
    monkeypatch.setattr(m, "analyze_and_plan", fake_plan)
    assert m.run() == 0
    out = tmp_path / "out" / "best-draft-stoppers"
    names = {p.name for p in out.iterdir()}
    assert {f"pin_{i:02d}.png" for i in range(1, 11)} <= names
    for f in ("article_analysis.json", "pinterest_keyword_suggestions.json", "pin_strategy.json",
              "pinterest_campaign.json", "publishing_queue.json", "quality_report.json", "CAMPAIGN_SUMMARY.md"):
        assert f in names, f
    q = json.loads((out / "quality_report.json").read_text())
    assert q["passed"] is True and len(q["checks"]) == 10
    assert json.loads((out / "publishing_queue.json").read_text())["publishing_enabled"] is False


def test_missing_groq_key_gives_clear_error(tmp_path, monkeypatch, capsys):
    s = make_settings(tmp_path); s.groq_api_key = ""
    monkeypatch.setattr(m, "load_settings", lambda: s)
    try:
        m.main()
    except SystemExit as e:
        assert e.code == 1
    assert "GROQ_API_KEY" in capsys.readouterr().err
