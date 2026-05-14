"""Data models: Topic, Source, Task, CrawlVersion, Summary, ChatMessage."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class TopicStatus(str, Enum):
    CHATTING = "chatting"
    CRAWLING = "crawling"
    SUMMARIZING = "summarizing"
    DONE = "done"
    ERROR = "error"


class Platform(str, Enum):
    WEB = "web"
    BILIBILI = "bilibili"
    DOUYIN = "douyin"
    WEIBO = "weibo"
    ZHIHU = "zhihu"
    XIAOHONGSHU = "xiaohongshu"
    WECHAT = "wechat"


class TaskType(str, Enum):
    CRAWL = "crawl"
    SUMMARIZE = "summarize"
    EXPORT_PDF = "export_pdf"
    EXPORT_JSON = "export_json"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class Topic:
    id: str
    keyword: str
    title: str = ""
    description: str = ""
    status: TopicStatus = TopicStatus.CHATTING
    categories: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ChatMessage:
    id: int = 0
    topic_id: str = ""
    role: str = "user"  # "user" or "assistant"
    content: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Source:
    id: str
    topic_id: str
    platform: Platform = Platform.WEB
    url: str = ""
    title: str = ""
    content: str = ""
    summary: str = ""
    images: list[str] = field(default_factory=list)
    author: str = ""
    publish_time: str = ""
    crawl_time: str = field(default_factory=lambda: datetime.now().isoformat())
    confidence: float = 0.0
    category: str = ""
    useful: int = -1  # 1=useful, 0=not useful, -1=unmarked
    crawl_version: int = 1


@dataclass
class CrawlVersion:
    id: int = 0
    topic_id: str = ""
    version: int = 1
    source_count: int = 0
    status: str = "running"
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    finished_at: str = ""


@dataclass
class Task:
    id: str = ""
    topic_id: str = ""
    type: TaskType = TaskType.CRAWL
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0
    detail: str = ""
    error_msg: str = ""
    retry_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Summary:
    id: int = 0
    topic_id: str = ""
    crawl_version: int = 1
    content: str = ""
    key_insights: list[str] = field(default_factory=list)
    reliability: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class WxAccount:
    id: str  # fakeid
    nickname: str = ""
    alias: str = ""
    avatar_url: str = ""
    subscribed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_crawl_at: str = ""
    status: str = "active"


def topic_to_dict(t: Topic) -> dict:
    return {
        "id": t.id,
        "keyword": t.keyword,
        "title": t.title,
        "description": t.description,
        "status": t.status.value if isinstance(t.status, TopicStatus) else t.status,
        "categories": t.categories,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }


def source_to_dict(s: Source) -> dict:
    return {
        "id": s.id,
        "topic_id": s.topic_id,
        "platform": s.platform.value if isinstance(s.platform, Platform) else s.platform,
        "url": s.url,
        "title": s.title,
        "content": s.content,
        "summary": s.summary,
        "images": s.images,
        "author": s.author,
        "publish_time": s.publish_time,
        "crawl_time": s.crawl_time,
        "confidence": s.confidence,
        "category": s.category,
        "useful": s.useful,
        "crawl_version": s.crawl_version,
    }


def task_to_dict(t: Task) -> dict:
    return {
        "id": t.id,
        "topic_id": t.topic_id,
        "type": t.type.value if isinstance(t.type, TaskType) else t.type,
        "status": t.status.value if isinstance(t.status, TaskStatus) else t.status,
        "progress": t.progress,
        "detail": t.detail,
        "error_msg": t.error_msg,
        "retry_count": t.retry_count,
        "created_at": t.created_at,
    }
