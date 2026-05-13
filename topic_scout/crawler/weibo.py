"""Weibo crawler — posts and articles.

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


class WeiboCrawler(BaseCrawler):
    platform = Platform.WEIBO
    _domains = ["weibo.com", "weibo.cn", "m.weibo.cn"]

    async def crawl_single(self, url: str, **kwargs: Any) -> Optional[Source]:
        topic_id = kwargs.get("topic_id", "")
        version = kwargs.get("version", 1)

        try:
            # Prefer mobile API for better content access
            mobile_url = self._to_mobile_url(url)

            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=config.crawl.request_timeout,
            ) as client:
                resp = await client.get(mobile_url, headers={
                    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
                    "Accept": "application/json, text/html",
                })
                resp.raise_for_status()
                html = resp.text

            title = self._extract_title(html)
            content = self._extract_content(html)
            author = self._extract_author(html)

            if not content.strip():
                return None

            summary = await summarize_single(content[:3000])
            images = self._extract_images(html, mobile_url)
            confidence = min(1.0, len(content) / 2000 * 0.5 + 0.3)

            return Source(
                id=f"src_weibo_{hashlib.md5(url.encode()).hexdigest()[:8]}",
                topic_id=topic_id,
                platform=Platform.WEIBO,
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

    def _to_mobile_url(self, url: str) -> str:
        url = url.replace("weibo.com", "m.weibo.cn")
        url = url.replace("weibo.cn", "m.weibo.cn")
        return url

    def _extract_title(self, html: str) -> str:
        match = re.search(r'"text"\s*:\s*"(.*?)"', html)
        if match:
            text = match.group(1)[:100]
            text = re.sub(r"<[^>]+>", "", text)
            return text.replace("\\n", " ").strip()[:200]
        match = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL)
        if match:
            return match.group(1).replace(" - 微博", "").strip()[:200]
        return ""

    def _extract_content(self, html: str) -> str:
        # Try JSON data first
        match = re.search(r'"text"\s*:\s*"(.*?)"', html)
        if match:
            text = match.group(1)
            text = text.replace("\\n", "\n").replace('\\"', '"')
            text = re.sub(r"<[^>]+>", " ", text)
            if len(text) > 20:
                return text[:50000]
        # Fallback
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()[:50000]

    def _extract_author(self, html: str) -> str:
        match = re.search(r'"screen_name"\s*:\s*"(.*?)"', html)
        if match:
            return match.group(1)
        return ""

    def _extract_images(self, html: str, base_url: str) -> list[str]:
        urls = re.findall(r'"original_pic"\s*:\s*"(.*?)"', html)
        if not urls:
            urls = re.findall(r'"bmiddle_pic"\s*:\s*"(.*?)"', html)
        return [u.replace("\\", "") for u in urls[:5]] if urls else []
