"""Zhihu crawler — questions, answers, and articles.

Reference: Zhihu web scraping patterns
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any, Optional

import httpx

from ..config import config
from ..llm import summarize_single
from ..models import Platform, Source
from .base import BaseCrawler


class ZhihuCrawler(BaseCrawler):
    platform = Platform.ZHIHU
    _domains = ["zhihu.com", "zhuanlan.zhihu.com"]

    async def crawl_single(self, url: str, **kwargs: Any) -> Optional[Source]:
        topic_id = kwargs.get("topic_id", "")
        version = kwargs.get("version", 1)

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=config.crawl.request_timeout,
            ) as client:
                resp = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Cookie": "",  # Can be configured for logged-in access
                })
                resp.raise_for_status()
                html = resp.text

            title = self._extract_title(html)
            content = self._extract_content(html)
            author = self._extract_author(html)

            if not content.strip():
                return None

            summary = await summarize_single(content[:3000])
            images = self._extract_images(html, url)
            confidence = min(1.0, len(content) / 3000 * 0.5 + 0.3)

            return Source(
                id=f"src_zhihu_{hashlib.md5(url.encode()).hexdigest()[:8]}",
                topic_id=topic_id,
                platform=Platform.ZHIHU,
                url=url,
                title=title,
                content=content,
                summary=summary,
                images=images,
                author=author,
                crawl_time=datetime.now().isoformat(),
                confidence=round(confidence, 2),
                crawl_version=version,
            )
        except Exception:
            return None

    def _extract_title(self, html: str) -> str:
        match = re.search(r'<h1[^>]*class="[^"]*QuestionHeader-title[^"]*"[^>]*>(.*?)</h1>', html, re.DOTALL)
        if match:
            return re.sub(r"<[^>]+>", "", match.group(1)).strip()[:200]
        match = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL)
        if match:
            return match.group(1).replace(" - 知乎", "").strip()[:200]
        return ""

    def _extract_content(self, html: str) -> str:
        # Try article content first
        match = re.search(r'<div[^>]*class="[^"]*RichContent-inner[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
        if match:
            text = re.sub(r"<[^>]+>", " ", match.group(1))
            return re.sub(r"\s+", " ", text).strip()[:50000]
        # Fallback: strip all tags
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()[:50000]

    def _extract_author(self, html: str) -> str:
        match = re.search(r'<a[^>]*class="[^"]*UserLink-link[^"]*"[^>]*>(.*?)</a>', html, re.DOTALL)
        if match:
            return re.sub(r"<[^>]+>", "", match.group(1)).strip()
        return ""

    def _extract_images(self, html: str, base_url: str) -> list[str]:
        urls = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
        from urllib.parse import urljoin
        return [urljoin(base_url, u) for u in urls[:5]]
