"""AI global summary + categorization."""

from __future__ import annotations

import logging
from typing import Optional

from .llm import chat_completion
from .models import Source, Summary

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM = """你是一个信息分析专家。给你一批爬取到的资料，请生成一份结构化的研究报告。

要求：
1. 总结要全面但不啰嗦，控制在 500-1000 字
2. 关键洞察要尖锐，不要说废话（3-5 条）
3. 指出信息之间的矛盾或争议
4. 标注信息的可靠程度

输出格式（严格遵守）：
---SUMMARY---
（总结正文）
---INSIGHTS---
- 洞察1
- 洞察2
- 洞察3
---RELIABILITY---
（对整体信息可靠性的评估，一句话）"""

CATEGORY_SYSTEM = """你是一个信息分类专家。给你一批资料，请按主题自动归类。

规则：
1. 类别名称用中文，简短（2-6 个字）
2. 每条资料只归入一个主类别
3. 类别数量控制在 3-8 个
4. 如果某条资料确实不属于任何类别，归入"其他"

直接输出分类结果，不要输出任何解释、规则或格式说明。每行一个分类，格式为"类别名: ID1, ID2"。"""


def _parse_summary_response(text: str) -> tuple[str, list[str], str]:
    """Parse the structured summary response."""
    summary = ""
    insights: list[str] = []
    reliability = ""

    parts = text.split("---")
    i = 0
    while i < len(parts):
        part = parts[i].strip()
        if part == "SUMMARY" and i + 1 < len(parts):
            summary = parts[i + 1].strip()
            i += 2
        elif part == "INSIGHTS" and i + 1 < len(parts):
            for line in parts[i + 1].strip().split("\n"):
                line = line.strip()
                if line.startswith("- "):
                    insights.append(line[2:].strip())
                elif line:
                    insights.append(line)
            i += 2
        elif part == "RELIABILITY" and i + 1 < len(parts):
            reliability = parts[i + 1].strip()
            i += 2
        else:
            i += 1

    if not summary:
        summary = text[:1000]

    # Dedup insights by normalized text
    seen: set[str] = set()
    unique_insights: list[str] = []
    for insight in insights:
        norm = insight.lower().strip()
        if norm not in seen:
            seen.add(norm)
            unique_insights.append(insight)

    return summary, unique_insights[:5], reliability


def _parse_categories(text: str) -> dict[str, list[str]]:
    """Parse categorization output. Returns {category: [source_ids]}."""
    import re

    result: dict[str, list[str]] = {}
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or ":" not in line:
            continue
        parts = line.split(":", 1)
        category = parts[0].strip()
        ids = [s.strip() for s in parts[1].split(",") if s.strip()]
        # Skip lines that look like prompt instructions, not real categories
        # Valid categories: short Chinese names (2-6 chars)
        if len(category) > 10:
            continue
        if re.search(r'[a-zA-Z]', category):
            continue
        if any(kw in category for kw in ("规则", "格式", "输出", "类别名", "要求", "示例")):
            continue
        # Validate source IDs look like src_xxx
        ids = [s for s in ids if re.match(r'^src_', s)]
        if category and ids:
            result[category] = ids
    return result


async def generate_summary(sources: list[Source]) -> Summary:
    """Generate global summary from all sources."""
    # Build source context (cap total input)
    source_texts = []
    total = 0
    for s in sources:
        text = f"[{s.id}] {s.title}\n{s.summary or s.content[:300]}"
        if total + len(text) > 30000:
            break
        source_texts.append(text)
        total += len(text)

    content_block = "\n\n".join(source_texts)

    try:
        response = await chat_completion(
            [
                {"role": "system", "content": SUMMARY_SYSTEM},
                {"role": "user", "content": f"以下是爬取到的{len(sources)}条资料：\n\n{content_block}"},
            ],
            max_tokens=2048,
        )
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        return Summary(
            content="暂无总结",
            key_insights=[],
            reliability="LLM 调用失败，无法评估",
        )

    summary_text, insights, reliability = _parse_summary_response(response)
    return Summary(
        content=summary_text[:5000],  # Cap at 5k chars
        key_insights=insights,
        reliability=reliability,
    )


async def categorize_sources(sources: list[Source]) -> dict[str, list[str]]:
    """Auto-categorize sources. Returns {category: [source_ids]}."""
    source_lines = "\n".join(f"[{s.id}] {s.title}" for s in sources)

    try:
        response = await chat_completion(
            [
                {"role": "system", "content": CATEGORY_SYSTEM},
                {"role": "user", "content": f"请对以下{len(sources)}条资料分类：\n\n{source_lines}"},
            ],
            max_tokens=1024,
        )
    except Exception as e:
        logger.error(f"Categorization failed: {e}")
        return {"其他": [s.id for s in sources]}

    categories = _parse_categories(response)

    # Fallback: if nothing parsed, put all in 其他
    if not categories:
        return {"其他": [s.id for s in sources]}

    # Cap at 9 + 其他
    if len(categories) > 10:
        sorted_cats = sorted(categories.items(), key=lambda x: len(x[1]), reverse=True)
        kept = dict(sorted_cats[:9])
        other_ids = [sid for _, ids in sorted_cats[9:] for sid in ids]
        if "其他" in kept:
            kept["其他"].extend(other_ids)
        else:
            kept["其他"] = other_ids
        categories = kept

    # Merge singleton categories — but keep at least 3 categories total
    other_key = "其他"
    merged: dict[str, list[str]] = {}
    singletons: dict[str, list[str]] = {}
    other_ids = list(categories.get(other_key, []))
    for cat, ids in categories.items():
        if cat == other_key:
            continue
        if len(ids) == 1:
            singletons[cat] = ids
        else:
            merged[cat] = ids

    # If merging all singletons would leave us with < 3 categories, keep some
    non_other_count = len(merged)
    if non_other_count + (1 if other_ids else 0) < 3 and singletons:
        # Keep enough singletons to reach 3 total categories
        needed = 3 - non_other_count - (1 if other_ids else 0)
        for cat, ids in list(singletons.items())[:max(needed, 0)]:
            merged[cat] = ids
            del singletons[cat]

    # Remaining singletons go to 其他
    for ids in singletons.values():
        other_ids.extend(ids)
    if other_ids:
        merged[other_key] = other_ids

    return merged
