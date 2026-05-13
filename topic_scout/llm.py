"""LLM adapter — OpenAI-compatible format, supports MiMo/DeepSeek/Kimi/MiniMax/通义."""

from __future__ import annotations

import logging
from typing import Optional

from openai import AsyncOpenAI

from .config import config

logger = logging.getLogger(__name__)


def _get_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=config.llm.base_url,
        api_key=config.llm.api_key,
        timeout=config.llm.timeout,
    )


async def chat_completion(
    messages: list[dict],
    *,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    model: Optional[str] = None,
) -> str:
    """Call the LLM with messages. Returns assistant reply text."""
    client = _get_client()
    response = await client.chat.completions.create(
        model=model or config.llm.model_name,
        messages=messages,
        temperature=temperature if temperature is not None else config.llm.temperature,
        max_tokens=max_tokens or config.llm.max_tokens,
    )
    return response.choices[0].message.content or ""


async def test_connection() -> tuple[bool, str]:
    """Test if the LLM API is reachable. Returns (success, message)."""
    try:
        client = _get_client()
        response = await client.chat.completions.create(
            model=config.llm.model_name,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=10,
        )
        return True, f"Connected to {config.llm.model_name}"
    except Exception as e:
        return False, str(e)


async def summarize_single(content: str) -> str:
    """Summarize a single piece of content in 1-2 sentences."""
    if not content.strip():
        return "暂无内容"
    try:
        return await chat_completion(
            [
                {"role": "system", "content": "用 1-2 句话总结以下内容的核心信息。不要废话，直接说重点。"},
                {"role": "user", "content": content[:3000]},
            ],
            max_tokens=256,
        )
    except Exception as e:
        logger.warning(f"Single summary failed: {e}")
        return "暂无总结"
