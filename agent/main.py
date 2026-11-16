from __future__ import annotations
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from .config import load_settings, load_brand
from .article_reader import extract_article
from .groq_brain import analyze_and_plan
from .image_designer import render_pin
from .quality_checker import check_pin


def slugify(value: str) -> str:
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-")[:70] or "article-campaign"


def write_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run():
    settings = load_settings()
    brand = load_brand(settings.brand_path)
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY is missing. Add it as a GitHub Actions secret named GROQ_API_KEY.")
    print(f"Extracting article: {settings.article_url}")
    article = extract_article(settings.article_url)

    print(f"Analyzing the article and planning {settings.pin_count} Pinterest pins with Groq ({settings.model})...")
    plan = analyze_and_plan(settings.groq_api_key, settings.model, article, brand,
                            settings.pin_count, settings.article_char_limit)

    campaign_slug = slugify(article.get("title") or plan["article_analysis"].get("topic", "article"))
    out = settings.output_dir / campaign_slug
    out.mkdir(parents=True, exist_ok=True)

    write_json(out / "article_analysis.json", plan["article_analysis"])
    write_json(out / "pinterest_keyword_suggestions.json", plan["keyword_suggestions"])
    write_json(out / "pin_strategy.json", {"pins": plan["pins"], "boards": plan.get("board_suggestions", [])})

    quality = []
    campaign_pins = []
    seen_hashes: dict[str, int] = {}
    for pin in plan["pins"]:
        number = int(pin["number"])
        image_path = out / f"pin_{number:02d}.png"
        image_meta = render_pin(
            pin, brand, image_path, article.get("image_urls", []),
            settings.openai_api_key, settings.image_model, settings.use_ai_backgrounds
        )
        result = check_pin(image_path, pin, article["url"], image_meta)
        digest = hashlib.sha1(image_path.read_bytes()).hexdigest()
        if digest in seen_hashes:
            result["issues"].append(f"Image is identical to pin {seen_hashes[digest]}.")
            result["passed"] = False
        seen_hashes.setdefault(digest, number)
        result["pin_number"] = number
        quality.append(result)
        campaign_pins.append({
            **pin,
            "destination_url": article["url"],
            "image_file": image_path.name,
            "image": image_meta,
            "approval_status": "pending"
        })

    campaign = {
        "brand": brand["brand"],
        "article_url": article["url"],
        "article_title": article["title"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "publishing_mode": "manual_review_only",
        "pins": campaign_pins
    }
    write_json(out / "pinterest_campaign.json", campaign)
    write_json(out / "publishing_queue.json", {
        "note": "No Pins have been published. Review and approve each item manually.",
        "publishing_enabled": False,
        "items": [{"pin_number": p["number"], "status": "pending_review",
                   "image_file": p["image_file"], "destination_url": p["destination_url"]}
                  for p in campaign_pins]
    })
    write_json(out / "quality_report.json", {
        "passed": all(x["passed"] for x in quality),
        "checks": quality
    })

    summary = [
        f"# Pinterest campaign: {article.get('title', 'Article')}",
        "",
        f"- Destination: {article['url']}",
        f"- Pins generated: {len(campaign_pins)}",
        "- Publishing: disabled; human review required",
        f"- Quality checks passed: {sum(x['passed'] for x in quality)}/{len(quality)}",
        "",
        "## Pin copy"
    ]
    for p in campaign_pins:
        summary += [f"### Pin {p['number']}: {p['title']}",
                    f"- Image: `{p['image_file']}`",
                    f"- Angle: {p.get('angle', '')}",
                    f"- Description: {p['description']}",
                    f"- Board: {p['board']}", ""]
    (out / "CAMPAIGN_SUMMARY.md").write_text("\n".join(summary), encoding="utf-8")
    print(f"Campaign saved to: {out}")
    if not all(x["passed"] for x in quality):
        print("WARNING: Some quality checks failed. Review quality_report.json.")
        return 2
    return 0


def main():
    try:
        code = run()
    except Exception as exc:  # report a clear error instead of a long traceback
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
    sys.exit(code)


if __name__ == "__main__":
    main()
