/** TypeScript types matching backend models. */

export type TopicStatus = 'chatting' | 'crawling' | 'summarizing' | 'done' | 'error'

export interface Topic {
  id: string
  keyword: string
  title: string
  description: string
  status: TopicStatus
  categories: string[]
  source_count?: number
  pinned?: boolean
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export type Platform = 'web' | 'bilibili' | 'douyin' | 'weibo' | 'zhihu' | 'xiaohongshu' | 'wechat'

export interface Source {
  id: string
  topic_id: string
  platform: Platform
  url: string
  title: string
  content: string
  summary: string
  images: string[]
  author: string
  publish_time: string
  crawl_time: string
  confidence: number
  category: string
  useful: number
  crawl_version: number
}

export interface CrawlVersion {
  id: number
  version: number
  source_count: number
  status: string
  started_at: string
  finished_at: string
}

export interface Summary {
  id: number
  content: string
  key_insights: string[]
  reliability: string
  crawl_version: number
  created_at: string
}

export type TaskType = 'crawl' | 'summarize' | 'export_pdf' | 'export_json'
export type TaskStatusType = 'pending' | 'running' | 'done' | 'error'

export interface TaskItem {
  id: string
  topic_id: string
  type: TaskType
  status: TaskStatusType
  progress: number
  detail: string
  error_msg: string
  retry_count: number
  created_at: string
}

export interface AppConfig {
  llm: {
    base_url: string
    model_name: string
    temperature: number
    max_tokens: number
    timeout: number
  }
  crawl: {
    max_depth: number
    max_items_per_source: number
    request_interval: number
    request_timeout: number
    max_concurrent: number
    max_retry: number
  }
  storage: {
    data_dir: string
    images_dir: string
    exports_dir: string
    db_path: string
    storage_limit_gb: number
  }
  frontend: {
    port: number
    theme: string
    items_per_page: number
  }
}

// WeChat MP
export interface WxLoginStatus {
  status: 'idle' | 'loading' | 'qr_ready' | 'success' | 'error'
  logged_in: boolean
  error: string
  qr_exists: boolean
}

export interface WxSearchResult {
  fakeid: string
  nickname: string
  alias: string
  round_head_img: string
}

export interface WxAccount {
  id: string
  nickname: string
  alias: string
  avatar_url: string
  subscribed_at: string
  last_crawl_at: string
}
