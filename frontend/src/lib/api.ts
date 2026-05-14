/** Backend API client. */

import type { Topic, ChatMessage, Source, CrawlVersion, Summary, TaskItem, AppConfig, WxLoginStatus, WxSearchResult, WxAccount } from './types'

const BASE = '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

// Topics
export const createTopic = (keyword: string) =>
  request<{ topic: Topic; ai_reply: string; title: string | null; description: string | null; is_ready: boolean }>('/topics', {
    method: 'POST',
    body: JSON.stringify({ keyword }),
  })

export const listTopics = () => request<Topic[]>('/topics')

export const getTopic = (id: string) => request<Topic>(`/topics/${id}`)

export const deleteTopic = (id: string) =>
  request<{ ok: boolean }>(`/topics/${id}`, { method: 'DELETE' })

// Chat
export const sendChat = (topicId: string, content: string) =>
  request<{ reply: string; title: string | null; description: string | null; is_ready: boolean; auto_confirmed: boolean }>(
    `/topics/${topicId}/chat`,
    { method: 'POST', body: JSON.stringify({ content }) }
  )

export const getChatHistory = (topicId: string) =>
  request<ChatMessage[]>(`/topics/${topicId}/chat`)

export const rollbackChat = (topicId: string, messageId: number) =>
  request<{ ok: boolean }>(`/topics/${topicId}/chat/${messageId}/rollback`, { method: 'POST' })

export const confirmTopic = (topicId: string, title?: string, description?: string) =>
  request<{ ok: boolean; title: string; description: string }>(`/topics/${topicId}/confirm`, {
    method: 'POST',
    body: JSON.stringify({ title, description }),
  })

// Crawl
export const triggerCrawl = (topicId: string, urls: string[], platforms: string[] = ['web', 'bilibili']) =>
  request<{ task_id: string; version: number }>(`/topics/${topicId}/crawl`, {
    method: 'POST',
    body: JSON.stringify({ urls, platforms }),
  })

export const getCrawlSources = (
  topicId: string,
  opts?: { version?: number; page?: number; per_page?: number; category?: string; search?: string }
) => {
  const params = new URLSearchParams()
  if (opts?.version !== undefined) params.set('version', String(opts.version))
  if (opts?.page) params.set('page', String(opts.page))
  if (opts?.per_page) params.set('per_page', String(opts.per_page))
  if (opts?.category) params.set('category', opts.category)
  if (opts?.search) params.set('search', opts.search)
  const qs = params.toString()
  return request<{ sources: Source[]; total: number; page: number; per_page: number }>(
    `/topics/${topicId}/sources${qs ? `?${qs}` : ''}`
  )
}

export const updateSource = (topicId: string, sourceId: string, updates: Partial<Source>) =>
  request<{ ok: boolean }>(`/topics/${topicId}/sources/${sourceId}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  })

export const getVersions = (topicId: string) =>
  request<CrawlVersion[]>(`/topics/${topicId}/versions`)

// Summarize
export const triggerSummarize = (topicId: string) =>
  request<{ task_id: string }>(`/topics/${topicId}/summarize`, { method: 'POST' })

export const getSummary = (topicId: string, version?: number) => {
  const qs = version !== undefined ? `?version=${version}` : ''
  return request<Summary | null>(`/topics/${topicId}/summary${qs}`)
}

// Export
export const exportJsonUrl = (topicId: string) => `${BASE}/topics/${topicId}/export/json`

export const exportPdf = (topicId: string, opts?: { include_summary?: boolean; useful_only?: boolean; full_content?: boolean }) =>
  fetch(`${BASE}/topics/${topicId}/export/pdf`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      include_summary: opts?.include_summary ?? true,
      include_categories: true,
      useful_only: opts?.useful_only ?? false,
      full_content: opts?.full_content ?? true,
    }),
  }).then(r => {
    if (!r.ok) throw new Error(`PDF export failed: ${r.statusText}`)
    return r.blob()
  })

// Tasks
export const listTasks = (opts?: { topic_id?: string; status?: string }) => {
  const params = new URLSearchParams()
  if (opts?.topic_id) params.set('topic_id', opts.topic_id)
  if (opts?.status) params.set('status', opts.status)
  const qs = params.toString()
  return request<TaskItem[]>(`/tasks${qs ? `?${qs}` : ''}`)
}

export const getTask = (taskId: string) => request<TaskItem>(`/tasks/${taskId}`)

export const retryTask = (taskId: string) =>
  request<{ ok: boolean }>(`/tasks/${taskId}/retry`, { method: 'POST' })

// Config
export const getConfig = () => request<AppConfig>('/config')

export const updateConfig = (config: Partial<AppConfig>) =>
  request<{ ok: boolean }>('/config', {
    method: 'PUT',
    body: JSON.stringify(config),
  })

export const testConnection = () =>
  request<{ success: boolean; message: string }>('/config/test', { method: 'POST' })

// SSE helper
export function createCrawlSSE(topicId: string, onMessage: (data: unknown) => void): EventSource {
  const es = new EventSource(`${BASE}/topics/${topicId}/crawl/status`)
  es.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      onMessage(data)
    } catch {
      // ignore parse errors
    }
  }
  es.onerror = () => {
    // Auto-close on error — caller should handle reconnection
    es.close()
  }
  return es
}

// WeChat MP
export const wxLogin = () => request<{ status: string; qr_url?: string }>('/wx/login', { method: 'POST' })

export const wxLoginStatus = () => request<WxLoginStatus>('/wx/status')

export const wxLogout = () => request<{ ok: boolean }>('/wx/logout', { method: 'POST' })

export const wxSearch = (keyword: string, limit = 10) =>
  request<{ accounts: WxSearchResult[] }>('/wx/search', {
    method: 'POST',
    body: JSON.stringify({ keyword, limit }),
  })

export const wxSubscribe = (account: { fakeid: string; nickname?: string; alias?: string; avatar_url?: string }) =>
  request<{ ok: boolean }>('/wx/subscribe', {
    method: 'POST',
    body: JSON.stringify(account),
  })

export const wxAccounts = () => request<WxAccount[]>('/wx/accounts')

export const wxUnsubscribe = (fakeid: string) =>
  request<{ ok: boolean }>(`/wx/accounts/${fakeid}`, { method: 'DELETE' })
