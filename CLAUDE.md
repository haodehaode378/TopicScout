# CLAUDE.md — TopicScout

## 项目

TopicScout：个人研究 Agent。
输入关键词 → AI 追问细化 → 深度爬取多源信息 → Notion 式前端展示 + 编辑 → PDF 导出 + JSON 复用。

作为视频生成项目的前置数据源。

## 代码风格：Karpathy Style

参考 github.com/karpathy（nanoGPT、micrograd、llm.c），核心原则：

1. **单文件优先**：能放一个文件就不要拆成五个。模块拆分的唯一理由是"这个文件真的太大了"
2. **可读性 > 一切**：代码首先是写给人看的，其次才是给机器执行的
3. **教育性注释**：解释 WHY，不解释 WHAT。变量名不自明时加行内注释
4. **最少依赖**：只引入真正需要的库，不用就不装
5. **直接写，不要过度抽象**：不要为了"可能的未来需求"提前搞框架套框架
6. **dataclass 做配置**：用 `@dataclass` 定义配置类，不要搞 YAML/JSON 配置解析器
7. **数学式命名**：在算法密集处可用 B/T/C（batch/time/channel）等简洁命名
8. **自包含**：每个文件应该能独立理解，不需要跳转 5 个文件才能看懂一个函数

### 好的写法（✅）

```python
# 模板评分：商品类别与模板风格的匹配度（0-1）
score = compute_match_score(product.category, template.family)

class TemplateConfig:
    """一个模板家族的完整配置，包含 3 个视觉变体。"""
    family: str
    colors: list[str]
    variants: int = 3
```

### 避免的写法（❌）

```python
# 过度抽象：为了一个评分函数建一个 Strategy Pattern
class TemplateMatchStrategy(ABC):
    @abstractmethod
    def compute(self, product: Product, template: Template) -> float: ...

# 过度注释：解释显而易见的事情
score = value  # 将 value 赋值给 score
```

## 技术栈

| 层次 | 技术 | 说明 |
|------|------|------|
| 后端 | Python 3.13.7 + FastAPI | 异步爬虫、轻量、Karpathy 风格 |
| 前端 | React 18 + TypeScript + Vite | 端口 3783 |
| 爬虫 | Crawl4AI + MediaCrawler 参考 | 通用网页 + 国内平台 |
| LLM | OpenAI 兼容格式 | 默认 MiMo，可切换 DeepSeek/Kimi/MiniMax/通义千问 |
| PDF | WeasyPrint | HTML 直接转 PDF |
| 存储 | SQLite + JSON 导出 + 本地图片 | 个人工具，简单够用 |
| UI 组件 | Radix Primitives | Notion 风格，无样式、可访问性强 |
| 设计资源 | design-resources-for-developers | 配色/图标/字体参考 |

## 常用命令

```bash
# 安装
pip install -e .
cd frontend && npm install

# 启动（前后端）
python -m topic_scout serve
# 前端另开终端
cd frontend && npm run dev

# 类型检查
mypy src/
cd frontend && npm run typecheck

# 测试
python -m pytest tests/
```

## 项目结构

```
topic_scout/
├── __init__.py
├── __main__.py          # CLI 入口：serve / crawl / export
├── config.py            # 所有配置（dataclass）
├── models.py            # 数据模型：Topic, CrawlResult, Source, Task
├── llm.py               # LLM 适配器（OpenAI 兼容格式，支持 MiMo/DeepSeek/Kimi/MiniMax/通义）
├── chat.py              # AI 追问对话逻辑（判断何时理解清楚）
├── crawler/
│   ├── __init__.py
│   ├── web.py           # 通用网页爬取（基于 Crawl4AI）
│   ├── bilibili.py      # B站（参考 bilibili-API-collect）
│   ├── douyin.py        # 抖音（参考 MediaCrawler）
│   ├── weibo.py         # 微博（参考 MediaCrawler）
│   ├── zhihu.py         # 知乎
│   ├── xiaohongshu.py   # 小红书（参考 MediaCrawler）
│   └── base.py          # 爬虫基类（统一接口）
├── summarizer.py        # AI 全局总结 + 归类
├── exporter.py          # JSON / PDF 导出
├── server.py            # FastAPI HTTP API
├── db.py                # SQLite 操作（版本管理、任务状态）
└── utils.py             # 工具函数（只有确实被多处使用的才放这里）
frontend/
├── index.html
├── package.json
├── src/
│   ├── App.tsx          # 主应用
│   ├── main.tsx
│   ├── components/
│   │   ├── ChatPanel.tsx        # AI 追问对话面板
│   │   ├── TaskList.tsx         # 多任务列表（进度实时更新）
│   │   ├── ResultEditor.tsx     # Notion 式结果编辑器（富文本）
│   │   ├── SourceCard.tsx       # 来源卡片（含图片预览）
│   │   └── ConfigPanel.tsx      # 前端配置（LLM/爬取/存储）
│   └── lib/
│       ├── api.ts               # 后端 API 调用
│       └── types.ts             # TypeScript 类型
tests/
├── test_crawler.py
├── test_llm.py
├── test_summarizer.py
└── test_exporter.py
```

