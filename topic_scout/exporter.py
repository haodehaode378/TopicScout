"""JSON / PDF export."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Optional

from . import db as db_module
from .config import config
from .models import Source, Summary, Topic, source_to_dict, topic_to_dict

logger = logging.getLogger(__name__)


def export_json(
    topic: Topic,
    sources: list[Source],
    summary: Optional[Summary] = None,
    versions: Optional[list[dict]] = None,
) -> str:
    """Export topic data to JSON file. Returns file path."""
    categories_map: dict[str, list[str]] = {}
    for s in sources:
        cat = s.category or "其他"
        categories_map.setdefault(cat, []).append(s.id)

    data = {
        "meta": {
            "topic_id": topic.id,
            "keyword": topic.keyword,
            "title": topic.title,
            "description": topic.description,
            "categories": list(categories_map.keys()),
            "crawl_versions": [v["version"] for v in (versions or [])],
            "created_at": topic.created_at,
            "exported_at": datetime.now().isoformat(),
            "total_sources": len(sources),
        },
        "summary": {
            "content": summary.content if summary else "",
            "key_insights": summary.key_insights if summary else [],
            "reliability": summary.reliability if summary else "",
        } if summary else None,
        "categories": [
            {"name": name, "sources": ids}
            for name, ids in categories_map.items()
        ],
        "sources": [source_to_dict(s) for s in sources],
    }

    export_dir = config.storage.exports_dir
    os.makedirs(export_dir, exist_ok=True)
    filename = f"{topic.id}_latest.json"
    path = os.path.join(export_dir, filename)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return path


def _build_pdf_html(
    topic: Topic,
    sources: list[Source],
    summary: Optional[Summary],
    include_summary: bool,
    include_categories: bool,
    full_content: bool,
) -> str:
    """Build complete HTML document for PDF conversion."""

    # Group sources by category
    categories_map: dict[str, list[Source]] = {}
    for s in sources:
        cat = s.category or "其他"
        categories_map.setdefault(cat, []).append(s)

    # Build TOC
    toc_items = []
    if include_summary and summary:
        toc_items.append('<li><a href="#summary">全局总结</a></li>')
    if include_categories:
        for cat in categories_map:
            toc_items.append(f'<li><a href="#cat-{cat}">{cat}</a></li>')
    toc_items.append(f'<li><a href="#sources">全部来源 ({len(sources)}条)</a></li>')

    # Build summary section
    summary_html = ""
    if include_summary and summary:
        insights = "".join(f"<li>{i}</li>" for i in summary.key_insights)
        summary_html = f"""
        <section id="summary">
            <h2>全局总结</h2>
            <p>{summary.content}</p>
            {'<h3>关键洞察</h3><ul>' + insights + '</ul>' if summary.key_insights else ''}
            {f'<p class="reliability">可靠度评估：{summary.reliability}</p>' if summary.reliability else ''}
        </section>
        """

    # Build categories section
    categories_html = ""
    if include_categories:
        for cat, cat_sources in categories_map.items():
            source_list = "".join(f"<li>{s.title or s.url}</li>" for s in cat_sources)
            categories_html += f"""
            <section id="cat-{cat}">
                <h2>{cat} ({len(cat_sources)}条)</h2>
                <ul>{source_list}</ul>
            </section>
            """

    # Build sources section
    sources_html = ""
    for i, s in enumerate(sources, 1):
        content_part = s.content if full_content else (s.summary or s.content[:500])
        content_html = content_part.replace("\n", "<br>") if content_part else "无内容"
        platform_names = {
            "web": "网页", "bilibili": "B站", "douyin": "抖音",
            "weibo": "微博", "zhihu": "知乎", "xiaohongshu": "小红书",
        }
        platform_label = platform_names.get(s.platform.value if hasattr(s.platform, "value") else s.platform, "网页")

        sources_html += f"""
        <article class="source">
            <h3>{i}. {s.title or '无标题'}</h3>
            <div class="meta">
                <span class="platform">{platform_label}</span>
                {f'<span class="author">{s.author}</span>' if s.author else ''}
                <span class="confidence">置信度: {s.confidence:.0%}</span>
                {s.url and f'<span class="url"><a href="{s.url}">{s.url[:80]}</a></span>'}
            </div>
            {f'<div class="summary-block"><strong>AI 总结：</strong>{s.summary}</div>' if s.summary else ''}
            <div class="content">{content_html}</div>
        </article>
        """

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{topic.title or topic.keyword}</title>
<style>
@page {{
    size: A4;
    margin: 2cm;
    @bottom-center {{
        content: counter(page) " / " counter(pages);
        font-size: 10px;
        color: #888;
    }}
}}
body {{
    font-family: "Noto Sans SC", "Microsoft YaHei", "PingFang SC", sans-serif;
    font-size: 14px;
    line-height: 1.8;
    color: #333;
    max-width: 210mm;
    margin: 0 auto;
}}
.cover {{
    text-align: center;
    padding: 60px 0;
    page-break-after: always;
}}
.cover h1 {{
    font-size: 28px;
    margin-bottom: 20px;
    color: #1a1a1a;
}}
.cover .meta-info {{
    font-size: 14px;
    color: #666;
    line-height: 2;
}}
.toc {{
    page-break-after: always;
}}
.toc h2 {{
    font-size: 20px;
    margin-bottom: 16px;
}}
.toc ul {{
    list-style: none;
    padding: 0;
}}
.toc li {{
    padding: 4px 0;
    border-bottom: 1px dotted #ddd;
}}
.toc a {{
    color: #4f46e5;
    text-decoration: none;
}}
section {{
    page-break-before: always;
    margin-bottom: 30px;
}}
h2 {{
    font-size: 20px;
    color: #1a1a1a;
    border-bottom: 2px solid #4f46e5;
    padding-bottom: 8px;
    margin-bottom: 16px;
}}
h3 {{
    font-size: 16px;
    color: #333;
}}
.source {{
    margin-bottom: 30px;
    padding: 16px;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    page-break-inside: avoid;
}}
.meta {{
    font-size: 12px;
    color: #888;
    margin: 8px 0;
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
}}
.platform {{
    background: #eef2ff;
    color: #4f46e5;
    padding: 2px 8px;
    border-radius: 4px;
}}
.summary-block {{
    background: #f9fafb;
    padding: 12px;
    border-radius: 4px;
    margin: 12px 0;
    font-size: 13px;
}}
.content {{
    font-size: 13px;
    line-height: 1.8;
    color: #555;
}}
.reliability {{
    font-style: italic;
    color: #888;
    margin-top: 12px;
}}
ul {{
    padding-left: 20px;
}}
li {{
    margin-bottom: 4px;
}}
a {{
    color: #4f46e5;
}}
</style>
</head>
<body>

<!-- Cover Page -->
<div class="cover">
    <h1>{topic.title or topic.keyword}</h1>
    <div class="meta-info">
        <p>关键词：{topic.keyword}</p>
        <p>来源数量：{len(sources)} 条</p>
        <p>生成时间：{now}</p>
        {f'<p>主题描述：{topic.description}</p>' if topic.description else ''}
    </div>
</div>

<!-- Table of Contents -->
<div class="toc">
    <h2>目录</h2>
    <ul>
        {''.join(toc_items)}
    </ul>
</div>

<!-- Summary -->
{summary_html}

<!-- Categories -->
{categories_html}

<!-- Sources -->
<section id="sources">
    <h2>全部来源</h2>
    {sources_html}
</section>

</body>
</html>"""


def export_pdf(
    topic: Topic,
    sources: list[Source],
    summary: Optional[Summary] = None,
    include_summary: bool = True,
    include_categories: bool = True,
    full_content: bool = True,
) -> str:
    """Export topic to PDF file. Returns file path."""
    export_dir = config.storage.exports_dir
    os.makedirs(export_dir, exist_ok=True)

    html = _build_pdf_html(topic, sources, summary, include_summary, include_categories, full_content)
    filename = f"{topic.id}_latest.pdf"
    path = os.path.join(export_dir, filename)

    # Try WeasyPrint first
    try:
        from weasyprint import HTML
        HTML(string=html).write_pdf(path)
        return path
    except ImportError:
        logger.warning("WeasyPrint not installed, falling back to HTML export")
    except Exception as e:
        logger.warning(f"WeasyPrint failed: {e}, falling back to HTML export")

    # Fallback: write HTML file
    html_path = path.replace(".pdf", ".html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    return html_path
