"""All configuration via dataclasses — no YAML/JSON parser needed."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _env(key: str, default: str) -> str:
    return os.getenv(key, default)


def _env_int(key: str, default: int) -> int:
    return int(os.getenv(key, str(default)))


def _env_float(key: str, default: float) -> float:
    return float(os.getenv(key, str(default)))


@dataclass
class LLMConfig:
    base_url: str = field(default_factory=lambda: _env("LLM_BASE_URL", "https://api.moonshot.cn/v1"))
    api_key: str = field(default_factory=lambda: _env("LLM_API_KEY", ""))
    model_name: str = field(default_factory=lambda: _env("LLM_MODEL_NAME", "mimo"))
    temperature: float = field(default_factory=lambda: _env_float("LLM_TEMPERATURE", 0.7))
    max_tokens: int = field(default_factory=lambda: _env_int("LLM_MAX_TOKENS", 4096))
    timeout: int = field(default_factory=lambda: _env_int("LLM_TIMEOUT", 60))


@dataclass
class CrawlConfig:
    max_depth: int = field(default_factory=lambda: _env_int("CRAWL_MAX_DEPTH", 5))
    max_items_per_source: int = field(default_factory=lambda: _env_int("CRAWL_MAX_ITEMS", 200))
    request_interval: float = field(default_factory=lambda: _env_float("CRAWL_INTERVAL", 2.0))
    request_timeout: int = field(default_factory=lambda: _env_int("CRAWL_TIMEOUT", 30))
    max_concurrent: int = field(default_factory=lambda: _env_int("CRAWL_MAX_CONCURRENT", 10))
    max_retry: int = field(default_factory=lambda: _env_int("CRAWL_MAX_RETRY", 3))
    retry_backoff: float = 2.0


@dataclass
class StorageConfig:
    data_dir: str = field(default_factory=lambda: _env("DATA_DIR", "./data"))
    images_dir: str = ""
    exports_dir: str = ""
    db_path: str = field(default_factory=lambda: _env("DB_PATH", "./data/research.db"))
    storage_limit_gb: float = field(default_factory=lambda: _env_float("STORAGE_LIMIT_GB", 2.0))

    def __post_init__(self) -> None:
        if not self.images_dir:
            self.images_dir = os.path.join(self.data_dir, "images")
        if not self.exports_dir:
            self.exports_dir = os.path.join(self.data_dir, "exports")


@dataclass
class FrontendConfig:
    port: int = field(default_factory=lambda: _env_int("FRONTEND_PORT", 3783))
    theme: str = "light"
    items_per_page: int = 20


@dataclass
class AppConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    crawl: CrawlConfig = field(default_factory=CrawlConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    frontend: FrontendConfig = field(default_factory=FrontendConfig)


# Global config singleton — updated at runtime via PUT /api/config
config = AppConfig()
