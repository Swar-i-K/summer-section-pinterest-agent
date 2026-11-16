from __future__ import annotations
from pathlib import Path
from PIL import Image


def check_pin(path: Path, pin: dict, expected_url: str, image_meta: dict | None = None) -> dict:
    issues = []
    try:
        with Image.open(path) as im:
            if im.size != (1000, 1500):
                issues.append(f"Unexpected dimensions: {im.size}")
            if im.mode not in {"RGB", "RGBA"}:
                issues.append(f"Unexpected color mode: {im.mode}")
    except Exception as exc:
        issues.append(f"Image cannot be opened: {exc}")

    for field in ("headline", "title", "description", "board"):
        if not str(pin.get(field, "")).strip():
            issues.append(f"Missing metadata field: {field}")
    if not expected_url.startswith(("https://", "http://")):
        issues.append("Destination URL is not an absolute HTTP(S) URL.")
    headline = str(pin.get("headline", ""))
    if len(headline) > 90:
        issues.append("Headline is too long for the intended mobile-first design.")
    if image_meta and image_meta.get("clipped"):
        issues.append("On-image text did not fit and was cut off. Shorten the headline or subheadline.")
    return {"passed": not issues, "issues": issues, "image": str(path)}
