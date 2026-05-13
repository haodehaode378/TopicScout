"""Tests for the crawler system."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from topic_scout.crawler.base import BaseCrawler
from topic_scout.crawler.web import WebCrawler
from topic_scout.models import Platform, Source


@pytest.fixture
def web_crawler():
    return WebCrawler()


class TestBaseCrawler:
    def test_platform_is_web(self, web_crawler: WebCrawler):
        assert web_crawler.platform == Platform.WEB

    def test_has_semaphore(self, web_crawler: WebCrawler):
        assert web_crawler._semaphore is not None
        assert web_crawler._platform_semaphore is not None


class TestWebCrawler:
    def test_extract_title(self, web_crawler: WebCrawler):
        html = '<html><head><title>Test Page Title</title></head></html>'
        assert web_crawler._extract_title(html) == "Test Page Title"

    def test_extract_title_missing(self, web_crawler: WebCrawler):
        html = "<html><body>No title</body></html>"
        assert web_crawler._extract_title(html) == ""

    def test_extract_text(self, web_crawler: WebCrawler):
        html = '<html><body><p>Hello</p> <p>World</p></body></html>'
        text = web_crawler._extract_text(html)
        assert "Hello" in text
        assert "World" in text
        assert "<p>" not in text

    def test_extract_text_removes_scripts(self, web_crawler: WebCrawler):
        html = '<html><body><script>alert("xss")</script><p>Content</p></body></html>'
        text = web_crawler._extract_text(html)
        assert "alert" not in text
        assert "Content" in text

    def test_extract_images(self, web_crawler: WebCrawler):
        html = '<img src="https://example.com/img1.jpg"><img src="/img2.png">'
        images = web_crawler._extract_images(html, "https://example.com/page")
        assert len(images) == 2
        assert "img1.jpg" in images[0]
        assert "img2.png" in images[1]

    def test_extract_images_empty(self, web_crawler: WebCrawler):
        html = "<p>No images here</p>"
        assert web_crawler._extract_images(html, "https://example.com") == []

    @pytest.mark.asyncio
    async def test_crawl_single_returns_none_on_empty_content(self, web_crawler: WebCrawler):
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_resp = AsyncMock()
            mock_resp.text = "<html><body></body></html>"
            mock_resp.raise_for_status = AsyncMock()
            mock_get.return_value = mock_resp
            # Empty text should return None
            with patch.object(web_crawler, "_extract_text", return_value=""):
                result = await web_crawler.crawl_single("https://example.com")
                assert result is None

    @pytest.mark.asyncio
    async def test_crawl_with_retry_returns_none_after_max_retries(self):
        crawler = WebCrawler()

        async def always_fail(*args, **kwargs):
            raise Exception("Network error")

        with patch.object(crawler, "crawl_single", side_effect=always_fail):
            result = await crawler.crawl_with_retry("https://example.com")
            assert result is None

    @pytest.mark.asyncio
    async def test_crawl_with_retry_succeeds_on_second_attempt(self):
        crawler = WebCrawler()
        call_count = 0

        async def succeed_on_second(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Fail once")
            return Source(
                id="src_test",
                topic_id="test",
                platform=Platform.WEB,
                url=url,
                title="Test",
                content="Content",
            )

        with patch.object(crawler, "crawl_single", side_effect=succeed_on_second):
            with patch("topic_scout.crawler.base.config") as mock_config:
                mock_config.crawl.max_retry = 3
                mock_config.crawl.retry_backoff = 0.01
                mock_config.crawl.max_concurrent = 10
                mock_config.crawl.request_interval = 0
                mock_config.crawl.request_timeout = 30
                result = await crawler.crawl_with_retry("https://example.com")
                assert result is not None
                assert result.title == "Test"
