"""Xiaohongshu (RED) crawler — notes and articles.

Reference: NanmiCoder/MediaCrawler
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


class XiaohongshuCrawler(BaseCrawler):
    platform = Platform.XIAOHONGSHU
    _domains = ["xiaohongshu.com", "xhslink.com"]

    async def crawl_single(self, url: str, **kwargs: Any) -> Optional[Source]:
        topic_id = kwargs.get("topic_id", "")
        version = kwargs.get("version", 1)

        try:
            # Resolve xhslink.com short links
            real_url = await self._resolve_url(url)

            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=config.crawl.request_timeout,
            ) as client:
                resp = await client.get(real_url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                })
                resp.raise_for_status()
                html = resp.text

            title = self._extract_title(html)
            content = self._extract_content(html)
            author = self._extract_author(html)

            if not content.strip():
                return None

            summary = await summarize_single(content[:3000])
            images = self._extract_images(html, real_url)
            confidence = min(1.0, len(content) / 2000 * 0.5 + 0.3)

            return Source(
                id=f"src_xhs_{hashlib.md5(url.encode()).hexdigest()[:8]}",
                topic_id=topic_id,
                platform=Platform.XIAOHONGSHU,
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

    async def _resolve_url(self, url: str) -> str:
        if "xhslink.com" in url:
            try:
                async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
                    resp = await client.head(url, headers={"User-Agent": "Mozilla/5.0"})
                    return str(resp.url)
            except Exception:
                pass
        return url

    def _extract_title(self, html: str) -> str:
        match = re.search(r'"title"\s*:\s*"(.*?)"', html)
        if match:
            return match.group(1).replace("\\n", " ").strip()[:200]
        match = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL)
        if match:
            return match.group(1).replace(" - 小红书", "").strip()[:200]
        return ""

    def _extract_content(self, html: str) -> str:
        # Try JSON data
        match = re.search(r'"desc"\s*:\s*"(.*?)"', html)
        if match:
            text = match.group(1)
            text = text.replace("\\n", "\n").replace('\\"', '"')
            if len(text) > 20:
                return text[:50000]
        # Fallback
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()[:50000]

    def _extract_author(self, html: str) -> str:
        match = re.search(r'"nickname"\s*:\s*"(.*?)"', html)
        if match:
            return match.group(1)
        return ""

    def _extract_images(self, html: str, base_url: str) -> list[str]:
        # Extract image URLs from JSON data
        urls = re.findall(r'"urlDefault"\s*:\s*"(.*?)"', html)
        if not urls:
            urls = re.findall(r'"imageList"\s*:\s*\[([^\]]+)\]', html)
            if urls:
                urls = re.findall(r'"urlDefault"\s*:\s*"(.*?)"', urls[0])
        return [u.replace("\\u002F", "/").replace("\\", "") for u in urls[:10]] if urls else []
