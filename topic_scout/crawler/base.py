"""Base crawler — concurrency control, retry with exponential backoff."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

from ..config import config
from ..models import Platform, Source

logger = logging.getLogger(__name__)


class BaseCrawler(ABC):
    platform: Platform = Platform.WEB
    _domains: list[str] = []

    def __init__(self) -> None:
        self._semaphore = asyncio.Semaphore(config.crawl.max_concurrent)
        self._platform_semaphore = asyncio.Semaphore(5)  # per-platform limit

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Check if this crawler can handle the given URL."""
        if not cls._domains:
            return False
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        return any(d in domain for d in cls._domains)

    @abstractmethod
    async def crawl_single(self, url: str, **kwargs: Any) -> Optional[Source]:
        """Crawl a single URL. Returns Source or None on failure."""

    async def crawl_with_retry(self, url: str, **kwargs: Any) -> Optional[Source]:
        """Crawl with retry and exponential backoff."""
        last_error: Optional[Exception] = None
        for attempt in range(config.crawl.max_retry):
            try:
                async with self._semaphore, self._platform_semaphore:
                    result = await asyncio.wait_for(
                        self.crawl_single(url, **kwargs),
                        timeout=config.crawl.request_timeout,
                    )
                # Rate limit outside semaphore so concurrency slots stay available
                await asyncio.sleep(config.crawl.request_interval)
                return result
            except asyncio.TimeoutError:
                last_error = TimeoutError(f"Timeout after {config.crawl.request_timeout}s")
                logger.warning(f"[{self.platform.value}] Timeout on {url} (attempt {attempt + 1})")
            except Exception as e:
                last_error = e
                logger.warning(f"[{self.platform.value}] Error on {url} (attempt {attempt + 1}): {e}")

            if attempt < config.crawl.max_retry - 1:
                wait = config.crawl.retry_backoff ** attempt
                logger.info(f"[{self.platform.value}] Retrying {url} in {wait}s...")
                await asyncio.sleep(wait)

        logger.error(f"[{self.platform.value}] Failed {url} after {config.crawl.max_retry} attempts: {last_error}")
        return None
