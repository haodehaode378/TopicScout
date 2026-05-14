"""WeChat MP platform API calls — search accounts, fetch articles, extract content."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Optional

import httpx

from .wx_token import load_credentials

logger = logging.getLogger(__name__)

WX_BASE = "https://mp.weixin.qq.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"


def _headers() -> dict[str, str]:
    creds = load_credentials()
    if not creds:
        raise ValueError("未登录，请先扫码登录微信公众号")
    return {
        "Cookie": creds.cookie_str,
        "User-Agent": creds.user_agent or UA,
        "Referer": f"{WX_BASE}/cgi-bin/home?t=home/index&lang=zh_CN",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }


def _token() -> str:
    creds = load_credentials()
    if not creds or not creds.token:
        raise ValueError("未登录或 token 已过期")
    return creds.token


async def search_biz(keyword: str, limit: int = 10) -> list[dict]:
    """Search for WeChat public accounts by keyword."""
    params = {
        "action": "search_biz",
        "begin": 0,
        "count": limit,
        "query": keyword,
        "token": _token(),
        "lang": "zh_CN",
        "f": "json",
        "ajax": 1,
    }
    url = f"{WX_BASE}/cgi-bin/searchbiz"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params=params, headers=_headers())
        resp.raise_for_status()
        data = resp.json()

    ret = data.get("base_resp", {}).get("ret", -1)
    if ret == 200013:
        logger.warning("[wx_api] search_biz 频率限制")
        return []
    if ret == 200003:
        raise ValueError("token 已过期，请重新扫码登录")
    if ret != 0:
        err = data.get("base_resp", {}).get("err_msg", "unknown")
        logger.error(f"[wx_api] search_biz ret={ret} err={err}")
        return []

    results = []
    for item in data.get("list", []):
        results.append({
            "fakeid": item.get("fakeid", ""),
            "nickname": item.get("nickname", ""),
            "alias": item.get("alias", ""),
            "round_head_img": item.get("round_head_img", ""),
        })
    return results


async def get_article_list(fakeid: str, page: int = 0, count: int = 5) -> list[dict]:
    """Fetch article list for a public account using appmsgpublish endpoint."""
    params = {
        "sub": "list",
        "sub_action": "list_ex",
        "begin": page * count,
        "count": count,
        "fakeid": fakeid,
        "token": _token(),
        "lang": "zh_CN",
        "f": "json",
        "ajax": 1,
    }
    url = f"{WX_BASE}/cgi-bin/appmsgpublish"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params=params, headers=_headers())
        resp.raise_for_status()
        data = resp.json()

    ret = data.get("base_resp", {}).get("ret", -1)
    if ret == 200013:
        logger.warning(f"[wx_api] appmsgpublish 频率限制 fakeid={fakeid}")
        return []
    if ret == 200003:
        raise ValueError("token 已过期，请重新扫码登录")
    if ret != 0:
        err = data.get("base_resp", {}).get("err_msg", "unknown")
        logger.error(f"[wx_api] appmsgpublish ret={ret} err={err}")
        return []

    articles = []
    # publish_page is a JSON string containing publish_list
    publish_page_str = data.get("publish_page", "")
    if publish_page_str:
        try:
            publish_page = json.loads(publish_page_str)
        except json.JSONDecodeError:
            publish_page = {}

        for pl_item in publish_page.get("publish_list", []):
            pub_info_str = pl_item.get("publish_info", "")
            if not pub_info_str:
                continue
            try:
                pub_info = json.loads(pub_info_str)
            except json.JSONDecodeError:
                continue
            for appmsg in pub_info.get("appmsgex", []):
                if appmsg.get("is_deleted"):
                    continue
                ts = appmsg.get("update_time", appmsg.get("create_time", 0))
                articles.append({
                    "aid": appmsg.get("aid", ""),
                    "title": appmsg.get("title", ""),
                    "link": appmsg.get("link", ""),
                    "cover": appmsg.get("cover", ""),
                    "digest": appmsg.get("digest", ""),
                    "update_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(ts)) if ts else "",
                })
    return articles


async def extract_article_content(url: str) -> dict:
    """Extract article content from a WeChat article URL using httpx fallback.
    Returns {title, author, content, cover_url, publish_time}.
    """
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get(url, headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        html = resp.text

    # Basic extraction from meta tags and content div
    title = _extract_meta(html, "og:title") or _extract_meta(html, "twitter:title")
    author = _extract_meta(html, "og:article:author")
    cover_url = _extract_meta(html, "og:image") or _extract_meta(html, "twitter:image")
    description = _extract_meta(html, "og:description")

    # Extract #js_content inner text
    content = _extract_div_content(html, "js_content")

    # Check for error states
    error_signals = ["该内容已被发布者删除", "内容审核中", "该内容暂时无法查看", "违规无法查看"]
    for sig in error_signals:
        if sig in html:
            logger.warning(f"[wx_api] Article error: {sig} url={url}")
            return {"title": title, "author": author, "content": "", "cover_url": cover_url, "description": ""}

    return {
        "title": title,
        "author": author,
        "content": content,
        "cover_url": cover_url,
        "description": description,
    }


def _extract_meta(html: str, name: str) -> str:
    """Extract content from a <meta> tag by property or name."""
    patterns = [
        rf'<meta\s+[^>]*property="{re.escape(name)}"\s+[^>]*content="([^"]*)"',
        rf'<meta\s+[^>]*content="([^"]*)"[^>]*property="{re.escape(name)}"',
        rf'<meta\s+[^>]*name="{re.escape(name)}"\s+[^>]*content="([^"]*)"',
        rf'<meta\s+[^>]*content="([^"]*)"[^>]*name="{re.escape(name)}"',
    ]
    for pattern in patterns:
        m = re.search(pattern, html, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return ""


def _extract_div_content(html: str, div_id: str) -> str:
    """Extract text content from a div by id — finds opening tag, then all content until matching close."""
    # Find the opening div
    open_tag = re.search(rf'<div[^>]*id="{div_id}"[^>]*>', html, re.IGNORECASE)
    if not open_tag:
        return ""
    start = open_tag.end()
    # Collect all text from here by stripping tags
    # Take a reasonable chunk (WeChat articles ~200KB max)
    chunk = html[start:start + 200000]
    # Strip all HTML tags
    text = re.sub(r'<[^>]+>', '', chunk)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text
