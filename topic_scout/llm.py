"""LLM adapter — OpenAI-compatible format, supports MiMo/DeepSeek/Kimi/MiniMax/通义."""

from __future__ import annotations

import logging
from typing import Optional

from openai import AsyncOpenAI

from .config import config

logger = logging.getLogger(__name__)

# Models that only accept temperature=1
TEMPERATURE_LOCKED_MODELS = {"kimi-k2.5", "kimi-k2.6", "kimi-k2-thinking", "kimi-k2-thinking-turbo"}


def _get_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=config.llm.base_url,
        api_key=config.llm.api_key,
        timeout=config.llm.timeout,
    )


def _effective_temperature(requested: Optional[float], model_name: str) -> float:
    """Return temperature, forcing 1 for models that require it."""
    if model_name in TEMPERATURE_LOCKED_MODELS:
        return 1.0
    return requested if requested is not None else config.llm.temperature


async def chat_completion(
    messages: list[dict],
    *,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    model: Optional[str] = None,
) -> str:
    """Call the LLM with messages. Returns assistant reply text."""
    client = _get_client()
    model_name = model or config.llm.model_name
    response = await client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=_effective_temperature(temperature, model_name),
        max_tokens=max_tokens or config.llm.max_tokens,
    )
    return response.choices[0].message.content or ""


async def test_connection() -> tuple[bool, str]:
    """Test if the LLM API is reachable. Returns (success, message)."""
    try:
        client = _get_client()
        model_name = config.llm.model_name
        response = await client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Hi"}],
            temperature=_effective_temperature(None, model_name),
            max_tokens=10,
        )
        return True, f"Connected to {model_name}"
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
