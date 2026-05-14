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

## Screenshots

### Home — Topic List

Browse all research topics with search, status filtering, and one-click delete.

![Home](docs/screenshots/home.png)

### AI Chat — Refinement

Chat-based interaction where AI asks follow-up questions until it understands your research direction. Supports skip and rollback.

![AI Chat](docs/screenshots/chat.png)

### Results — Notion-style Display

Three-column layout: category filter on the left, source cards in the center, version management on the right. Inline editing, useful marking, and image preview.

![Results](docs/screenshots/result.png)

### Tasks — Background Progress

Real-time progress bars with SSE push notifications for crawl status at a glance.

![Tasks](docs/screenshots/tasks.png)

### Config — LLM + Crawling + WeChat

Provider card selection, crawling parameter tuning, and WeChat public account QR login.

![Config](docs/screenshots/config.png)

## Features

| Feature | Description |
|---------|-------------|
| AI Conversation | Chat-based refinement with auto-readiness detection, skip and rollback support |
| Multi-source Crawling | Web, Bilibili, Douyin, Weibo, Zhihu, Xiaohongshu, WeChat MP |
| Smart Summary | Global summary + key insights + reliability assessment |
| Auto Categorization | AI groups sources into 3-8 categories |
| Notion-style Display | 3-column layout: category filter / source cards / version manager |
| Version Management | Each crawl creates a new version with history switching |
| Real-time Progress | SSE push with animated progress bars |
| Export | PDF (cover + TOC + body) / structured JSON for downstream reuse |
| WeChat MP | QR login → keyword-based search → auto crawl articles |
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
playwright install chromium

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
| LLM | OpenAI-compatible format | DeepSeek / Kimi / MiniMax / Tongyi Qianwen / MiMo |
| Crawler | httpx + Playwright | General web + Chinese platforms + WeChat MP |
| PDF | WeasyPrint | HTML to PDF conversion |
| Animation | Framer Motion | Card expansion, progress bars, page transitions |

## WeChat Public Account Integration

TopicScout has built-in WeChat MP crawling:

1. **QR Login**: Click "Login WeChat MP" in config, scan QR with your phone
2. **Keyword Search**: When creating a topic, AI automatically searches relevant public accounts based on keywords
3. **Auto Crawl**: Fetches latest articles from found accounts, fully automatic like web/Bilibili platforms

Technical approach: Playwright headless browser for login → token + cookies → httpx MP platform API calls.

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
| [we-mp-rss](https://github.com/rachelos/we-mp-rss) | — | WeChat MP crawling reference |

## Contributing

Issues and Pull Requests are welcome.

## License

[MIT](LICENSE)
