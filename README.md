# Summer Section Pinterest Agent

A manually triggered GitHub Actions workflow that turns a public Summer Section article URL into a Pinterest campaign (10 pins by default) using the **Groq API** for planning, plus optional AI-generated visual backgrounds.

## What it does

1. Fetches a public article URL and extracts its readable text, headings, description, and image URLs.
2. Uses Groq to analyze the article, then plan the pins in small batches (each pin gets a different marketing angle), with titles, descriptions, keyword suggestions, and board suggestions.
3. Creates 1000 × 1500 Pinterest graphics using three branded editorial layouts.
4. Optionally requests background-only imagery from the OpenAI Images API. If no OpenAI key is set or generation fails, it uses a suitable article image (icons, logos and tiny images are skipped) or a branded template background.
5. Runs asset and metadata checks: size, missing fields, clipped text, duplicate images.
6. Saves a campaign summary, JSON metadata, images, and a review-only publishing queue.
7. Uploads the campaign as a GitHub Actions artifact (kept for 3 days).

**Publishing is intentionally disabled.** This project does not create or publish Pins. Every pin is marked `pending` for human review.

## Requirements

- A GitHub repository you can administer.
- A Groq API key (https://console.groq.com/keys). The free tier works; see "Groq limits" below.
- Optional: an OpenAI API key with image-generation access for AI backgrounds.

Groq does not generate images. Groq creates the copy and creative direction; Pillow renders the typography and layout; the optional OpenAI Images API creates background imagery.

## Setup

1. Create a repository (for example `summer-section-pinterest-agent`) and upload this project.
2. In **Settings → Secrets and variables → Actions → New repository secret**, add:
   - `GROQ_API_KEY` (required)
   - `OPENAI_API_KEY` (optional; enables AI backgrounds)
3. Optional: under the **Variables** tab, add `GROQ_MODEL` to use a different model. Default: `openai/gpt-oss-120b`.
4. Open **Actions → Summer Section Pinterest Agent → Run workflow**, enter the article URL, choose the number of pins, and run.
5. Open the finished run and download the artifact `summer-section-pinterest-campaign`.

Do not put keys in source code or commit a `.env` file.

## Output

The artifact contains one folder per article with:

- `article_analysis.json`, `pinterest_keyword_suggestions.json`, `pin_strategy.json`
- `pinterest_campaign.json` (each pin linked to its image)
- `pin_01.png` … `pin_10.png`
- `publishing_queue.json`, `quality_report.json`, `CAMPAIGN_SUMMARY.md`

## Local run

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Set your keys and article URL in `.env`, then run `python -m agent.main`.

## Configuration

- `GROQ_MODEL`: default `openai/gpt-oss-120b`. Check current model names at https://console.groq.com/docs/models.
- `PINS_PER_ARTICLE`: 1 to 15, default `10`.
- `ARTICLE_CHAR_LIMIT`: how much article text is sent to the model, default `9000`. Lower it if you see a "request too large" message.
- `USE_AI_BACKGROUNDS`: `true` or `false`.
- `OPENAI_IMAGE_MODEL`: default `gpt-image-1`.
- `brand/summer_section.json`: colors, tone, website, and `display_domain`, the text printed at the bottom of every pin. **Set `display_domain` to your live website.**

## Groq limits

Groq's free tier has small per-minute and per-day token limits. This agent sends several small requests (one analysis, then batches of 5 pins) instead of one large one, and it waits and retries when it is rate limited. A full 10-pin campaign can take a few minutes. If the daily limit is used up, the run stops with a clear message; try again later or choose another model.

## Important limitations

- Keyword suggestions are AI-generated ideas, not verified Pinterest search-volume data.
- Article images may be blocked, hotlinked, or unsuitable. The renderer skips them and falls back to a brand background.
- The quality checker validates dimensions, required metadata, clipped text and duplicate images. It does not replace human review of spelling, claims and visual quality.
- The workflow does not publish to Pinterest and does not schedule posts.

## Tests

```bash
pip install pytest
pytest -q
```

## Security

Never commit `.env`, API keys, or tokens. Use GitHub Actions secrets.
