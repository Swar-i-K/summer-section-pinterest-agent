from __future__ import annotations
import json
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

DEFAULT_MODEL = "openai/gpt-oss-120b"


def _env(name: str, default: str = "") -> str:
    """Environment value, treating an empty string (e.g. an unset GitHub variable) as 'not set'."""
    return os.getenv(name, "").strip() or default


@dataclass
class Settings:
    groq_api_key: str
    model: str
    article_url: str
    openai_api_key: str
    image_model: str
    use_ai_backgrounds: bool
    pin_count: int
    article_char_limit: int
    output_dir: Path
    brand_path: Path


def load_settings() -> Settings:
    url = _env("ARTICLE_URL")
    if not url:
        raise ValueError("ARTICLE_URL is required. Supply it as an environment variable.")
    try:
        pins = int(_env("PINS_PER_ARTICLE", "10"))
    except ValueError:
        raise ValueError("PINS_PER_ARTICLE must be a whole number between 1 and 15.")
    if not 1 <= pins <= 15:
        raise ValueError("PINS_PER_ARTICLE must be a whole number between 1 and 15.")
    return Settings(
        groq_api_key=_env("GROQ_API_KEY"),
        model=_env("GROQ_MODEL", DEFAULT_MODEL),
        article_url=url,
        openai_api_key=_env("OPENAI_API_KEY"),
        image_model=_env("OPENAI_IMAGE_MODEL", "gpt-image-1"),
        use_ai_backgrounds=_env("USE_AI_BACKGROUNDS", "true").lower() == "true",
        pin_count=pins,
        article_char_limit=int(_env("ARTICLE_CHAR_LIMIT", "9000")),
        output_dir=Path(_env("OUTPUT_DIR", str(ROOT / "output"))),
        brand_path=Path(_env("BRAND_CONFIG", str(ROOT / "brand/summer_section.json"))),
    )


def load_brand(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
