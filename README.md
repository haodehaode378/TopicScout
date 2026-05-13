<div align="center">

# TopicScout

**个人研究 Agent — 输入关键词，AI 驱动深度调研，结构化输出**

[![中文](https://img.shields.io/badge/中文-当前文档-blue)](README.md)
[![English](https://img.shields.io/badge/English-README_en.md-green)](README_en.md)
[![GitHub Stars](https://img.shields.io/github/stars/haodehaode378/TopicScout?style=social)](https://github.com/haodehaode378/TopicScout/stargazers)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.13+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev/)

</div>

---

## 简介

TopicScout 是一个**个人研究 Agent**。输入一个关键词，AI 通过对话帮你明确研究方向，然后深度爬取多源信息，生成结构化报告，支持 PDF 导出和 JSON 复用。

核心流程：

```
关键词 → AI 追问细化 → 深度爬取 → AI 总结归类 → Notion 式展示 → PDF/JSON 导出
```

作为视频生成项目的前置数据源，也可独立用于任何主题的信息调研。

## 功能特性

| 功能 | 说明 |
|------|------|
| AI 对话 | 聊天式追问，自动判断何时理解清楚，支持跳过和回退 |
| 多源爬取 | 通用网页、B站、抖音、微博、知乎、小红书 |
| 智能总结 | 全局总结 + 关键洞察 + 信息可靠度评估 |
| 自动归类 | AI 自动将来源归入 3-8 个类别 |
| Notion 式展示 | 三栏布局：分类筛选 / 来源卡片 / 版本管理 |
| 版本管理 | 每次爬取生成新版本，可切换查看历史版本 |
| 实时进度 | SSE 推送爬取进度，进度条实时更新 |
| 导出 | PDF（封面+目录+正文）/ JSON 结构化复用 |
| 深色/浅色 | CSS 变量主题切换，localStorage 持久化 |

## 快速开始

### 环境要求

- Python 3.13+
- Node.js 18+

### 安装

```bash
git clone https://github.com/haodehaode378/TopicScout.git
cd TopicScout

# 后端
pip install -e .

# 前端
cd frontend
npm install
cd ..
```

### 配置

```bash
cp .env.example .env
# 编辑 .env，填入 LLM API Key
```

### 启动

```bash
# 终端 1：后端
python -m topic_scout serve

# 终端 2：前端
cd frontend && npm run dev
```

打开 http://localhost:3783 即可使用。

## 技术栈

| 层次 | 技术 | 说明 |
|------|------|------|
| 后端 | Python 3.13 + FastAPI | 异步爬虫、轻量 API |
| 前端 | React 18 + TypeScript + Vite | Notion 风格 UI |
| 数据库 | SQLite + aiosqlite | 轻量存储，无需额外服务 |
| LLM | OpenAI 兼容格式 | 支持 MiMo / DeepSeek / Kimi / MiniMax / 通义千问 |
| 爬虫 | httpx + 正则解析 | 通用网页 + 国内平台 |
| PDF | WeasyPrint | HTML 直转 PDF |
| 动画 | Framer Motion | 卡片展开、进度条、入场动画 |

## 项目结构

```
topic_scout/
├── __main__.py          # CLI 入口
├── config.py            # Dataclass 配置
├── models.py            # 数据模型
├── llm.py               # LLM 适配器
├── chat.py              # AI 追问对话
├── crawler/
│   ├── base.py          # 爬虫基类
│   ├── web.py           # 通用网页
│   ├── bilibili.py      # B站
│   ├── douyin.py        # 抖音
│   ├── weibo.py         # 微博
│   ├── zhihu.py         # 知乎
│   └── xiaohongshu.py   # 小红书
├── summarizer.py        # AI 总结 + 归类
├── exporter.py          # JSON / PDF 导出
├── server.py            # FastAPI 服务
└── db.py                # SQLite CRUD

frontend/src/
├── App.tsx              # 路由 + 主题切换
├── components/
│   ├── HomePage.tsx     # 主题列表
│   ├── ChatPage.tsx     # AI 对话
│   ├── ResultPage.tsx   # Notion 式结果页
│   ├── SourceCard.tsx   # 来源卡片
│   ├── TasksPage.tsx    # 任务列表
│   ├── ConfigPage.tsx   # 配置面板
│   └── ...
└── lib/
    ├── api.ts           # API 客户端
    └── types.ts         # TypeScript 类型
```

## API 端点

<details>
<summary>点击展开完整 API 列表</summary>

### 主题
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/topics` | 创建主题 |
| GET | `/api/topics` | 主题列表 |
| GET | `/api/topics/:id` | 主题详情 |
| DELETE | `/api/topics/:id` | 删除主题 |

### AI 对话
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/topics/:id/chat` | 发送消息 |
| GET | `/api/topics/:id/chat` | 对话历史 |
| POST | `/api/topics/:id/confirm` | 确认主题 |

### 爬取
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/topics/:id/crawl` | 触发爬取 |
| GET | `/api/topics/:id/crawl/status` | 爬取进度 (SSE) |
| GET | `/api/topics/:id/sources` | 爬取结果 |
| PATCH | `/api/topics/:id/sources/:src_id` | 编辑来源 |

### 总结 & 导出
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/topics/:id/summarize` | 触发总结 |
| GET | `/api/topics/:id/summary` | 获取总结 |
| GET | `/api/topics/:id/export/json` | 导出 JSON |
| POST | `/api/topics/:id/export/pdf` | 导出 PDF |

### 任务 & 配置
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/tasks` | 任务列表 |
| POST | `/api/tasks/:id/retry` | 重试任务 |
| GET | `/api/config` | 获取配置 |
| PUT | `/api/config` | 更新配置 |

</details>

## LLM 配置

支持 OpenAI 兼容格式，前端可配：

| 服务商 | base_url |
|--------|----------|
| 小米 MiMo | 查官方文档 |
| DeepSeek | `https://api.deepseek.com/v1` |
| Kimi | `https://api.moonshot.cn/v1` |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |

## 测试

```bash
# 后端测试
python -m pytest tests/ -v

# 前端类型检查
cd frontend && npx tsc --noEmit

# 前端构建
cd frontend && npx vite build
```

## 参考项目

| 项目 | Stars | 参考点 |
|------|-------|--------|
| [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) | 49k+ | 国内平台爬虫架构 |
| [gpt-researcher](https://github.com/assafelovic/gpt-researcher) | 27k+ | planner+execution 架构 |
| [crawl4ai](https://github.com/unclecode/crawl4ai) | 65k+ | LLM 友好的网页爬取 |

## 贡献

欢迎提交 Issue 和 Pull Request。

## License

[MIT](LICENSE)
