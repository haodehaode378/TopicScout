"""General web crawler — search + content extraction for Chinese web."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import httpx

from ..config import config
from ..llm import summarize_single
from ..models import Platform, Source
from .base import BaseCrawler

logger = logging.getLogger(__name__)

# Domains to skip in search results
BLOCKED_DOMAINS = {
    "google.com", "github.com", "vk.com", "youtube.com",
    "duckduckgo.com", "bing.com", "yandex.com",
    "lazada.com.my", "lazada.sg", "pchome.com.tw",
    "huishou.jd.com", "meigen.ai", "facebook.com",
    "twitter.com", "instagram.com", "tiktok.com",
}


def _is_blocked(url: str) -> bool:
    """Check if URL belongs to a blocked domain."""
    try:
        domain = urlparse(url).netloc.lower()
        return any(domain.endswith(b) for b in BLOCKED_DOMAINS)
    except Exception:
        return False


class WebCrawler(BaseCrawler):
    platform = Platform.WEB

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Web crawler handles all URLs as fallback."""
        return True

    @staticmethod
    async def search_urls(keyword: str, max_results: int = 10) -> list[str]:
        """Search for URLs using DuckDuckGo. Returns filtered result URLs."""
        from ddgs import DDGS

        urls: list[str] = []
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: DDGS().text(keyword, max_results=max_results),
            )
            for r in results:
                url = r.get("href", "")
                if url.startswith("http") and not _is_blocked(url):
                    urls.append(url)
        except Exception as e:
            logger.warning(f"[web] Search failed for '{keyword}': {e}")

        logger.info(f"[web] Search '{keyword}' found {len(urls)} URLs")
        return urls

    async def crawl_single(self, url: str, **kwargs: Any) -> Optional[Source]:
        """Crawl a single web page. Uses httpx for async fetching."""
        if _is_blocked(url):
            return None

        topic_id = kwargs.get("topic_id", "")
        version = kwargs.get("version", 1)

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=config.crawl.request_timeout) as client:
                resp = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
                })
                resp.raise_for_status()
                html = resp.text
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (403, 401):
                logger.warning(f"[web] Access denied for {url}: {e.response.status_code}")
            elif e.response.status_code >= 500:
                logger.warning(f"[web] Server error for {url}: {e.response.status_code}")
            else:
                logger.warning(f"[web] HTTP error for {url}: {e}")
            return None
        except Exception as e:
            logger.warning(f"[web] Failed to fetch {url}: {e}")
            return None

        # Basic content extraction from HTML
        title = self._extract_title(html)
        content = self._extract_text(html)
        images = self._extract_images(html, url)

        if not content.strip():
            logger.warning(f"[web] Empty content for {url}")
            return None

        # Download images
        saved_images = await self._download_images(images, topic_id)

        # Single summary
        summary = await summarize_single(content[:3000])

        # Simple confidence heuristic
        confidence = min(1.0, len(content) / 2000 * 0.5 + 0.3)

        source = Source(
            id=f"src_{hashlib.md5(url.encode()).hexdigest()[:8]}",
            topic_id=topic_id,
            platform=Platform.WEB,
            url=url,
            title=title,
            content=content,
            summary=summary,
            images=saved_images,
            crawl_time=datetime.now().isoformat(),
            confidence=confidence,
            crawl_version=version,
        )
        return source

    def _extract_title(self, html: str) -> str:
        import re
        match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()[:200]
        return ""

    def _extract_text(self, html: str) -> str:
        """Strip HTML tags and extract readable text."""
        import re
        # Remove script/style
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.IGNORECASE | re.DOTALL)
        # Remove tags
        text = re.sub(r"<[^>]+>", " ", text)
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text[:50000]  # Cap at 50k chars

    def _extract_images(self, html: str, base_url: str) -> list[str]:
        """Extract image URLs from HTML."""
        import re
        urls = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
        # Resolve relative URLs
        from urllib.parse import urljoin
        return [urljoin(base_url, u) for u in urls[:10]]

    async def _download_images(self, urls: list[str], topic_id: str) -> list[str]:
        """Download images to local storage. Returns saved paths."""
        if not topic_id:
            return []
        save_dir = os.path.join(config.storage.images_dir, topic_id)
        os.makedirs(save_dir, exist_ok=True)
        saved: list[str] = []
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            for i, url in enumerate(urls[:5]):  # Max 5 images per source
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    ext = ".jpg"
                    if "png" in resp.headers.get("content-type", ""):
                        ext = ".png"
                    elif "webp" in resp.headers.get("content-type", ""):
                        ext = ".webp"
                    filename = f"img_{hashlib.md5(url.encode()).hexdigest()[:8]}{ext}"
                    path = os.path.join(save_dir, filename)
                    with open(path, "wb") as f:
                        f.write(resp.content)
                    saved.append(path)
                except Exception:
                    pass  # Silently skip failed image downloads
        return saved
