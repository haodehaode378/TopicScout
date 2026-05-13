"""Tests for the summarizer."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from topic_scout.models import Platform, Source
from topic_scout.summarizer import (
    _parse_categories,
    _parse_summary_response,
    categorize_sources,
    generate_summary,
)


class TestParseSummaryResponse:
    def test_full_response(self):
        text = """---SUMMARY---
AI视频生成领域快速发展，Sora和CogVideoX是主要代表。
---INSIGHTS---
- Sora 仍是最强商业方案
- 开源方案追赶迅速
- 长视频仍是难题
---RELIABILITY---
整体信息较为可靠，但部分数据可能过时。"""
        summary, insights, reliability = _parse_summary_response(text)
        assert "AI视频生成" in summary
        assert len(insights) == 3
        assert "Sora" in insights[0]
        assert "较为可靠" in reliability

    def test_missing_sections(self):
        text = "Just a plain summary without markers"
        summary, insights, reliability = _parse_summary_response(text)
        assert summary == text
        assert len(insights) == 0
        assert reliability == ""

    def test_partial_response(self):
        text = """---SUMMARY---
This is the summary.
---INSIGHTS---
- Insight 1"""
        summary, insights, reliability = _parse_summary_response(text)
        assert summary == "This is the summary."
        assert len(insights) == 1
        assert reliability == ""


class TestParseCategories:
    def test_normal_output(self):
        text = """商业产品: src_001, src_005
开源模型: src_003, src_008
其他: src_002"""
        result = _parse_categories(text)
        assert "商业产品" in result
        assert "src_001" in result["商业产品"]
        assert "开源模型" in result
        assert len(result["开源模型"]) == 2

    def test_empty_output(self):
        result = _parse_categories("")
        assert result == {}

    def test_malformed_lines_skipped(self):
        text = """商业产品: src_001
bad line without colon
其他: src_002"""
        result = _parse_categories(text)
        assert "商业产品" in result
        assert "其他" in result
        assert len(result) == 2


class TestGenerateSummary:
    @pytest.mark.asyncio
    async def test_llm_failure_returns_fallback(self):
        sources = [
            Source(id="src_1", topic_id="t1", platform=Platform.WEB, title="Test", content="Content"),
        ]
        with patch("topic_scout.summarizer.chat_completion", side_effect=Exception("API error")):
            result = await generate_summary(sources)
            assert result.content == "暂无总结"
            assert result.key_insights == []

    @pytest.mark.asyncio
    async def test_normal_summary(self):
        sources = [
            Source(id="src_1", topic_id="t1", platform=Platform.WEB, title="Test", summary="A summary"),
        ]
        response = """---SUMMARY---
The main summary.
---INSIGHTS---
- Insight 1
- Insight 2
---RELIABILITY---
Good reliability."""

        with patch("topic_scout.summarizer.chat_completion", return_value=response):
            result = await generate_summary(sources)
            assert "main summary" in result.content
            assert len(result.key_insights) == 2
            assert result.reliability == "Good reliability."


class TestCategorizeSources:
    @pytest.mark.asyncio
    async def test_llm_failure_returns_other(self):
        sources = [
            Source(id="src_1", topic_id="t1", platform=Platform.WEB, title="Test"),
        ]
        with patch("topic_scout.summarizer.chat_completion", side_effect=Exception("API error")):
            result = await categorize_sources(sources)
            assert "其他" in result
            assert "src_1" in result["其他"]

    @pytest.mark.asyncio
    async def test_merges_singletons(self):
        sources = [
            Source(id="src_1", topic_id="t1", platform=Platform.WEB, title="A"),
            Source(id="src_2", topic_id="t1", platform=Platform.WEB, title="B"),
            Source(id="src_3", topic_id="t1", platform=Platform.WEB, title="C"),
            Source(id="src_4", topic_id="t1", platform=Platform.WEB, title="D"),
            Source(id="src_5", topic_id="t1", platform=Platform.WEB, title="E"),
            Source(id="src_6", topic_id="t1", platform=Platform.WEB, title="F"),
            Source(id="src_7", topic_id="t1", platform=Platform.WEB, title="G"),
        ]
        response = """开源: src_1, src_2, src_3
商业: src_4
学术: src_5
其他: src_6, src_7"""

        with patch("topic_scout.summarizer.chat_completion", return_value=response):
            result = await categorize_sources(sources)
            # With 3+ non-singleton categories, one singleton kept for min 3,
            # the rest merged into 其他
            assert len(result) >= 3
            assert "src_1" in result["开源"]
            assert "src_6" in result.get("其他", [])
            # One singleton goes to 其他
            assert "src_5" in result.get("其他", [])

    @pytest.mark.asyncio
    async def test_enforces_minimum_categories(self):
        sources = [
            Source(id="src_1", topic_id="t1", platform=Platform.WEB, title="A"),
            Source(id="src_2", topic_id="t1", platform=Platform.WEB, title="B"),
            Source(id="src_3", topic_id="t1", platform=Platform.WEB, title="C"),
        ]
        response = """商业: src_1
开源: src_2
其他: src_3"""

        with patch("topic_scout.summarizer.chat_completion", return_value=response):
            result = await categorize_sources(sources)
            # All singletons — keeps at least 3 categories
            assert len(result) >= 3
