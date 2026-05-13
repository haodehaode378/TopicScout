"""Bilibili crawler — video info and comments via API.

Reference: SocialSisterYi/bilibili-API-collect
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from datetime import datetime
from typing import Any, Optional

import httpx

from ..config import config
from ..llm import summarize_single
from ..models import Platform, Source
from .base import BaseCrawler


class BilibiliCrawler(BaseCrawler):
    platform = Platform.BILIBILI
    _domains = ["bilibili.com", "b23.tv", "bili"]

    @staticmethod
    async def search_urls(keyword: str, max_results: int = 10) -> list[str]:
        """Search Bilibili for videos by keyword. Returns list of video URLs."""
        urls: list[str] = []
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://api.bilibili.com/x/web-interface/search/all/v2",
                    params={"keyword": keyword, "page": 1, "pagesize": max_results},
                    headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com"},
                )
                data = resp.json()
                if data.get("code") != 0:
                    return urls
                for result in data.get("data", {}).get("result", []):
                    if result.get("result_type") == "video":
                        for v in result.get("data", []):
                            bvid = v.get("bvid", "")
                            if bvid:
                                urls.append(f"https://www.bilibili.com/video/{bvid}")
                                if len(urls) >= max_results:
                                    break
                    if len(urls) >= max_results:
                        break
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"[bilibili] Search failed for '{keyword}': {e}")

        import logging
        logging.getLogger(__name__).info(f"[bilibili] Search '{keyword}' found {len(urls)} URLs")
        return urls

    async def crawl_single(self, url: str, **kwargs: Any) -> Optional[Source]:
        topic_id = kwargs.get("topic_id", "")
        version = kwargs.get("version", 1)

        bvid = self._extract_bvid(url)
        if not bvid:
            return None

        try:
            # Fetch video info via API
            async with httpx.AsyncClient(timeout=config.crawl.request_timeout) as client:
                resp = await client.get(
                    f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}",
                    headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com"},
                )
                resp.raise_for_status()
                data = resp.json()

            if data.get("code") != 0:
                return None

            info = data["data"]
            title = info.get("title", "")
            desc = info.get("desc", "")
            author = info.get("owner", {}).get("name", "")
            pub_ts = info.get("pubdate", 0)
            pic = info.get("pic", "")

            # Fetch top comments
            comments = await self._fetch_comments(bvid)

            # Build content
            content_parts = [f"# {title}", f"\n{desc}"]
            if comments:
                content_parts.append("\n## 热门评论")
                for c in comments[:10]:
                    content_parts.append(f"- {c}")

            content = "\n".join(content_parts)
            summary = await summarize_single(content[:3000])

            # Download cover image
            images = []
            if pic:
                img_path = await self._download_image(pic, topic_id, f"bili_{bvid}")
                if img_path:
                    images.append(img_path)

            # Confidence based on view count and likes
            stat = info.get("stat", {})
            views = stat.get("view", 0)
            likes = stat.get("like", 0)
            confidence = min(1.0, views / 100000 * 0.5 + likes / 10000 * 0.3 + 0.2)

            pub_time = datetime.fromtimestamp(pub_ts).isoformat() if pub_ts else ""

            return Source(
                id=f"src_bili_{bvid}",
                topic_id=topic_id,
                platform=Platform.BILIBILI,
                url=url,
                title=title,
                content=content,
                summary=summary,
                images=images,
                author=author,
                publish_time=pub_time,
                crawl_time=datetime.now().isoformat(),
                confidence=round(confidence, 2),
                crawl_version=version,
            )
        except Exception:
            return None

    def _extract_bvid(self, url: str) -> Optional[str]:
        match = re.search(r"(BV[\w]{10})", url)
        return match.group(1) if match else None

    async def _fetch_comments(self, bvid: str) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"https://api.bilibili.com/x/v2/reply?type=1&oid={bvid}&sort=1&ps=20",
                    headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com"},
                )
                data = resp.json()
                replies = data.get("data", {}).get("replies", [])
                return [r.get("content", {}).get("message", "") for r in replies if r.get("content", {}).get("message")]
        except Exception:
            return []

    async def _download_image(self, url: str, topic_id: str, name: str) -> Optional[str]:
        import os
        save_dir = os.path.join(config.storage.images_dir, topic_id)
        os.makedirs(save_dir, exist_ok=True)
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url, headers={"Referer": "https://www.bilibili.com"})
                resp.raise_for_status()
                path = os.path.join(save_dir, f"{name}.jpg")
                with open(path, "wb") as f:
                    f.write(resp.content)
                return path
        except Exception:
            return None
