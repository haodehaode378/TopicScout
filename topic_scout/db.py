"""SQLite database — raw SQL, no ORM."""

from __future__ import annotations

import json
import os
from typing import Optional

import aiosqlite

from .config import config
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
    WxAccount,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS topics (
    id TEXT PRIMARY KEY,
    keyword TEXT NOT NULL,
    title TEXT DEFAULT '',
    description TEXT DEFAULT '',
    status TEXT DEFAULT 'chatting',
    categories TEXT DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id TEXT NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    topic_id TEXT NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    platform TEXT DEFAULT 'web',
    url TEXT DEFAULT '',
    title TEXT DEFAULT '',
    content TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    images TEXT DEFAULT '[]',
    author TEXT DEFAULT '',
    publish_time TEXT DEFAULT '',
    crawl_time TEXT DEFAULT '',
    confidence REAL DEFAULT 0.0,
    category TEXT DEFAULT '',
    useful INTEGER DEFAULT -1,
    crawl_version INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS crawl_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id TEXT NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    source_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'running',
    started_at TEXT NOT NULL,
    finished_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    topic_id TEXT NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    detail TEXT DEFAULT '',
    error_msg TEXT DEFAULT '',
    retry_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id TEXT NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    crawl_version INTEGER NOT NULL,
    content TEXT DEFAULT '',
    key_insights TEXT DEFAULT '[]',
    reliability TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS wx_accounts (
    id TEXT PRIMARY KEY,
    nickname TEXT DEFAULT '',
    alias TEXT DEFAULT '',
    avatar_url TEXT DEFAULT '',
    subscribed_at TEXT NOT NULL,
    last_crawl_at TEXT DEFAULT '',
    status TEXT DEFAULT 'active'
);
"""


async def get_db() -> aiosqlite.Connection:
    db_path = config.storage.db_path
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await db.executescript(SCHEMA)
    return db


# --- Topics ---

async def create_topic(topic: Topic) -> Topic:
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO topics (id, keyword, title, description, status, categories, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (topic.id, topic.keyword, topic.title, topic.description, topic.status.value, json.dumps(topic.categories, ensure_ascii=False), topic.created_at, topic.updated_at),
        )
        await db.commit()
        return topic
    finally:
        await db.close()


async def get_topic(topic_id: str) -> Optional[Topic]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM topics WHERE id = ?", (topic_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return Topic(
            id=row[0], keyword=row[1], title=row[2], description=row[3],
            status=TopicStatus(row[4]), categories=json.loads(row[5]),
            created_at=row[6], updated_at=row[7],
        )
    finally:
        await db.close()


async def list_topics() -> list[Topic]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM topics ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [
            Topic(
                id=r[0], keyword=r[1], title=r[2], description=r[3],
                status=TopicStatus(r[4]), categories=json.loads(r[5]),
                created_at=r[6], updated_at=r[7],
            )
            for r in rows
        ]
    finally:
        await db.close()


async def update_topic(topic_id: str, **kwargs: object) -> None:
    from datetime import datetime
    kwargs["updated_at"] = datetime.now().isoformat()
    if "categories" in kwargs:
        kwargs["categories"] = json.dumps(kwargs["categories"], ensure_ascii=False)
    if "status" in kwargs and isinstance(kwargs["status"], TopicStatus):
        kwargs["status"] = kwargs["status"].value
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values())
    vals.append(topic_id)
    db = await get_db()
    try:
        await db.execute(f"UPDATE topics SET {sets} WHERE id = ?", vals)
        await db.commit()
    finally:
        await db.close()


async def delete_topic(topic_id: str) -> None:
    db = await get_db()
    try:
        # Cascade delete — order matters due to FK constraints
        for table in ["summaries", "tasks", "crawl_versions", "sources", "chat_messages"]:
            await db.execute(f"DELETE FROM {table} WHERE topic_id = ?", (topic_id,))
        await db.execute("DELETE FROM topics WHERE id = ?", (topic_id,))
        await db.commit()
    finally:
        await db.close()


# --- Chat messages ---

async def add_chat_message(msg: ChatMessage) -> ChatMessage:
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO chat_messages (topic_id, role, content, created_at) VALUES (?, ?, ?, ?) RETURNING id",
            (msg.topic_id, msg.role, msg.content, msg.created_at),
        )
        row = await cursor.fetchone()
        msg.id = row[0]
        await db.commit()
        return msg
    finally:
        await db.close()


async def get_chat_messages(topic_id: str) -> list[ChatMessage]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, topic_id, role, content, created_at FROM chat_messages WHERE topic_id = ? ORDER BY id",
            (topic_id,),
        )
        rows = await cursor.fetchall()
        return [ChatMessage(id=r[0], topic_id=r[1], role=r[2], content=r[3], created_at=r[4]) for r in rows]
    finally:
        await db.close()


async def delete_chat_after(topic_id: str, message_id: int) -> None:
    db = await get_db()
    try:
        await db.execute("DELETE FROM chat_messages WHERE topic_id = ? AND id > ?", (topic_id, message_id))
        await db.commit()
    finally:
        await db.close()


# --- Sources ---

async def add_source(source: Source) -> Source:
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO sources (id, topic_id, platform, url, title, content, summary, images, author, publish_time, crawl_time, confidence, category, useful, crawl_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (source.id, source.topic_id, source.platform.value, source.url, source.title, source.content,
             source.summary, json.dumps(source.images, ensure_ascii=False), source.author, source.publish_time,
             source.crawl_time, source.confidence, source.category, source.useful, source.crawl_version),
        )
        await db.commit()
        return source
    finally:
        await db.close()


async def get_sources(topic_id: str, version: Optional[int] = None) -> list[Source]:
    db = await get_db()
    try:
        if version is not None:
            cursor = await db.execute("SELECT * FROM sources WHERE topic_id = ? AND crawl_version = ?", (topic_id, version))
        else:
            cursor = await db.execute("SELECT * FROM sources WHERE topic_id = ?", (topic_id,))
        rows = await cursor.fetchall()
        return [
            Source(
                id=r[0], topic_id=r[1], platform=Platform(r[2]), url=r[3], title=r[4],
                content=r[5], summary=r[6], images=json.loads(r[7]), author=r[8],
                publish_time=r[9], crawl_time=r[10], confidence=r[11], category=r[12],
                useful=r[13], crawl_version=r[14],
            )
            for r in rows
        ]
    finally:
        await db.close()


async def update_source(source_id: str, **kwargs: object) -> None:
    if "images" in kwargs:
        kwargs["images"] = json.dumps(kwargs["images"], ensure_ascii=False)
    if "platform" in kwargs and isinstance(kwargs["platform"], Platform):
        kwargs["platform"] = kwargs["platform"].value
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values())
    vals.append(source_id)
    db = await get_db()
    try:
        await db.execute(f"UPDATE sources SET {sets} WHERE id = ?", vals)
        await db.commit()
    finally:
        await db.close()


async def source_exists(topic_id: str, url: str) -> bool:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT 1 FROM sources WHERE topic_id = ? AND url = ?", (topic_id, url))
        return await cursor.fetchone() is not None
    finally:
        await db.close()


async def count_sources(topic_id: str) -> int:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT COUNT(*) FROM sources WHERE topic_id = ?", (topic_id,))
        row = await cursor.fetchone()
        return row[0]
    finally:
        await db.close()


# --- Crawl versions ---

async def create_crawl_version(cv: CrawlVersion) -> CrawlVersion:
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO crawl_versions (topic_id, version, source_count, status, started_at, finished_at) VALUES (?, ?, ?, ?, ?, ?) RETURNING id",
            (cv.topic_id, cv.version, cv.source_count, cv.status, cv.started_at, cv.finished_at),
        )
        row = await cursor.fetchone()
        cv.id = row[0]
        await db.commit()
        return cv
    finally:
        await db.close()


async def get_crawl_versions(topic_id: str) -> list[CrawlVersion]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM crawl_versions WHERE topic_id = ? ORDER BY version DESC", (topic_id,))
        rows = await cursor.fetchall()
        return [CrawlVersion(id=r[0], topic_id=r[1], version=r[2], source_count=r[3], status=r[4], started_at=r[5], finished_at=r[6]) for r in rows]
    finally:
        await db.close()


async def update_crawl_version(cv_id: int, **kwargs: object) -> None:
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values())
    vals.append(cv_id)
    db = await get_db()
    try:
        await db.execute(f"UPDATE crawl_versions SET {sets} WHERE id = ?", vals)
        await db.commit()
    finally:
        await db.close()


async def get_next_crawl_version(topic_id: str) -> int:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT COALESCE(MAX(version), 0) FROM crawl_versions WHERE topic_id = ?", (topic_id,))
        row = await cursor.fetchone()
        return row[0] + 1
    finally:
        await db.close()


# --- Tasks ---

async def create_task(task: Task) -> Task:
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO tasks (id, topic_id, type, status, progress, detail, error_msg, retry_count, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (task.id, task.topic_id, task.type.value, task.status.value, task.progress, task.detail, task.error_msg, task.retry_count, task.created_at),
        )
        await db.commit()
        return task
    finally:
        await db.close()


async def get_task(task_id: str) -> Optional[Task]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return Task(
            id=row[0], topic_id=row[1], type=TaskType(row[2]), status=TaskStatus(row[3]),
            progress=row[4], detail=row[5], error_msg=row[6], retry_count=row[7], created_at=row[8],
        )
    finally:
        await db.close()


async def list_tasks(topic_id: Optional[str] = None, status: Optional[str] = None) -> list[Task]:
    db = await get_db()
    try:
        query = "SELECT * FROM tasks WHERE 1=1"
        params: list = []
        if topic_id:
            query += " AND topic_id = ?"
            params.append(topic_id)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [
            Task(
                id=r[0], topic_id=r[1], type=TaskType(r[2]), status=TaskStatus(r[3]),
                progress=r[4], detail=r[5], error_msg=r[6], retry_count=r[7], created_at=r[8],
            )
            for r in rows
        ]
    finally:
        await db.close()


async def update_task(task_id: str, **kwargs: object) -> None:
    if "type" in kwargs and isinstance(kwargs["type"], TaskType):
        kwargs["type"] = kwargs["type"].value
    if "status" in kwargs and isinstance(kwargs["status"], TaskStatus):
        kwargs["status"] = kwargs["status"].value
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values())
    vals.append(task_id)
    db = await get_db()
    try:
        await db.execute(f"UPDATE tasks SET {sets} WHERE id = ?", vals)
        await db.commit()
    finally:
        await db.close()


# --- Summaries ---

async def save_summary(summary: Summary) -> Summary:
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO summaries (topic_id, crawl_version, content, key_insights, reliability, created_at) VALUES (?, ?, ?, ?, ?, ?) RETURNING id",
            (summary.topic_id, summary.crawl_version, summary.content, json.dumps(summary.key_insights, ensure_ascii=False), summary.reliability, summary.created_at),
        )
        row = await cursor.fetchone()
        summary.id = row[0]
        await db.commit()
        return summary
    finally:
        await db.close()


async def get_summary(topic_id: str, version: Optional[int] = None) -> Optional[Summary]:
    db = await get_db()
    try:
        if version is not None:
            cursor = await db.execute("SELECT * FROM summaries WHERE topic_id = ? AND crawl_version = ?", (topic_id, version))
        else:
            cursor = await db.execute("SELECT * FROM summaries WHERE topic_id = ? ORDER BY crawl_version DESC, id DESC LIMIT 1", (topic_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return Summary(
            id=row[0], topic_id=row[1], crawl_version=row[2], content=row[3],
            key_insights=json.loads(row[4]), reliability=row[5], created_at=row[6],
        )
    finally:
        await db.close()


# --- WeChat Accounts ---

async def add_wx_account(acct: WxAccount) -> WxAccount:
    db = await get_db()
    try:
        await db.execute(
            "INSERT OR REPLACE INTO wx_accounts (id, nickname, alias, avatar_url, subscribed_at, last_crawl_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (acct.id, acct.nickname, acct.alias, acct.avatar_url, acct.subscribed_at, acct.last_crawl_at, acct.status),
        )
        await db.commit()
        return acct
    finally:
        await db.close()


async def list_wx_accounts() -> list[WxAccount]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM wx_accounts WHERE status = 'active' ORDER BY subscribed_at DESC")
        rows = await cursor.fetchall()
        return [
            WxAccount(id=r[0], nickname=r[1], alias=r[2], avatar_url=r[3],
                      subscribed_at=r[4], last_crawl_at=r[5], status=r[6])
            for r in rows
        ]
    finally:
        await db.close()


async def get_wx_account(fakeid: str) -> Optional[WxAccount]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM wx_accounts WHERE id = ?", (fakeid,))
        row = await cursor.fetchone()
        if not row:
            return None
        return WxAccount(id=row[0], nickname=row[1], alias=row[2], avatar_url=row[3],
                         subscribed_at=row[4], last_crawl_at=row[5], status=row[6])
    finally:
        await db.close()


async def delete_wx_account(fakeid: str) -> None:
    db = await get_db()
    try:
        await db.execute("DELETE FROM wx_accounts WHERE id = ?", (fakeid,))
        await db.commit()
    finally:
        await db.close()


async def update_wx_account(fakeid: str, **kwargs: object) -> None:
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values())
    vals.append(fakeid)
    db = await get_db()
    try:
        await db.execute(f"UPDATE wx_accounts SET {sets} WHERE id = ?", vals)
        await db.commit()
    finally:
        await db.close()
