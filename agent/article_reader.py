from __future__ import annotations
import re
from urllib.parse import urljoin, urlparse
import requests
import trafilatura
from bs4 import BeautifulSoup

USER_AGENT = "SummerSectionPinterestAgent/1.0 (+content transformation; contact site owner)"

def validate_article_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Please provide a valid http(s) article URL.")

def extract_article(url: str) -> dict:
    validate_article_url(url)
    response = requests.get(url, timeout=30, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    html = response.text
    soup = BeautifulSoup(html, "html.parser")

    title = (soup.find("h1").get_text(" ", strip=True) if soup.find("h1")
             else (soup.title.get_text(" ", strip=True) if soup.title else ""))
    headings = []
    for tag in soup.find_all(["h1", "h2", "h3"]):
        text = tag.get_text(" ", strip=True)
        if text:
            headings.append({"level": tag.name, "text": text})

    image_urls = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
        if src:
            absolute = urljoin(url, src)
            if absolute.startswith(("http://", "https://")) and absolute not in image_urls:
                image_urls.append(absolute)

    text = trafilatura.extract(
        html, url=url, include_comments=False, include_tables=True,
        include_links=False, favor_precision=True
    )
    if not text or len(text.strip()) < 300:
        raise RuntimeError("Article extraction returned too little text. Check that the URL is public and contains a readable article.")

    canonical = soup.find("link", rel="canonical")
    canonical_url = canonical.get("href") if canonical and canonical.get("href") else url

    return {
        "url": canonical_url,
        "submitted_url": url,
        "title": title.strip(),
        "headings": headings,
        "text": re.sub(r"\n{3,}", "\n\n", text).strip(),
        "image_urls": image_urls[:30],
        "description": (soup.find("meta", attrs={"name": "description"}) or {}).get("content", "")
    }
