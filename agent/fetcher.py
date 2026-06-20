import logging
from dataclasses import dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class WebPage:
    url: str
    title: str
    content: str
    status: Optional[int] = None
    error: Optional[str] = None


def fetch_page(url: str, timeout: int = 20, max_length: int = 12000) -> WebPage:
    """Fetch a single page and extract readable text."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return WebPage(url=url, title="", content="", error=str(exc))

    html = response.text
    title = ""

    # Try trafilatura first
    try:
        import trafilatura

        extracted = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=False,
            deduplicate=True,
            target_language=("zh" if "zh" in response.headers.get("Content-Language", "") else None),
        )
        if extracted:
            content = extracted.strip()
            title = _extract_title(html) or ""
            return WebPage(
                url=url,
                title=title,
                content=content[:max_length],
                status=response.status_code,
            )
    except Exception as exc:
        logger.debug("Trafilatura extraction failed for %s: %s", url, exc)

    # Fallback to BeautifulSoup
    try:
        soup = BeautifulSoup(html, "html.parser")
        title = _extract_title_from_soup(soup) or ""
        content = _extract_text_from_soup(soup)[:max_length]
        return WebPage(url=url, title=title, content=content, status=response.status_code)
    except Exception as exc:
        logger.warning("BeautifulSoup extraction failed for %s: %s", url, exc)
        return WebPage(url=url, title="", content="", error=str(exc))


def _extract_title(html: str) -> str:
    try:
        soup = BeautifulSoup(html, "html.parser")
        return _extract_title_from_soup(soup)
    except Exception:
        return ""


def _extract_title_from_soup(soup: BeautifulSoup) -> str:
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return ""


def _extract_text_from_soup(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()

    main = soup.find("main") or soup.find("article") or soup.find("div", role="main")
    if main:
        text = main.get_text(separator="\n", strip=True)
    else:
        text = soup.get_text(separator="\n", strip=True)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)
