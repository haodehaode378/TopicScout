<div align="center">

# TopicScout

**Personal Research Agent — Keyword-driven deep research with AI, structured output**

[![中文](https://img.shields.io/badge/中文-README.md-blue)](README.md)
[![English](https://img.shields.io/badge/English-Current-green)](README_en.md)
[![GitHub Stars](https://img.shields.io/github/stars/haodehaode378/TopicScout?style=social)](https://github.com/haodehaode378/TopicScout/stargazers)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.13+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev/)

</div>

---

## Introduction

TopicScout is a **personal research Agent**. Enter a keyword, and AI refines your research direction through conversation, then deeply crawls multiple sources, generates a structured report with PDF export and JSON reuse.

Core flow:

```
Keyword → AI Refinement Chat → Deep Crawling → AI Summary & Categorization → Notion-style Display → PDF/JSON Export
```

Designed as a data source foundation for video generation projects, also usable standalone for any research topic.

## Features

| Feature | Description |
|---------|-------------|
| AI Conversation | Chat-based refinement with auto-readiness detection, skip and rollback support |
| Multi-source Crawling | Web, Bilibili, Douyin, Weibo, Zhihu, Xiaohongshu |
| Smart Summary | Global summary + key insights + reliability assessment |
| Auto Categorization | AI groups sources into 3-8 categories |
| Notion-style Display | 3-column layout: category filter / source cards / version manager |
| Version Management | Each crawl creates a new version with history switching |
| Real-time Progress | SSE push with animated progress bars |
| Export | PDF (cover + TOC + body) / structured JSON for downstream reuse |
| Dark / Light Theme | CSS variable theming with localStorage persistence |

## Quick Start

### Requirements

- Python 3.13+
- Node.js 18+

### Installation

```bash
git clone https://github.com/haodehaode378/TopicScout.git
cd TopicScout

# Backend
pip install -e .

# Frontend
cd frontend
npm install
cd ..
```

### Configuration

```bash
cp .env.example .env
# Edit .env and add your LLM API key
```

### Run

```bash
# Terminal 1: Backend
python -m topic_scout serve

# Terminal 2: Frontend
cd frontend && npm run dev
```

Open http://localhost:3783 to start using.

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Backend | Python 3.13 + FastAPI | Async crawling, lightweight API |
| Frontend | React 18 + TypeScript + Vite | Notion-style UI |
| Database | SQLite + aiosqlite | Lightweight, no external service |
| LLM | OpenAI-compatible format | MiMo / DeepSeek / Kimi / MiniMax / Tongyi Qianwen |
| Crawler | httpx + regex parsing | General web + Chinese platforms |
| PDF | WeasyPrint | HTML to PDF conversion |
| Animation | Framer Motion | Card expansion, progress bars, page transitions |

## Project Structure

```
topic_scout/
├── __main__.py          # CLI entry
├── config.py            # Dataclass configuration
├── models.py            # Data models
├── llm.py               # LLM adapter
├── chat.py              # AI refinement chat
├── crawler/
│   ├── base.py          # Crawler base class
│   ├── web.py           # General web
│   ├── bilibili.py      # Bilibili
│   ├── douyin.py        # Douyin (TikTok China)
│   ├── weibo.py         # Weibo
│   ├── zhihu.py         # Zhihu
│   └── xiaohongshu.py   # Xiaohongshu (RED)
├── summarizer.py        # AI summary + categorization
├── exporter.py          # JSON / PDF export
├── server.py            # FastAPI server
└── db.py                # SQLite CRUD

frontend/src/
├── App.tsx              # Router + theme toggle
├── components/
│   ├── HomePage.tsx     # Topic list
│   ├── ChatPage.tsx     # AI conversation
│   ├── ResultPage.tsx   # Notion-style results
│   ├── SourceCard.tsx   # Source cards
│   ├── TasksPage.tsx    # Task list
│   ├── ConfigPage.tsx   # Configuration panel
│   └── ...
└── lib/
    ├── api.ts           # API client
    └── types.ts         # TypeScript types
```

## API Endpoints

<details>
<summary>Click to expand full API list</summary>

### Topics
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/topics` | Create topic |
| GET | `/api/topics` | List topics |
| GET | `/api/topics/:id` | Get topic |
| DELETE | `/api/topics/:id` | Delete topic |

### AI Chat
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/topics/:id/chat` | Send message |
| GET | `/api/topics/:id/chat` | Chat history |
| POST | `/api/topics/:id/confirm` | Confirm topic |

### Crawling
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/topics/:id/crawl` | Trigger crawl |
| GET | `/api/topics/:id/crawl/status` | Crawl progress (SSE) |
| GET | `/api/topics/:id/sources` | Get sources |
| PATCH | `/api/topics/:id/sources/:src_id` | Update source |

### Summary & Export
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/topics/:id/summarize` | Trigger summary |
| GET | `/api/topics/:id/summary` | Get summary |
| GET | `/api/topics/:id/export/json` | Export JSON |
| POST | `/api/topics/:id/export/pdf` | Export PDF |

### Tasks & Config
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/tasks` | List tasks |
| POST | `/api/tasks/:id/retry` | Retry task |
| GET | `/api/config` | Get config |
| PUT | `/api/config` | Update config |

</details>

## LLM Configuration

Supports any OpenAI-compatible API, configurable from the frontend:

| Provider | base_url |
|----------|----------|
| Xiaomi MiMo | Check official docs |
| DeepSeek | `https://api.deepseek.com/v1` |
| Kimi (Moonshot) | `https://api.moonshot.cn/v1` |
| Tongyi Qianwen | `https://dashscope.aliyuncs.com/compatible-mode/v1` |

## Testing

```bash
# Backend tests
python -m pytest tests/ -v

# Frontend type check
cd frontend && npx tsc --noEmit

# Frontend build
cd frontend && npx vite build
```

## Reference Projects

| Project | Stars | Reference Point |
|---------|-------|-----------------|
| [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) | 49k+ | Chinese platform crawling architecture |
| [gpt-researcher](https://github.com/assafelovic/gpt-researcher) | 27k+ | Planner + execution agent pattern |
| [crawl4ai](https://github.com/unclecode/crawl4ai) | 65k+ | LLM-friendly web crawling |

## Contributing

Issues and Pull Requests are welcome.

## License

[MIT](LICENSE)
