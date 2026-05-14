"""WeChat public account crawler — deep integration via wx_api."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Any, Optional

from ..llm import summarize_single
from ..models import Platform, Source
from ..wx_api import extract_article_content, get_article_list
from .base import BaseCrawler

logger = logging.getLogger(__name__)


class WechatCrawler(BaseCrawler):
    platform = Platform.WECHAT
    _domains = ["mp.weixin.qq.com"]

    @staticmethod
    async def search_urls(keyword: str, max_results: int = 10) -> list[str]:
        """Search WeChat public accounts by keyword, then fetch their articles."""
        from ..wx_api import search_biz

        urls: list[str] = []
        try:
            accounts = await search_biz(keyword, limit=5)
            if not accounts:
                logger.info("[wechat] No accounts found for keyword, skipping")
                return []

            per_account = max(1, max_results // max(len(accounts), 1))
            for acct in accounts:
                try:
                    fakeid = acct.get("fakeid", "")
                    nickname = acct.get("nickname", "")
                    if not fakeid:
                        continue
                    articles = await get_article_list(fakeid, page=0, count=per_account)
                    for a in articles:
                        if a.get("link") and a["link"].startswith("http"):
                            urls.append(a["link"])
                        if len(urls) >= max_results:
                            break
                except ValueError:
                    logger.warning("[wechat] Token expired during article fetch")
                    return urls
                except Exception as e:
                    logger.warning(f"[wechat] Failed to fetch articles for {nickname}: {e}")
                if len(urls) >= max_results:
                    break
        except Exception as e:
            logger.warning(f"[wechat] Search failed: {e}")

        logger.info(f"[wechat] Found {len(urls)} article URLs")
        return urls

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return any(d in url for d in cls._domains)

    async def crawl_single(self, url: str, **kwargs: Any) -> Optional[Source]:
        """Crawl a single WeChat article."""
        topic_id = kwargs.get("topic_id", "")
        version = kwargs.get("version", 1)

        try:
            article = await extract_article_content(url)
            if not article:
                return None

            title = article.get("title", "")
            content = article.get("content", "")
            author = article.get("author", "")
            cover_url = article.get("cover_url", "")

            if not content.strip():
                logger.warning(f"[wechat] Empty content for {url}")
                return None

            summary = await summarize_single(content[:3000])
            images = [cover_url] if cover_url else []
            confidence = min(1.0, len(content) / 2000 * 0.5 + 0.3)

            return Source(
                id=f"src_wechat_{hashlib.md5(url.encode()).hexdigest()[:8]}",
                topic_id=topic_id,
                platform=Platform.WECHAT,
                url=url,
                title=title,
                content=content[:50000],
                summary=summary,
                images=images,
                author=author,
                publish_time="",
                crawl_time=datetime.now().isoformat(),
                confidence=round(confidence, 2),
                crawl_version=version,
            )
        except Exception as e:
            logger.warning(f"[wechat] Failed to crawl {url}: {e}")
            return None
