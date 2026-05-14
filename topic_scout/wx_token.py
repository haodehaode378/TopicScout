"""WeChat MP token persistence — simple JSON file, no Redis needed."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional

from .config import config

logger = logging.getLogger(__name__)

LIC_PATH = os.path.join(config.storage.data_dir, "wx.lic")


@dataclass
class WxCredentials:
    token: str = ""
    cookies: list[dict] = field(default_factory=list)
    cookie_str: str = ""
    user_agent: str = ""
    login_time: str = ""
    expiry_time: str = ""


def load_credentials() -> Optional[WxCredentials]:
    """Load credentials from data/wx.lic."""
    if not os.path.exists(LIC_PATH):
        return None
    try:
        with open(LIC_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not data.get("token"):
            return None
        return WxCredentials(**data)
    except Exception as e:
        logger.warning(f"[wx_token] Failed to load credentials: {e}")
        return None


def save_credentials(creds: WxCredentials) -> None:
    """Save credentials to data/wx.lic."""
    os.makedirs(os.path.dirname(LIC_PATH), exist_ok=True)
    with open(LIC_PATH, "w", encoding="utf-8") as f:
        json.dump(asdict(creds), f, ensure_ascii=False, indent=2)
    try:
        os.chmod(LIC_PATH, 0o600)
    except OSError:
        pass  # Windows doesn't support chmod the same way


def clear_credentials() -> None:
    """Delete credentials file."""
    if os.path.exists(LIC_PATH):
        os.remove(LIC_PATH)


def is_logged_in() -> bool:
    """Check if we have valid credentials."""
    creds = load_credentials()
    return creds is not None and bool(creds.token)
