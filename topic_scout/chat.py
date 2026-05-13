"""AI conversation logic — keyword → refinement chat → [READY] detection."""

from __future__ import annotations

import logging
import re
from typing import Optional

from .llm import chat_completion

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个研究助理。用户给你一个关键词，你需要通过对话帮他明确研究主题。

你的任务：
1. 理解用户想研究什么
2. 通过提问缩小范围、明确方向
3. 判断什么时候你已经足够理解主题

提问规则：
- 每次只问 1-2 个问题，不要一次问太多
- 问题要具体，不要问"你想研究什么方向"这种太宽泛的
- 优先问：时间范围、地域范围、关注角度、深度要求
- 语气自然，像聊天不像问卷

判断何时理解清楚的信号：
- 你能用一句话准确描述这个主题的研究范围
- 你清楚知道要爬哪些类型的内容
- 你不会再问出有价值的新问题

当你认为已经理解清楚时，在回复末尾加上特殊标记：
[READY] 主题标题 | 一句话描述"""


async def process_chat(
    messages: list[dict],
) -> tuple[str, Optional[str], Optional[str]]:
    """Process a chat turn. Returns (reply, title_or_none, description_or_none).

    If [READY] detected, extracts title and description.
    If chat exceeds max_turns without READY, auto-confirms.
    """
    # Build messages with system prompt
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    reply = await chat_completion(full_messages, max_tokens=1024)

    # Check for [READY] marker
    ready_match = re.search(r"\[READY\]\s*(.+?)\s*\|\s*(.+)", reply)
    if ready_match:
        title = ready_match.group(1).strip()
        description = ready_match.group(2).strip()
        # Remove the marker from the reply shown to user
        clean_reply = re.sub(r"\s*\[READY\].*$", "", reply).strip()
        return clean_reply, title, description

    return reply, None, None


def auto_confirm(keyword: str, messages: list[dict]) -> tuple[str, str]:
    """Auto-confirm when chat exceeds max turns. Build title and description from conversation."""
    title = keyword
    description = keyword
    # Try to extract a better description from user messages
    user_texts = [m["content"] for m in messages if m["role"] == "user"]
    if user_texts:
        description = "；".join(user_texts[:5])
    return title, description
