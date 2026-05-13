/** Result page — Notion-style display with categories, sources, versions. */

import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  getTopic, getCrawlSources, getSummary, getVersions,
  triggerCrawl, triggerSummarize, exportJsonUrl, exportPdf, updateSource, createCrawlSSE,
} from '../lib/api'
import type { Topic, Source, Summary, CrawlVersion } from '../lib/types'
import { useToast } from './Toast'
import SourceCard from './SourceCard'

export default function ResultPage() {
  const { id } = useParams<{ id: string }>()
  const { toast } = useToast()

  const [topic, setTopic] = useState<Topic | null>(null)
  const [sources, setSources] = useState<Source[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [versions, setVersions] = useState<CrawlVersion[]>([])
  const [selectedVersion, setSelectedVersion] = useState<number | undefined>()
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    const loadData = async () => {
      try {
        const [t, s, sum, v] = await Promise.all([
          getTopic(id),
          getCrawlSources(id),
          getSummary(id),
          getVersions(id),
        ])
        setTopic(t)
        setSources(s.sources)
        setSummary(sum)
        setVersions(v)
      } catch (err) {
        toast(err instanceof Error ? err.message : '加载失败', 'error')
      } finally {
        setLoading(false)
      }
    }
    loadData()

    // SSE for live updates if still crawling
    const es = createCrawlSSE(id, (data: unknown) => {
      const d = data as { type: string; source?: Source }
      if (d.type === 'source' && d.source) {
        setSources(prev => {
          if (prev.find(s => s.id === d.source!.id)) return prev
          return [...prev, d.source!]
        })
      }
      if (d.type === 'done') {
        toast('爬取完成', 'success')
        getTopic(id).then(setTopic)
      }
    })
    return () => es.close()
  }, [id])

  useEffect(() => {
    if (!id) return
    getCrawlSources(id, { version: selectedVersion, category: selectedCategory || undefined, search: search || undefined })
      .then(r => setSources(r.sources))
      .catch(console.error)
  }, [id, selectedVersion, selectedCategory, search])

  const handleReCrawl = async () => {
    if (!id) return
    try {
      const result = await triggerCrawl(id, [])
      toast(`已触发重新爬取 (v${result.version})`, 'success')
    } catch (err) {
      toast(err instanceof Error ? err.message : '触发失败', 'error')
    }
  }

  const handleSummarize = async () => {
    if (!id) return
    try {
      await triggerSummarize(id)
      toast('正在生成总结...', 'info')
      // Poll for summary
      const check = async () => {
        const s = await getSummary(id)
        if (s) {
          setSummary(s)
          toast('总结完成', 'success')
        } else {
          setTimeout(check, 2000)
        }
      }
      setTimeout(check, 3000)
    } catch (err) {
      toast(err instanceof Error ? err.message : '总结失败', 'error')
    }
  }

  const handleSourceUpdate = async (sourceId: string, updates: Partial<Source>) => {
    if (!id) return
    try {
      await updateSource(id, sourceId, updates)
      setSources(prev => prev.map(s => s.id === sourceId ? { ...s, ...updates } : s))
      toast('已保存', 'success')
    } catch (err) {
      toast(err instanceof Error ? err.message : '保存失败', 'error')
    }
  }

  const handleExportPdf = async () => {
    if (!id) return
    try {
      toast('正在生成PDF...', 'info')
      const blob = await exportPdf(id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${topic?.id || 'export'}.pdf`
      a.click()
      URL.revokeObjectURL(url)
      toast('PDF已导出', 'success')
    } catch (err) {
      toast(err instanceof Error ? err.message : 'PDF导出失败', 'error')
    }
  }

  const handleExportJson = async () => {
    if (!id) return
    try {
      const res = await fetch(exportJsonUrl(id))
      if (!res.ok) throw new Error(`导出失败: ${res.statusText}`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${topic?.id || 'export'}.json`
      a.click()
      URL.revokeObjectURL(url)
      toast('JSON已导出', 'success')
    } catch (err) {
      toast(err instanceof Error ? err.message : 'JSON导出失败', 'error')
    }
  }

  if (loading) return <div className="empty-state"><p>加载中...</p></div>
  if (!topic) return <div className="empty-state"><h3>主题不存在</h3></div>

  const categories = topic.categories || []
  const filteredSources = sources

  return (
    <div className="result-page">
      {/* Left sidebar — categories */}
      <div className="sidebar">
        <h3>分类</h3>
        <div
          className={`sidebar-item ${selectedCategory === null ? 'active' : ''}`}
          onClick={() => setSelectedCategory(null)}
        >
          <span>全部</span>
          <span className="count">{sources.length}</span>
        </div>
        {categories.map(cat => (
          <div
            key={cat}
            className={`sidebar-item ${selectedCategory === cat ? 'active' : ''}`}
            onClick={() => setSelectedCategory(cat)}
          >
            <span>{cat}</span>
          </div>
        ))}
      </div>

      {/* Main content */}
      <div className="result-main">
        <div className="result-header">
          <h2>{topic.title || topic.keyword}</h2>
          <div className="result-actions">
            <button className="btn btn-sm" onClick={handleSummarize}>生成总结</button>
            <button className="btn btn-sm" onClick={handleExportJson}>导出JSON</button>
            <button className="btn btn-sm" onClick={handleExportPdf}>导出PDF</button>
            <button className="btn btn-sm" onClick={handleReCrawl}>重新爬取</button>
          </div>
        </div>

        {/* Summary section */}
        {summary && (
          <motion.div
            className="summary-section"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <h3>全局总结</h3>
            <div className="summary-text">{summary.content}</div>
            {summary.key_insights.length > 0 && (
              <>
                <h3>关键洞察</h3>
                <ul className="insights-list">
                  {summary.key_insights.map((insight, i) => (
                    <li key={i}>{insight}</li>
                  ))}
                </ul>
              </>
            )}
            {summary.reliability && (
              <p style={{ marginTop: 12, fontSize: 13, color: 'var(--text-muted)' }}>
                可靠度评估：{summary.reliability}
              </p>
            )}
          </motion.div>
        )}

        {/* Search & filter */}
        <div className="search-box" style={{ marginBottom: 16 }}>
          <input
            type="text"
            placeholder="搜索来源..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>

        {/* Source list */}
        <div className="source-list">
          <AnimatePresence>
            {filteredSources.map((source, i) => (
              <SourceCard
                key={source.id}
                source={source}
                expanded={expandedId === source.id}
                onToggle={() => setExpandedId(expandedId === source.id ? null : source.id)}
                onUpdate={handleSourceUpdate}
                delay={i * 0.03}
              />
            ))}
          </AnimatePresence>
          {filteredSources.length === 0 && (
            <div className="empty-state">
              <h3>暂无来源数据</h3>
              <p>点击"重新爬取"或等待爬取完成</p>
            </div>
          )}
        </div>

        {/* Stats footer */}
        <div style={{
          marginTop: 24,
          padding: '12px 0',
          borderTop: '1px solid var(--border)',
          fontSize: 13,
          color: 'var(--text-muted)',
          display: 'flex',
          gap: 16,
        }}>
          <span>共 {sources.length} 条</span>
          <span>· 已标记 {sources.filter(s => s.useful === 1).length} 条有用</span>
          <span>· 生成于 {new Date(topic.created_at).toLocaleDateString('zh-CN')}</span>
        </div>
      </div>

      {/* Right sidebar — versions */}
      <div className="version-sidebar">
        <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 12 }}>版本</h3>
        <div
          className={`sidebar-item ${selectedVersion === undefined ? 'active' : ''}`}
          onClick={() => setSelectedVersion(undefined)}
        >
          <span>最新</span>
        </div>
        {versions.map(v => (
          <div
            key={v.id}
            className={`sidebar-item ${selectedVersion === v.version ? 'active' : ''}`}
            onClick={() => setSelectedVersion(v.version)}
          >
            <span>v{v.version}</span>
            <span className="count">{v.source_count}条</span>
          </div>
        ))}
      </div>
    </div>
  )
}
