"""FastAPI HTTP API — all endpoints defined in CLAUDE.md."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from . import db
from .chat import auto_confirm, process_chat
from .config import config
from .crawler.bilibili import BilibiliCrawler
from .crawler.douyin import DouyinCrawler
from .crawler.weibo import WeiboCrawler
from .crawler.web import WebCrawler
from .crawler.xiaohongshu import XiaohongshuCrawler
from .crawler.zhihu import ZhihuCrawler
from .exporter import export_json
from .llm import test_connection
from .models import (
    ChatMessage,
    CrawlVersion,
    Platform,
    Source,
    Summary,
    Task,
    TaskStatus,
    TaskType,
    Topic,
    TopicStatus,
    source_to_dict,
    task_to_dict,
    topic_to_dict,
)
from .summarizer import categorize_sources, generate_summary

logger = logging.getLogger(__name__)

app = FastAPI(title="TopicScout", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory SSE event queues per topic
_sse_queues: dict[str, asyncio.Queue] = {}

# Active crawl tasks
_active_crawls: dict[str, asyncio.Task] = {}

MAX_CHAT_TURNS = 10


def _get_sse_queue(topic_id: str) -> asyncio.Queue:
    if topic_id not in _sse_queues:
        _sse_queues[topic_id] = asyncio.Queue()
    return _sse_queues[topic_id]


async def _push_sse(topic_id: str, data: dict) -> None:
    queue = _get_sse_queue(topic_id)
    await queue.put(data)


# --- Pydantic models for request bodies ---

class CreateTopicRequest(BaseModel):
    keyword: str


class ChatRequest(BaseModel):
    content: str


class ConfirmRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class CrawlRequest(BaseModel):
    platforms: list[str] = ["web", "bilibili"]
    urls: list[str] = []


class UpdateSourceRequest(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    category: Optional[str] = None
    confidence: Optional[float] = None
    useful: Optional[int] = None
    content: Optional[str] = None

    def model_post_init(self, __context: object) -> None:
        if self.useful is not None and self.useful not in (-1, 0, 1):
            raise ValueError("useful must be -1, 0, or 1")
        if self.confidence is not None and not (0 <= self.confidence <= 1):
            raise ValueError("confidence must be between 0 and 1")


class UpdateConfigRequest(BaseModel):
    llm: Optional[dict] = None
    crawl: Optional[dict] = None
    storage: Optional[dict] = None
    frontend: Optional[dict] = None


# --- Topics ---

@app.post("/api/topics", status_code=201)
async def create_topic(req: CreateTopicRequest):
    topic_id = f"topic_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}"
    topic = Topic(id=topic_id, keyword=req.keyword)
    created = await db.create_topic(topic)
    # Auto-send first AI message
    messages = [{"role": "user", "content": req.keyword}]
    reply, title, desc = await process_chat(messages)
    # Save both messages
    await db.add_chat_message(ChatMessage(topic_id=topic_id, role="user", content=req.keyword))
    await db.add_chat_message(ChatMessage(topic_id=topic_id, role="assistant", content=reply))
    return {
        "topic": topic_to_dict(created),
        "ai_reply": reply,
        "title": title,
        "description": desc,
        "is_ready": title is not None,
    }


@app.get("/api/topics")
async def list_topics():
    topics = await db.list_topics()
    result = []
    for t in topics:
        d = topic_to_dict(t)
        d["source_count"] = await db.count_sources(t.id)
        result.append(d)
    return result


@app.get("/api/topics/{topic_id}")
async def get_topic(topic_id: str):
    topic = await db.get_topic(topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")
    return topic_to_dict(topic)


@app.delete("/api/topics/{topic_id}")
async def delete_topic(topic_id: str):
    topic = await db.get_topic(topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")
    # Cancel active crawl if any
    if topic_id in _active_crawls:
        _active_crawls[topic_id].cancel()
        del _active_crawls[topic_id]
    await db.delete_topic(topic_id)
    return {"ok": True}


# --- Chat ---

@app.post("/api/topics/{topic_id}/chat")
async def send_chat(topic_id: str, req: ChatRequest):
    topic = await db.get_topic(topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")
    if topic.status != TopicStatus.CHATTING:
        raise HTTPException(400, "Topic is not in chatting status")

    # Save user message
    await db.add_chat_message(ChatMessage(topic_id=topic_id, role="user", content=req.content))

    # Get chat history
    history = await db.get_chat_messages(topic_id)
    messages = [{"role": m.role, "content": m.content} for m in history]

    # Check turn count
    user_turns = sum(1 for m in history if m.role == "user")

    if user_turns > MAX_CHAT_TURNS:
        # Auto-confirm
        title, desc = auto_confirm(topic.keyword, messages)
        reply = f"我们已经聊了{user_turns}轮，我来帮你确认一下主题。"
        await db.add_chat_message(ChatMessage(topic_id=topic_id, role="assistant", content=reply))
        return {
            "reply": reply,
            "title": title,
            "description": desc,
            "is_ready": True,
            "auto_confirmed": True,
        }

    reply, title, desc = await process_chat(messages)
    await db.add_chat_message(ChatMessage(topic_id=topic_id, role="assistant", content=reply))

    return {
        "reply": reply,
        "title": title,
        "description": desc,
        "is_ready": title is not None,
        "auto_confirmed": False,
    }


@app.get("/api/topics/{topic_id}/chat")
async def get_chat_history(topic_id: str):
    topic = await db.get_topic(topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")
    messages = await db.get_chat_messages(topic_id)
    return [
        {"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at}
        for m in messages
    ]


@app.post("/api/topics/{topic_id}/chat/{message_id}/rollback")
async def rollback_chat(topic_id: str, message_id: int):
    """Rollback chat to a specific message — delete all messages after it."""
    topic = await db.get_topic(topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")
    await db.delete_chat_after(topic_id, message_id)
    return {"ok": True}


@app.post("/api/topics/{topic_id}/confirm")
async def confirm_topic(topic_id: str, req: ConfirmRequest):
    topic = await db.get_topic(topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")

    # Get title/description from request or from last AI message
    title = req.title
    description = req.description

    if not title or not description:
        history = await db.get_chat_messages(topic_id)
        # Try to find [READY] in last assistant message
        for m in reversed(history):
            if m.role == "assistant":
                import re
                match = re.search(r"\[READY\]\s*(.+?)\s*\|\s*(.+)", m.content)
                if match:
                    title = title or match.group(1).strip()
                    description = description or match.group(2).strip()
                    break

    title = title or topic.keyword
    description = description or topic.keyword

    await db.update_topic(
        topic_id,
        title=title,
        description=description,
        status=TopicStatus.CRAWLING,
    )
    return {"ok": True, "title": title, "description": description}


# --- Crawl ---

@app.post("/api/topics/{topic_id}/crawl", status_code=202)
async def trigger_crawl(topic_id: str, req: CrawlRequest):
    topic = await db.get_topic(topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")

    # Check for active crawl
    if topic_id in _active_crawls and not _active_crawls[topic_id].done():
        raise HTTPException(400, "已有爬取任务在进行中")

    task_id = f"task_{uuid.uuid4().hex[:8]}"
    task = Task(
        id=task_id,
        topic_id=topic_id,
        type=TaskType.CRAWL,
        status=TaskStatus.RUNNING,
        detail="开始爬取...",
    )
    await db.create_task(task)

    # Create crawl version
    version = await db.get_next_crawl_version(topic_id)
    cv = CrawlVersion(topic_id=topic_id, version=version, status="running")
    cv = await db.create_crawl_version(cv)

    # Start async crawl
    crawl_task = asyncio.create_task(
        _run_crawl(topic_id, task_id, version, cv.id, req.platforms, req.urls)
    )
    _active_crawls[topic_id] = crawl_task

    await db.update_topic(topic_id, status=TopicStatus.CRAWLING)

    return {"task_id": task_id, "version": version}


async def _run_crawl(
    topic_id: str,
    task_id: str,
    version: int,
    cv_id: int,
    platforms: list[str],
    urls: list[str],
) -> None:
    """Background crawl task with multi-platform support."""
    logger.info(f"[crawl] START: topic={topic_id}, platforms={platforms}, urls={len(urls)}")
    try:
        await db.update_task(task_id, status=TaskStatus.RUNNING, detail="正在爬取...")

        sources_found = 0
        total = len(urls) if urls else 0

        # Build crawlers map
        crawler_map: dict[str, type] = {
            "web": WebCrawler,
            "bilibili": BilibiliCrawler,
            "douyin": DouyinCrawler,
            "weibo": WeiboCrawler,
            "zhihu": ZhihuCrawler,
            "xiaohongshu": XiaohongshuCrawler,
        }

        platform_urls: dict[str, list[str]] = {p: [] for p in platforms}

        # If no URLs provided, search across platforms
        if not urls:
            topic = await db.get_topic(topic_id)
            search_q = (topic.title if topic else "") or (topic.keyword if topic else "")
            per_platform = max(5, config.crawl.max_items_per_source // max(len(platforms), 1))
            logger.info(f"[crawl] SEARCH: platforms={platforms}, q={search_q[:50]}, per={per_platform}")

            # Search each platform in parallel
            search_tasks = {}
            if "bilibili" in platforms:
                search_tasks["bilibili"] = BilibiliCrawler.search_urls(search_q, max_results=per_platform)
            if "web" in platforms:
                search_tasks["web"] = WebCrawler.search_urls(f"{search_q} 最新", max_results=per_platform)

            results = await asyncio.gather(*search_tasks.values(), return_exceptions=True)
            for platform_name, result in zip(search_tasks.keys(), results):
                if isinstance(result, Exception):
                    logger.warning(f"Search failed for {platform_name}: {result}")
                    continue
                logger.info(f"[search] {platform_name}: found {len(result)} URLs")
                platform_urls[platform_name].extend(result)
                urls.extend(result)
                logger.info(f"[crawl] RESULT: {platform_name} -> {len(result)} URLs")

            total = len(urls) if urls else 0
        else:
            # Distribute provided URLs to platform crawlers
            for url in urls:
                assigned = False
                for p in platforms:
                    crawler_cls = crawler_map.get(p)
                    if crawler_cls and crawler_cls.can_handle(url):
                        platform_urls[p].append(url)
                        assigned = True
                        break
                if not assigned:
                    platform_urls.setdefault("web", []).append(url)

        # Crawl each platform
        for platform_name in platforms:
            p_urls = platform_urls.get(platform_name, [])
            if not p_urls:
                continue

            crawler_cls = crawler_map.get(platform_name, WebCrawler)
            crawler = crawler_cls()

            for i, url in enumerate(p_urls):
                try:
                    source = await crawler.crawl_with_retry(
                        url, topic_id=topic_id, version=version
                    )
                    if source:
                        if not await db.source_exists(topic_id, url):
                            await db.add_source(source)
                            sources_found += 1
                            progress = int((sources_found) / max(total, 1) * 100)
                            await _push_sse(topic_id, {
                                "type": "source",
                                "source": source_to_dict(source),
                                "progress": min(progress, 99),
                                "detail": f"已爬取 {platform_name} {i + 1}/{len(p_urls)}",
                            })
                        else:
                            logger.info(f"Duplicate URL skipped: {url}")
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.warning(f"Failed to crawl {url}: {e}")
                    await _push_sse(topic_id, {
                        "type": "error",
                        "url": url,
                        "error": str(e),
                    })

                progress = int((sources_found) / max(total, 1) * 100)
                await db.update_task(task_id, progress=min(progress, 99), detail=f"正在爬取 {platform_name} {i + 1}/{len(p_urls)}")

        # Update crawl version
        from datetime import datetime as dt
        await db.update_crawl_version(
            cv_id=cv_id,
            source_count=sources_found,
            status="done",
            finished_at=dt.now().isoformat(),
        )

        await db.update_task(task_id, status=TaskStatus.DONE, progress=100, detail=f"完成，共 {sources_found} 条")
        await db.update_topic(topic_id, status=TopicStatus.DONE)

        if sources_found == 0:
            await _push_sse(topic_id, {
                "type": "no_results",
                "detail": "未找到相关内容",
            })

        await _push_sse(topic_id, {
            "type": "done",
            "total_sources": sources_found,
            "detail": f"爬取完成，共 {sources_found} 条来源",
        })

    except asyncio.CancelledError:
        await db.update_task(task_id, status=TaskStatus.ERROR, error_msg="用户取消")
        await _push_sse(topic_id, {"type": "cancelled"})
    except Exception as e:
        logger.error(f"[crawl] ERROR: {type(e).__name__}: {e}")
        logger.exception(f"Crawl failed for {topic_id}")
        await db.update_task(task_id, status=TaskStatus.ERROR, error_msg=str(e))
        await db.update_topic(topic_id, status=TopicStatus.ERROR)
        await _push_sse(topic_id, {"type": "error", "error": str(e)})


@app.get("/api/topics/{topic_id}/crawl/status")
async def crawl_status(topic_id: str):
    """SSE endpoint for real-time crawl progress."""
    topic = await db.get_topic(topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")

    async def event_generator():
        queue = _get_sse_queue(topic_id)
        while True:
            try:
                data = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield {"data": json.dumps(data, ensure_ascii=False)}
                if data.get("type") in ("done", "error", "cancelled"):
                    break
            except asyncio.TimeoutError:
                yield {"data": json.dumps({"type": "ping"})}

    return EventSourceResponse(event_generator())


@app.get("/api/topics/{topic_id}/sources")
async def get_sources(
    topic_id: str,
    version: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    topic = await db.get_topic(topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")
    sources = await db.get_sources(topic_id, version)

    # Filter by category
    if category:
        sources = [s for s in sources if s.category == category]

    # Search
    if search:
        search_lower = search.lower()
        sources = [s for s in sources if search_lower in s.title.lower() or search_lower in s.content.lower() or search_lower in s.summary.lower()]

    total = len(sources)
    start = (page - 1) * per_page
    sources = sources[start:start + per_page]

    return {
        "sources": [source_to_dict(s) for s in sources],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@app.patch("/api/topics/{topic_id}/sources/{source_id}")
async def update_source(topic_id: str, source_id: str, req: UpdateSourceRequest):
    topic = await db.get_topic(topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No updates provided")
    await db.update_source(source_id, **updates)
    return {"ok": True}


@app.get("/api/topics/{topic_id}/versions")
async def get_versions(topic_id: str):
    topic = await db.get_topic(topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")
    versions = await db.get_crawl_versions(topic_id)
    return [
        {"id": v.id, "version": v.version, "source_count": v.source_count, "status": v.status, "started_at": v.started_at, "finished_at": v.finished_at}
        for v in versions
    ]


# --- Summarize ---

@app.post("/api/topics/{topic_id}/summarize")
async def trigger_summarize(topic_id: str):
    topic = await db.get_topic(topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")

    task_id = f"task_{uuid.uuid4().hex[:8]}"
    task = Task(id=task_id, topic_id=topic_id, type=TaskType.SUMMARIZE, status=TaskStatus.RUNNING)
    await db.create_task(task)

    # Run async
    asyncio.create_task(_run_summarize(topic_id, task_id))

    return {"task_id": task_id}


async def _run_summarize(topic_id: str, task_id: str) -> None:
    try:
        await db.update_task(task_id, progress=20, detail="正在生成总结...")
        sources = await db.get_sources(topic_id)

        if not sources:
            await db.update_task(task_id, status=TaskStatus.DONE, progress=100, detail="无来源数据")
            return

        # Generate summary
        summary = await generate_summary(sources)
        summary.topic_id = topic_id
        await db.save_summary(summary)

        await db.update_task(task_id, progress=60, detail="正在分类...")

        # Categorize
        categories = await categorize_sources(sources)
        category_names = list(categories.keys())

        # Update sources with categories
        for cat_name, source_ids in categories.items():
            for sid in source_ids:
                await db.update_source(sid, category=cat_name)

        # Update topic
        await db.update_topic(
            topic_id,
            status=TopicStatus.DONE,
            categories=category_names,
        )

        await db.update_task(task_id, status=TaskStatus.DONE, progress=100, detail="总结完成")

    except Exception as e:
        logger.exception(f"Summarize failed for {topic_id}")
        await db.update_task(task_id, status=TaskStatus.ERROR, error_msg=str(e))


@app.get("/api/topics/{topic_id}/summary")
async def get_summary(topic_id: str, version: Optional[int] = Query(None)):
    topic = await db.get_topic(topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")
    summary = await db.get_summary(topic_id, version)
    if not summary:
        return None
    return {
        "id": summary.id,
        "content": summary.content,
        "key_insights": summary.key_insights,
        "reliability": summary.reliability,
        "crawl_version": summary.crawl_version,
        "created_at": summary.created_at,
    }


# --- Export ---

class ExportPdfRequest(BaseModel):
    include_summary: bool = True
    include_categories: bool = True
    useful_only: bool = False
    full_content: bool = True


@app.get("/api/topics/{topic_id}/export/json")
async def export_json_endpoint(topic_id: str):
    topic = await db.get_topic(topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")
    sources = await db.get_sources(topic_id)
    summary = await db.get_summary(topic_id)
    versions = await db.get_crawl_versions(topic_id)
    path = export_json(topic, sources, summary, versions=[
        {"version": v.version, "source_count": v.source_count, "status": v.status}
        for v in versions
    ])
    return FileResponse(path, filename=f"{topic.id}.json", media_type="application/json")


@app.post("/api/topics/{topic_id}/export/pdf")
async def export_pdf_endpoint(topic_id: str, req: ExportPdfRequest):
    topic = await db.get_topic(topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")
    sources = await db.get_sources(topic_id)
    if req.useful_only:
        sources = [s for s in sources if s.useful == 1]
    summary = await db.get_summary(topic_id) if req.include_summary else None

    from .exporter import export_pdf
    path = export_pdf(
        topic, sources, summary,
        include_summary=req.include_summary,
        include_categories=req.include_categories,
        full_content=req.full_content,
    )
    return FileResponse(path, filename=f"{topic.id}.pdf", media_type="application/pdf")


# --- Tasks ---

@app.get("/api/tasks")
async def list_tasks(
    topic_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    tasks = await db.list_tasks(topic_id, status)
    return [task_to_dict(t) for t in tasks]


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    task = await db.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task_to_dict(task)


@app.post("/api/tasks/{task_id}/retry")
async def retry_task(task_id: str):
    task = await db.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    if task.type == TaskType.CRAWL:
        await db.update_task(task_id, status=TaskStatus.RUNNING, progress=0, error_msg="", retry_count=task.retry_count + 1)
        version = await db.get_next_crawl_version(task.topic_id)
        cv = CrawlVersion(topic_id=task.topic_id, version=version, status="running")
        cv = await db.create_crawl_version(cv)
        crawl_task = asyncio.create_task(
            _run_crawl(task.topic_id, task_id, version, cv.id, ["web"], [])
        )
        _active_crawls[task.topic_id] = crawl_task
    elif task.type == TaskType.SUMMARIZE:
        await db.update_task(task_id, status=TaskStatus.RUNNING, progress=0, error_msg="", retry_count=task.retry_count + 1)
        asyncio.create_task(_run_summarize(task.topic_id, task_id))
    return {"ok": True}


# --- Config ---

@app.get("/api/config")
async def get_config():
    return {
        "llm": {
            "base_url": config.llm.base_url,
            "model_name": config.llm.model_name,
            "temperature": config.llm.temperature,
            "max_tokens": config.llm.max_tokens,
            "timeout": config.llm.timeout,
            # Don't return api_key for security
        },
        "crawl": {
            "max_depth": config.crawl.max_depth,
            "max_items_per_source": config.crawl.max_items_per_source,
            "request_interval": config.crawl.request_interval,
            "request_timeout": config.crawl.request_timeout,
            "max_concurrent": config.crawl.max_concurrent,
            "max_retry": config.crawl.max_retry,
        },
        "storage": {
            "data_dir": config.storage.data_dir,
            "images_dir": config.storage.images_dir,
            "exports_dir": config.storage.exports_dir,
            "db_path": config.storage.db_path,
            "storage_limit_gb": config.storage.storage_limit_gb,
        },
        "frontend": {
            "port": config.frontend.port,
            "theme": config.frontend.theme,
            "items_per_page": config.frontend.items_per_page,
        },
    }


@app.put("/api/config")
async def update_config(req: UpdateConfigRequest):
    if req.llm:
        for k, v in req.llm.items():
            if hasattr(config.llm, k):
                setattr(config.llm, k, v)
    if req.crawl:
        for k, v in req.crawl.items():
            if hasattr(config.crawl, k):
                setattr(config.crawl, k, v)
    if req.storage:
        for k, v in req.storage.items():
            if hasattr(config.storage, k):
                setattr(config.storage, k, v)
    if req.frontend:
        for k, v in req.frontend.items():
            if hasattr(config.frontend, k):
                setattr(config.frontend, k, v)
    return {"ok": True}


@app.post("/api/config/test")
async def test_llm_connection():
    success, message = await test_connection()
    return {"success": success, "message": message}
