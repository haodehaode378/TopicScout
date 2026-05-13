"""Tests for the LLM adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from topic_scout.llm import chat_completion, summarize_single, test_connection


class TestChatCompletion:
    @pytest.mark.asyncio
    async def test_returns_assistant_content(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Hello there!"))]

        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("topic_scout.llm._get_client", return_value=mock_client):
            result = await chat_completion([{"role": "user", "content": "Hi"}])
            assert result == "Hello there!"

    @pytest.mark.asyncio
    async def test_uses_custom_model(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="OK"))]

        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("topic_scout.llm._get_client", return_value=mock_client):
            await chat_completion([{"role": "user", "content": "test"}], model="custom-model")
            mock_client.chat.completions.create.assert_called_once()
            call_args = mock_client.chat.completions.create.call_args
            assert call_args.kwargs["model"] == "custom-model"

    @pytest.mark.asyncio
    async def test_returns_empty_string_on_none_content(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=None))]

        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("topic_scout.llm._get_client", return_value=mock_client):
            result = await chat_completion([{"role": "user", "content": "test"}])
            assert result == ""


class TestTestConnection:
    @pytest.mark.asyncio
    async def test_success(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Hi"))]

        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("topic_scout.llm._get_client", return_value=mock_client):
            success, msg = await test_connection()
            assert success is True
            assert "Connected" in msg

    @pytest.mark.asyncio
    async def test_failure(self):
        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = Exception("Connection refused")

        with patch("topic_scout.llm._get_client", return_value=mock_client):
            success, msg = await test_connection()
            assert success is False
            assert "Connection refused" in msg


class TestSummarizeSingle:
    @pytest.mark.asyncio
    async def test_empty_content(self):
        result = await summarize_single("")
        assert result == "暂无内容"

    @pytest.mark.asyncio
    async def test_normal_content(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="This is the summary."))]

        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("topic_scout.llm._get_client", return_value=mock_client):
            result = await summarize_single("Some long content here")
            assert result == "This is the summary."

    @pytest.mark.asyncio
    async def test_llm_failure_returns_fallback(self):
        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = Exception("API error")

        with patch("topic_scout.llm._get_client", return_value=mock_client):
            result = await summarize_single("Some content")
            assert result == "暂无总结"
