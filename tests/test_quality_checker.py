from pathlib import Path
from PIL import Image
from agent.quality_checker import check_pin

PIN = {"headline": "Test headline", "title": "Title", "description": "Description", "board": "Board"}


def test_quality_checker_accepts_valid_pin(tmp_path):
    path = tmp_path / "pin.png"
    Image.new("RGB", (1000, 1500), "white").save(path)
    result = check_pin(path, PIN, "https://example.com/article")
    assert result["passed"] is True


def test_quality_checker_flags_clipped_text_and_bad_size(tmp_path):
    path = tmp_path / "pin.png"
    Image.new("RGB", (800, 1200), "white").save(path)
    result = check_pin(path, PIN, "https://example.com/article", {"clipped": True})
    assert result["passed"] is False
    assert any("dimensions" in i for i in result["issues"])
    assert any("cut off" in i for i in result["issues"])