## 核心流程

```
关键词输入
  → AI 追问（聊天式，自动判断何时理解清楚）
  → 确认主题
  → 并发爬取（网页/B站/抖音/微博/知乎/小红书）
  → AI 全局总结 + 自动归类
  → 结构化 JSON 存储
  → 前端 Notion 式展示 + 编辑
  → PDF 导出
  → JSON 文件供下游项目复用
```

## 参考项目（GitHub）

| 项目 | ⭐ Stars | 说明 | 值得参考的点 |
|------|---------|------|-------------|
| NanmiCoder/MediaCrawler | 49,501 | 国内平台爬虫：小红书/抖音/快手/B站/微博/百度贴吧/知乎 | **核心参考**，多平台爬取架构、签名处理、Cookie 管理、反爬策略 |
| khoj-ai/khoj | 34,524 | AI 第二大脑，自托管，Python | 知识管理、深度研究、自托管方案 |
| assafelovic/gpt-researcher | 27,015 | 自主深度研究 Agent，Python | planner+execution 架构、并发爬取、研究报告生成 |
| virattt/dexter | 25,495 | 金融领域深度研究，TypeScript | 垂直领域研究 Agent 设计 |
| dzhng/deep-research | 18,893 | 迭代式深度研究，<500行，TypeScript | 极简实现、depth/breadth 参数、迭代深入 |
| unclecode/crawl4ai | 65,446 | LLM 友好的通用爬虫 | 网页内容提取、异步爬取、LLM 集成模式 |

### TopicScout 的差异化
- 国内平台爬取（B站/抖音/微博/知乎/小红书）
- Notion 式前端 + 富文本编辑
- 多任务并行 + 版本管理
- JSON 导出复用给下游项目
- 中文优先

## 爬取源参考

| 平台 | 参考仓库 | ⭐ Stars |
|------|---------|---------|
| 通用网页 | unclecode/crawl4ai | 65,446 |
| 多平台 | NanmiCoder/MediaCrawler | 49,501 |
| B站 API | SocialSisterYi/bilibili-API-collect | 20,321 |
| 抖音 | JoeanAmier/TikTokDownloader | 14,394 |
| B站下载 | nilaoda/BBDown | 13,866 |
| B站异步 | HFrost0/bilix | 1,778 |

## LLM 配置

支持 OpenAI 兼容格式，前端可配 base_url + api_key + model_name：

| 服务商 | base_url |
|--------|----------|
| 小米 MiMo（默认） | 查官方文档 |
| DeepSeek | https://api.deepseek.com/v1 |
| Kimi（月之暗面） | https://api.moonshot.cn/v1 |
| MiniMax | https://api.minimax.chat/v1 |
| 通义千问 | https://dashscope.aliyuncs.com/compatible-mode/v1 |

## 爬取配置（前端可配）

| 配置项 | 默认值 |
|--------|--------|
| 最大递归深度 | 5 层 |
| 每源最大条数 | 200 条 |
| 请求间隔 | 2 秒 |
| 超时时间 | 30 秒 |

## 存储

| 类型 | 路径 |
|------|------|
| 图片 | ./data/images/ |
| JSON 导出 | ./data/exports/ |
| 数据库 | ./data/research.db |
| 存储上限 | 2GB（超限前端提醒） |

## API 端点

### 主题

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/topics` | 创建主题（输入关键词，返回 topic_id） |
| GET | `/api/topics` | 主题列表 |
| GET | `/api/topics/:id` | 主题详情 |
| DELETE | `/api/topics/:id` | 删除主题（级联删除所有关联数据） |

### AI 对话

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/topics/:id/chat` | 发送消息给 AI（追问/回答） |
| GET | `/api/topics/:id/chat` | 获取对话历史 |
| POST | `/api/topics/:id/confirm` | 确认主题，开始爬取 |

### 爬取

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/topics/:id/crawl` | 触发爬取（可指定平台） |
| GET | `/api/topics/:id/crawl/status` | 爬取进度（SSE 实时推送） |
| GET | `/api/topics/:id/sources` | 获取爬取结果列表（支持分页、筛选） |
| PATCH | `/api/topics/:id/sources/:src_id` | 编辑来源（修改内容/标记有用） |
| GET | `/api/topics/:id/versions` | 获取爬取版本列表 |
| GET | `/api/topics/:id/versions/:ver` | 获取某次版本的来源 |

### 总结

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/topics/:id/summarize` | 触发 AI 全局总结 |
| GET | `/api/topics/:id/summary` | 获取总结结果 |

### 导出

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/topics/:id/export/json` | 导出 JSON 文件 |
| GET | `/api/topics/:id/export/pdf` | 导出 PDF 文件 |

### 任务

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/tasks` | 任务列表（支持筛选状态） |
| GET | `/api/tasks/:id` | 任务详情（进度、错误信息） |

### 配置

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/config` | 获取当前配置 |
| PUT | `/api/config` | 更新配置（LLM/爬取/存储） |

> 技术要点：爬取进度用 SSE（Server-Sent Events）实时推送，不用 WebSocket。所有 POST 立即返回任务 ID。

## 前端页面设计

### 1. 首页（/）— 主题列表
- 顶部：大搜索框（输入关键词开始新研究）
- 列表：已有主题卡片（标题、缩略图封面、状态标签、来源数量、创建时间）
- 排序：按创建时间倒序
- 状态标签：对话中 / 爬取中 / 已完成 / 出错
- 支持置顶/收藏
- 操作：查看、删除、重新爬取

### 2. 对话页（/topics/:id/chat）— AI 追问
- 左侧：聊天界面（类 ChatGPT，用户消息 + AI 消息）
- 右侧：实时预览（AI 提取的主题标题、描述、确认按钮）
- 支持中断对话（直接跳过剩余追问，确认主题）
- 支持编辑 AI 回复（标题不满意可直接改）
- 支持回退到某一轮重新聊
- 底部：输入框 + 发送按钮
- 确认按钮：点击后进入爬取流程

### 3. 结果页（/topics/:id）— Notion 式展示（核心页面）

整体三栏布局：

```
┌─────────────────────────────────────────────────────────────┐
│  ← 返回    主题标题    [导出JSON] [导出PDF] [重新爬取]        │
├──────────┬──────────────────────────────┬───────────────────┤
│  分类    │   主内容区                   │  版本切换栏       │
│  筛选栏  │                              │                   │
│          │  📊 全局总结 + 关键洞察       │  v3 最新          │
│ □ 全部(87)│                              │  v2 (56条)        │
│ □ 商业(12)│  🔍 搜索框 + 排序筛选       │  v1 (31条)        │
│ □ 开源(23)│                              │                   │
│ □ 学术(18)│  来源卡片列表...            │                   │
│ □ 其他(34)│                              │                   │
├──────────┴──────────────────────────────┴───────────────────┤
│  共 87 条 · 已标记 12 条有用 · 生成于 2026-05-13            │
└─────────────────────────────────────────────────────────────┘
```

来源卡片（默认收起）：
- 左上角：平台图标（🎬B站、🎵抖音、📱微博、📖知乎、📕小红书、🌐网页）
- 右上角：置信度数字（≥0.8 绿色、0.5-0.8 黄色、<0.5 红色）
- 标题加粗，摘要灰色最多2行省略
- 底部：作者 · 时间 · 有用标记

来源卡片（展开后）：
- 图片预览区（点击放大，lightbox 左右切换）
- AI 总结（可直接点击编辑，contenteditable）
- 全文内容（Markdown 渲染：标题、列表、代码块、链接）
- 所有字段可编辑：标题、摘要、分类、置信度、有用标记
- 原始链接、作者、爬取版本

全局总结区域：
- 总结正文（可编辑）
- 关键洞察列表
- 信息可靠度评估
- 打字机效果逐字显示

导出 PDF：
- 用户可选择范围：全局总结 / 分类目录 / 全部来源或仅“有用” / 全文或仅摘要
- 封面页（主题标题 + 日期 + 来源统计）
- 目录页（自动生成）
- 正文：全局总结 → 分类 → 各来源详情
- 页码 + 页眉

### 4. 任务页（/tasks）— 后台任务
- 任务列表表格：主题名、任务类型、状态、进度条、详情、时间
- 状态：等待中 / 运行中 / 已完成 / 出错
- 进度条实时更新（SSE 推送）
- 出错时显示错误信息 + 重试次数（已重试 2/3 次）
- 重试按钮
- 爬取完成后 Toast 通知（不自动跳转）

### 5. 配置页（/config）— 前端配置
- LLM 配置区：base_url、api_key、model_name 输入框
- 爬取配置区：递归深度、最大条数、请求间隔、超时 滑块/输入框
- 存储配置区：图片路径、导出路径、数据库路径、存储上限
- 保存即时生效（不需要重启）
- 测试连接按钮（只测 LLM API 通不通）

### 组件清单

| 组件 | 文件 | 功能 |
|------|------|------|
| ChatPanel | ChatPanel.tsx | AI 追问对话界面 |
| TaskList | TaskList.tsx | 多任务列表 + 进度条 |
| ResultEditor | ResultEditor.tsx | Notion 式富文本编辑器 |
| SourceCard | SourceCard.tsx | 来源卡片（含图片、置信度、平台图标） |
| ConfigPanel | ConfigPanel.tsx | 配置表单 |
| CategorySidebar | CategorySidebar.tsx | 左侧分类筛选栏 |
| VersionSidebar | VersionSidebar.tsx | 右侧版本切换栏 |
| SearchBar | SearchBar.tsx | 关键词搜索框 |
| ProgressBar | ProgressBar.tsx | 进度条组件 |
| RichTextEditor | RichTextEditor.tsx | 富文本编辑器（加粗/标题/列表） |
| Toast | Toast.tsx | 页面内通知弹窗 |
| Lightbox | Lightbox.tsx | 图片放大预览 |

### 动画设计（Motion 库）

| 交互 | 动画效果 |
|------|----------|
| 页面进入 | 三栏依次从左滑入（stagger 100ms） |
| 卡片出现 | 从下方淡入 + 上移（fade up） |
| 卡片展开/收起 | 高度平滑过渡 + 内容淡入 |
| 置信度数字 | 从 0 跑到目标值（count up） |
| 版本切换 | 卡片列表淡出 → 新列表淡入 |
| 分类筛选 | 卡片淡出/淡入 + 重新排列 |
| 搜索过滤 | 不匹配卡片缩小+淡出 |
| 有用标记 | 点击时心形弹跳效果 |
| 进度条 | 平滑增长 + 光泽流动 |
| 全局总结 | 打字机效果（逐字显示） |
| 错误状态 | 轻微抖动（shake） |
| 导出按钮 | 点击后弹出下载动画 |

动画原则：
- duration 200-400ms，不要太慢
- 使用 spring 物理动画（不是 linear/ease）
- 卡片展开用 layoutId 做共享布局动画
- 入场动画只在首次加载时播放，切换 tab 不重复

### 通知方式

用前端 Toast 通知（页面内弹窗，不用浏览器通知）：
- 爬取完成：✅ “xxx调研已完成，共 87 条来源”
- 爬取出错：❌ “爬取失败：B站请求超时，已重试 2/3 次”
- 导出完成：📥 “JSON 已导出到 ./data/exports/topic_001_v3.json”
- Toast 自动 5 秒消失，可手动关闭

### 前端技术要点
- 状态管理：React Context + useReducer（不上 Redux）
- 实时更新：SSE（EventSource API）监听爬取进度
- 富文本编辑：基于 Radix Primitives + Tiptap 或 Slate
- 图片预览：Lightbox 效果，支持左右切换
- 深色/浅色：CSS 变量 + localStorage 持久化
- 路由：React Router v6
- 只做桌面端，不适配手机

## 并发模型

使用 asyncio + httpx（不用线程池）：

```
TaskManager（单例）
├── task_001 → asyncio.Task (爬取)
├── task_002 → asyncio.Task (爬取)
└── task_003 → asyncio.Task (总结)

每个爬取任务内部：
asyncio.gather(
    crawl_web(url1),      # 并发
    crawl_bilibili(bv),   # 并发
    crawl_douyin(url),    # 并发
)
```

限速策略：
- 全局信号量：最多同时 10 个请求
- 每平台信号量：每个平台最多 5 个并发
- 请求间隔：2 秒（可配），用 asyncio.sleep
- 遇到 429/503：指数退避重试（1s → 2s → 4s → 放弃）

## 错误处理策略

### 爬取错误

| 错误类型 | 处理方式 |
|----------|----------|
| 网络超时 | 重试 3 次，间隔指数退避（1s/2s/4s） |
| 429 限流 | 等待 Retry-After 头部指定时间，或 60 秒 |
| 403/401 | 跳过该 URL，记录错误，继续爬其他 |
| 5xx 服务端错误 | 重试 2 次，间隔 5 秒 |
| 页面解析失败 | 跳过，记录 warning，不阻塞整体流程 |
| 某平台全部失败 | 标记该平台 error，其他平台继续跑 |
| 所有平台全失败 | 任务标记 error，通知前端 |

### LLM 错误

| 错误类型 | 处理方式 |
|----------|----------|
| API 超时 | 重试 2 次，间隔 3 秒 |
| API 返回空 | 用默认值兜底（总结="暂无总结"，归类="其他"） |
| Rate limit | 等 30 秒后重试 |
| API Key 无效 | 任务标记 error，前端 Toast 提示检查配置 |

## 配置 dataclass

```python
@dataclass
class LLMConfig:
    base_url: str = "https://api.moonshot.cn/v1"
    api_key: str = ""  # 从环境变量读取
    model_name: str = "mimo"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 60

@dataclass
class CrawlConfig:
    max_depth: int = 5
    max_items_per_source: int = 200
    request_interval: float = 2.0
    request_timeout: int = 30
    max_concurrent: int = 10
    max_retry: int = 3
    retry_backoff: float = 2.0

@dataclass
class StorageConfig:
    data_dir: str = "./data"
    images_dir: str = "./data/images"
    exports_dir: str = "./data/exports"
    db_path: str = "./data/research.db"
    storage_limit_gb: float = 2.0

@dataclass
class FrontendConfig:
    port: int = 3783
    theme: str = "light"
    items_per_page: int = 20

@dataclass
class AppConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    crawl: CrawlConfig = field(default_factory=CrawlConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    frontend: FrontendConfig = field(default_factory=FrontendConfig)
```

配置来源优先级：前端配置页 > 环境变量 > 默认值

## 文件命名规范

```
data/
├── images/
│   └── {topic_id}/                  # 按主题分目录
│       ├── src_001_hero.jpg
│       └── src_002_cover.jpg
├── exports/
│   ├── {topic_id}_v{version}.json   # topic_20260513_001_v1.json
│   ├── {topic_id}_v{version}.pdf
│   └── {topic_id}_latest.json       # 最新版本软链接
└── research.db                      # SQLite 数据库
```

## LLM 提示词设计

### 追问逻辑（chat.py）

System Prompt：
```
你是一个研究助理。用户给你一个关键词，你需要通过对话帮他明确研究主题。

你的任务：
1. 理解用户想研究什么
2. 通过提问缩小范围、明确方向
3. 判断什么时候你已经足够理解主题

提问规则：
- 每次只问 1-2 个问题，不要一次问太多
- 问题要具体，不要问“你想研究什么方向”这种太宽泛的
- 优先问：时间范围、地域范围、关注角度、深度要求
- 语气自然，像聊天不像问卷

判断何时理解清楚的信号：
- 你能用一句话准确描述这个主题的研究范围
- 你清楚知道要爬哪些类型的内容
- 你不会再问出有价值的新问题

当你认为已经理解清楚时，在回复末尾加上特殊标记：
[READY] 主题标题 | 一句话描述
```

判断逻辑：检测 assistant 回复中是否包含 [READY] 标记。有 → 提取标题和描述，进入确认流程。没有 → 继续对话。

### 全局总结（summarizer.py）

System Prompt：
```
你是一个信息分析专家。给你一批爬取到的资料，请生成一份结构化的研究报告。

要求：
1. 总结要全面但不啰嗦，控制在 500-1000 字
2. 关键洞察要尖锐，不要说废话（3-5 条）
3. 指出信息之间的矛盾或争议
4. 标注信息的可靠程度

输出格式（严格遵守）：
---SUMMARY---
（总结正文）
---INSIGHTS---
- 洞察1
- 洞察2
- 洞察3
---RELIABILITY---
（对整体信息可靠性的评估，一句话）
```

### 自动归类（summarizer.py）

System Prompt：
```
你是一个信息分类专家。给你一批资料，请按主题自动归类。

规则：
1. 类别名称用中文，简短（2-6 个字）
2. 每条资料只归入一个主类别
3. 类别数量控制在 3-8 个
4. 如果某条资料确实不属于任何类别，归入“其他”

输出格式（每行一个）：
类别名: 来源ID1, 来源ID2, 来源ID3
类别名: 来源ID4, 来源ID5
```

### 单条总结（爬取时即时生成）

System Prompt：`用 1-2 句话总结以下内容的核心信息。不要废话，直接说重点。`

设计要点：
- 所有 prompt 都用中文（爬取内容以中文为主）
- 总结和归类分开两次 LLM 调用（职责清晰，出错好排查）
- 单条总结在爬取时即时做，不等全部爬完（并行友好）
- 追问逻辑用 [READY] 标记做状态机，比让 LLM 返回 JSON 更稳定

## JSON 输出格式（供下游项目复用）

```json
{
  "meta": {
    "topic_id": "topic_20260513_001",
    "keyword": "AI 视频生成",
    "title": "2026年AI视频生成技术全景调研",
    "description": "覆盖主流模型、开源方案、商业产品...",
    "categories": ["AI视频", "生成式AI", "多模态"],
    "crawl_versions": [1, 2],
    "created_at": "2026-05-13T10:00:00Z",
    "exported_at": "2026-05-13T12:30:00Z",
    "total_sources": 87
  },
  "summary": {
    "content": "AI视频生成领域在2025-2026年经历了爆发式增长...",
    "key_insights": [
      "Sora 仍是最强商业方案，但开源追赶迅速",
      "CogVideoX 是目前最可用的开源替代",
      "短视频场景（<60s）已基本成熟，长视频仍是难题"
    ]
  },
  "categories": [
    {"name": "商业产品", "sources": ["src_001", "src_005"]},
    {"name": "开源模型", "sources": ["src_003", "src_008"]}
  ],
  "sources": [
    {
      "id": "src_001",
      "platform": "web",
      "url": "https://example.com/ai-video-2026",
      "title": "AI视频生成技术年度报告",
      "content": "（正文全文...）",
      "summary": "总结了2026年主流AI视频生成方案的对比...",
      "images": ["./data/images/topic_001/src_001_hero.jpg"],
      "author": "张三",
      "publish_time": "2026-05-01T08:00:00Z",
      "crawl_time": "2026-05-13T10:05:00Z",
      "confidence": 0.92,
      "category": "商业产品",
      "useful": 1,
      "crawl_version": 1
    }
  ]
}
```

设计要点：
- meta — 主题元信息，下游项目快速了解数据来源
- summary — AI 全局总结 + 关键洞察，可直接用于生成脚本大纲
- categories — AI 自动归类，每个类别引用 source ID
- sources — 完整来源数据，包含全文、图片路径、置信度
- useful 字段：1=有用、0=无用、-1=未标记
- images 存相对路径，下游项目可直接读取本地文件

## 数据库表结构（SQLite）

### topics — 研究主题

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PK | 主题ID，如 `topic_20260513_001` |
| keyword | TEXT | 用户输入的原始关键词 |
| title | TEXT | AI 追问后确认的主题标题 |
| description | TEXT | AI 生成的主题描述 |
| status | TEXT | `chatting` / `crawling` / `summarizing` / `done` / `error` |
| categories | TEXT | AI 自动归类结果（JSON 数组） |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 最后更新时间 |

### chat_messages — AI 追问对话

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 |
| topic_id | TEXT FK | 关联主题 |
| role | TEXT | `user` / `assistant` |
| content | TEXT | 消息内容 |
| created_at | DATETIME | 时间 |

### sources — 爬取来源

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PK | 来源ID，如 `src_001` |
| topic_id | TEXT FK | 关联主题 |
| platform | TEXT | `web` / `bilibili` / `douyin` / `weibo` / `zhihu` / `xiaohongshu` |
| url | TEXT | 原始URL |
| title | TEXT | 标题 |
| content | TEXT | 正文全文 |
| summary | TEXT | AI 单条总结 |
| images | TEXT | 图片路径列表（JSON 数组） |
| author | TEXT | 作者 |
| publish_time | DATETIME | 原文发布时间 |
| crawl_time | DATETIME | 爬取时间 |
| confidence | REAL | AI 置信度评分 0-1 |
| category | TEXT | AI 归类标签 |
| useful | INTEGER | 用户标记（1有用/0无用/-1未标记） |
| crawl_version | INTEGER | 第几次爬取（版本管理） |

### crawl_versions — 爬取版本

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 |
| topic_id | TEXT FK | 关联主题 |
| version | INTEGER | 版本号（1, 2, 3...） |
| source_count | TEXT | 本版爬取条数 |
| status | TEXT | `running` / `done` / `error` |
| started_at | DATETIME | 开始时间 |
| finished_at | DATETIME | 完成时间 |

### tasks — 后台任务

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PK | 任务ID |
| topic_id | TEXT FK | 关联主题 |
| type | TEXT | `crawl` / `summarize` / `export_pdf` / `export_json` |
| status | TEXT | `pending` / `running` / `done` / `error` |
| progress | INTEGER | 进度百分比 0-100 |
| detail | TEXT | 当前进度描述（如"正在爬取网页 3/10"） |
| error_msg | TEXT | 错误信息 |
| created_at | DATETIME | 创建时间 |

### summaries — AI 全局总结

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 |
| topic_id | TEXT FK | 关联主题 |
| crawl_version | INTEGER | 对应哪次爬取 |
| content | TEXT | 全局总结内容 |
| key_insights | TEXT | 关键洞察（JSON 数组） |
| created_at | DATETIME | 时间 |

### ER 关系

```
topics 1──N chat_messages
topics 1──N sources
topics 1──N crawl_versions
topics 1──N tasks
topics 1──N summaries
```

## 环境变量清单

```env
# LLM
LLM_BASE_URL=https://api.moonshot.cn/v1
LLM_API_KEY=sk-xxx
LLM_MODEL_NAME=mimo
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4096
LLM_TIMEOUT=60

# 爬取
CRAWL_MAX_DEPTH=5
CRAWL_MAX_ITEMS=200
CRAWL_INTERVAL=2.0
CRAWL_TIMEOUT=30
CRAWL_MAX_CONCURRENT=10
CRAWL_MAX_RETRY=3

# 存储
DATA_DIR=./data
DB_PATH=./data/research.db
STORAGE_LIMIT_GB=2.0

# 服务
SERVER_PORT=8000
FRONTEND_PORT=3783
```

## 边界情况清单

### 爬取

| 情况 | 处理 |
|------|------|
| 爬取结果为空（搜索无结果） | 记录 warning，不报错，前端显示“未找到相关内容” |
| 爬取到重复 URL | 去重，同一 URL 只存一条，保留最新版本 |
| 页面内容为空（404/被删） | 跳过，记录 warning |
| 页面内容全是广告/垃圾 | LLM 判断 confidence < 0.3 则标记为低质量，不删除 |
| 图片下载失败 | 保留 URL 引用，images 字段为空数组，不阻塞 |
| 视频平台需要登录 | 跳过该平台，前端提示“需要配置 Cookie” |
| 爬取过程中用户删除主题 | 取消所有 asyncio.Task，清理临时文件 |
| 同一主题并发触发多次爬取 | 拒绝第二次，返回“已有爬取任务在进行中” |

### LLM

| 情况 | 处理 |
|------|------|
| LLM 返回格式不符合预期（如没有 [READY] 标记） | 继续对话，不报错，3 轮后仍无标记则自动确认 |
| LLM 返回空字符串 | 用默认值兜底（总结=“暂无总结”，归类=“其他”） |
| LLM 返回超长内容（>5000字） | 截断到 5000 字，记录 warning |
| 追问超过 10 轮仍未 READY | 自动确认，用已有信息构建主题描述 |
| 归类结果类别数 > 10 | 合并为“其他”，只保留前 9 个 + 其他 |
| 归类结果某类别只有 1 条来源 | 合并到最相近的类别或“其他” |

### 前端

| 情况 | 处理 |
|------|------|
| 页面加载时后端未启动 | 显示“服务未启动，请运行 python -m topic_scout serve” |
| SSE 连接断开 | 自动重连（3 次间隔 1s/2s/4s），失败后显示“连接已断开，刷新页面” |
| 图片加载失败 | 显示占位图（灰色方块 + 图标） |
| 导出时主题无数据 | 禁用导出按钮，tooltip 提示“无数据可导出” |
| 配置保存后 LLM 测试失败 | Toast 提示“API 连接失败，请检查配置”，不回滚配置 |

## 验收标准

### v0.1 MVP 验收标准

#### 后端 — 主题管理

| # | 验收项 | 测试方法 | 通过标准 |
|---|--------|---------|----------|
| B1 | 创建主题 | POST /api/topics {"keyword": "AI视频生成"} | 201，含 topic_id，status=chatting |
| B2 | 主题列表 | GET /api/topics | 返回数组，按 created_at 倒序 |
| B3 | 主题详情 | GET /api/topics/:id | 完整信息含 keyword/title/description/status/categories |
| B4 | 删除主题 | DELETE /api/topics/:id | 200，级联删除 chat/sources/tasks/summaries |

#### 后端 — AI 对话

| # | 验收项 | 测试方法 | 通过标准 |
|---|--------|---------|----------|
| B5 | 发送消息 | POST /api/topics/:id/chat | AI 回复包含追问问题 |
| B6 | 对话历史 | GET /api/topics/:id/chat | role=user/assistant 交替，时间正确 |
| B7 | READY 检测 | 连续对话直到 AI 含 [READY] | 自动提取标题和描述 |
| B8 | 确认主题 | POST /api/topics/:id/confirm | status chatting→crawling |
| B9 | 超10轮无READY | 连续10轮无 [READY] | 第11轮自动确认 |

#### 后端 — 爬取

| # | 验收项 | 测试方法 | 通过标准 |
|---|--------|---------|----------|
| B10 | 触发爬取 | POST /api/topics/:id/crawl | 202，任务创建 |
| B11 | 通用网页 | 爬取3个真实URL | sources 新增3条，content 有正文 |
| B12 | B站爬取 | 爬取1个B站视频 | platform=bilibili，title/content 正确 |
| B13 | SSE 推送 | GET crawl/status | 每完成URL推送一条 event，含 progress/detail |
| B14 | 重复去重 | 爬取2次相同URL | sources 只1条，crawl_version 递增 |
| B15 | 空结果 | 搜索无结果的关键词 | 不报错，显示"未找到相关内容" |
| B16 | 超时处理 | 30秒无响应URL | 重试3次后跳过，不阻塞其他URL |
| B17 | 并发任务 | 同时触发2个主题爬取 | 两个都能完成，互不干扰 |
| B18 | 图片下载 | 爬取含图片网页 | images目录有文件，sources.images有路径 |

#### 后端 — AI 总结与归类

| # | 验收项 | 测试方法 | 通过标准 |
|---|--------|---------|----------|
| B19 | 全局总结 | POST /api/topics/:id/summarize | content 500-1000字 |
| B20 | 关键洞察 | 同上 | key_insights 3-5条，不重复 |
| B21 | 自动归类 | 同上 | sources.category 更新，3-8个类别 |
| B22 | 单条总结 | 爬取完查看 source.summary | 每条都有，1-2句话 |
| B23 | LLM失败 | 模拟API不可用 | 总结="暂无"，归类="其他" |

#### 后端 — 导出

| # | 验收项 | 测试方法 | 通过标准 |
|---|--------|---------|----------|
| B24 | JSON导出 | GET /api/topics/:id/export/json | 结构符合本文件定义的格式 |
| B25 | JSON可用 | 另一个脚本读取JSON | 能正常解析所有字段 |

#### 后端 — 任务管理

| # | 验收项 | 测试方法 | 通过标准 |
|---|--------|---------|----------|
| B26 | 任务列表 | GET /api/tasks | 含 status/progress/detail |
| B27 | 任务详情 | GET /api/tasks/:id | 完整信息 |
| B28 | 重试计数 | 爬取失败后查看 | error_msg 含重试次数 |

#### 后端 — 配置

| # | 验收项 | 测试方法 | 通过标准 |
|---|--------|---------|----------|
| B29 | 获取配置 | GET /api/config | 返回当前配置 |
| B30 | 更新配置 | PUT /api/config | 下次调用用新模型 |
| B31 | 即时生效 | 更新间隔后爬取 | 使用新值 |
| B32 | 环境变量 | .env 设 LLM_MODEL_NAME | 启动后默认为此值 |

#### 前端 — 首页

| # | 验收项 | 测试方法 | 通过标准 |
|---|--------|---------|----------|
| F1 | 列表展示 | 创建3个主题 | 3张卡片，含标题/状态/缩略图/来源数 |
| F2 | 搜索输入 | 输入"AI"回车 | 跳转对话页 |
| F3 | 进入主题 | 点击卡片 | 跳转正确 |
| F4 | 删除主题 | 点击删除 | 确认框→卡片消失 |
| F5 | 置顶收藏 | 点击置顶 | 排在最前 |
| F6 | 状态颜色 | 不同状态 | 对话中=蓝 爬取中=橙 已完成=绿 出错=红 |

#### 前端 — 对话页

| # | 验收项 | 测试方法 | 通过标准 |
|---|--------|---------|----------|
| F7 | 消息收发 | 输入发送 | 用户右/AI左 |
| F8 | 中断对话 | 点击确认主题 | 跳过追问，进入爬取 |
| F9 | 编辑回复 | 点击AI标题 | 可编辑，保存后更新 |
| F10 | 回退对话 | 点击第1轮 | 后续折叠 |
| F11 | 右侧预览 | 对话中 | 实时显示标题描述 |
| F12 | 确认按钮 | AI含[READY] | 按钮高亮可点击 |

#### 前端 — 结果页

| # | 验收项 | 测试方法 | 通过标准 |
|---|--------|---------|----------|
| F13 | 三栏布局 | 打开已完成主题 | 左分类+中内容+右版本 |
| F14 | 全局总结 | 查看顶部 | 总结+洞察+可靠度 |
| F15 | 来源卡片 | 查看内容区 | 平台图标/标题/摘要/置信度 |
| F16 | 卡片展开 | 点击卡片 | 图片+AI总结+全文(Markdown) |
| F17 | 置信度色 | 不同值 | ≥0.8绿 0.5-0.8黄 <0.5红 |
| F18 | 分类筛选 | 点击左侧类别 | 只显示该类别 |
| F19 | 搜索过滤 | 输入关键词 | 实时过滤 |
| F20 | 版本切换 | 点击v1 | 显示该版本来源 |
| F21 | 编辑来源 | 改标题保存 | 刷新后为新值 |
| F22 | 标记有用 | 点击有用按钮 | 图标变化+计数更新 |
| F23 | 导出JSON | 点击按钮 | 浏览器下载 |
| F24 | 图片放大 | 点击图片 | Lightbox+左右切换 |
| F25 | 展开动画 | 展开/收起 | 高度平滑无跳变 |
| F26 | 入场动画 | 首次加载 | 三栏滑入+卡片淡入 |

#### 前端 — 任务页

| # | 验收项 | 测试方法 | 通过标准 |
|---|--------|---------|----------|
| F27 | 任务列表 | 触发2个任务 | 2行，含进度条和状态 |
| F28 | 进度更新 | 观察进行中 | 进度条实时增长 |
| F29 | 出错显示 | 失败后查看 | 错误信息+重试次数 |
| F30 | 重试按钮 | 点击重试 | 任务重新开始 |

#### 前端 — 配置页

| # | 验收项 | 测试方法 | 通过标准 |
|---|--------|---------|----------|
| F31 | 配置表单 | 打开配置页 | 3个配置区 |
| F32 | 测试连接 | 点击按钮 | 通=绿 不通=红 |
| F33 | 保存配置 | 改端口保存 | Toast+即时生效 |

#### 前端 — 全局

| # | 验收项 | 测试方法 | 通过标准 |
|---|--------|---------|----------|
| F34 | 深色主题 | 切换深色 | 颜色正确无白闪 |
| F35 | 浅色主题 | 切换浅色 | 颜色正确 |
| F36 | Toast通知 | 爬取完成 | 右上角弹出，5秒消失 |
| F37 | 后端未启动 | 关后端刷新 | 友好提示不白屏 |

**总计：后端 B1-B32 + 前端 F1-F37 = 69 项**

### v0.2（国内平台）
- [ ] 抖音爬取正常
- [ ] 微博爬取正常
- [ ] 知乎爬取正常
- [ ] 小红书爬取正常

### v0.3（导出增强）
- [ ] PDF 导出格式正确，包含封面/目录/正文
- [ ] PDF 支持选择导出范围

## 设计约束

1. **后端是核心**：所有业务逻辑在 Python 后端，前端只负责展示和编辑
2. **文件即状态**：任务状态存 SQLite，素材存本地文件系统
3. **LLM 统一接口**：所有 AI 调用通过一个适配器，切换模型只改配置
4. **渐进增强**：先跑通核心链路（通用网页爬取 + 总结 + 展示），再加国内平台
5. **JSON 是一等公民**：所有爬取结果最终都导出为结构化 JSON，供下游项目复用

## 开发规范

- Python 3.13.7，用 type hints
- 前端 TypeScript strict mode
- 不用 ORM，直接写 SQL（SQLite 够用）
- Git 提交：`feat: 新增xxx`、`fix: 修复xxx`、`refactor: 重构xxx`、`docs: 更新xxx`、`chore: xxx`
- 测试：核心逻辑必须有测试，UI 可以没有
