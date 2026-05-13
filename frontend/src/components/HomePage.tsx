/** Home page — topic list + new search. */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { listTopics, createTopic, deleteTopic } from '../lib/api'
import type { Topic } from '../lib/types'
import { useToast } from './Toast'

const statusLabels: Record<string, string> = {
  chatting: '对话中',
  crawling: '爬取中',
  summarizing: '总结中',
  done: '已完成',
  error: '出错',
}

const PIN_KEY = 'topic_scout_pinned'

function getPinned(): string[] {
  try { return JSON.parse(localStorage.getItem(PIN_KEY) || '[]') } catch { return [] }
}

export default function HomePage() {
  const [topics, setTopics] = useState<Topic[]>([])
  const [keyword, setKeyword] = useState('')
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [pinnedIds, setPinnedIds] = useState<string[]>(getPinned)
  const navigate = useNavigate()
  const { toast } = useToast()

  useEffect(() => {
    listTopics().then(setTopics).catch(console.error).finally(() => setLoading(false))
  }, [])

  const togglePin = (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    setPinnedIds(prev => {
      const next = prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
      localStorage.setItem(PIN_KEY, JSON.stringify(next))
      return next
    })
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!keyword.trim() || creating) return
    setCreating(true)
    try {
      const result = await createTopic(keyword.trim())
      setTopics(prev => [result.topic, ...prev])
      setKeyword('')
      navigate(`/topics/${result.topic.id}/chat`)
    } catch (err) {
      toast(err instanceof Error ? err.message : '创建失败', 'error')
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    if (!confirm('确定删除此主题？')) return
    try {
      await deleteTopic(id)
      setTopics(prev => prev.filter(t => t.id !== id))
      toast('已删除', 'success')
    } catch (err) {
      toast(err instanceof Error ? err.message : '删除失败', 'error')
    }
  }

  // Sort: pinned first, then by created_at desc
  const sorted = [...topics].sort((a, b) => {
    const ap = pinnedIds.includes(a.id) ? 1 : 0
    const bp = pinnedIds.includes(b.id) ? 1 : 0
    if (ap !== bp) return bp - ap
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  })

  return (
    <div>
      <form className="search-box" onSubmit={handleCreate}>
        <input
          type="text"
          placeholder="输入关键词开始新的研究..."
          value={keyword}
          onChange={e => setKeyword(e.target.value)}
          disabled={creating}
        />
        <button className="btn btn-primary" type="submit" disabled={!keyword.trim() || creating}>
          {creating ? <span className="spinner" /> : '开始研究'}
        </button>
      </form>

      {loading ? (
        <div className="empty-state"><p>加载中...</p></div>
      ) : topics.length === 0 ? (
        <div className="empty-state">
          <h3>还没有研究主题</h3>
          <p>输入关键词，开始你的第一次研究</p>
        </div>
      ) : (
        <div className="topic-grid">
          {sorted.map((topic, i) => (
            <motion.div
              key={topic.id}
              className="card topic-card"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05, duration: 0.3 }}
              onClick={() => navigate(topic.status === 'chatting' ? `/topics/${topic.id}/chat` : `/topics/${topic.id}`)}
            >
              <div className="card-header">
                <span className={`badge badge-${topic.status}`}>{statusLabels[topic.status] || topic.status}</span>
                <div style={{ display: 'flex', gap: 4 }}>
                  <button
                    className="btn btn-sm"
                    onClick={e => togglePin(e, topic.id)}
                    style={{ color: pinnedIds.includes(topic.id) ? 'var(--accent)' : undefined }}
                  >
                    {pinnedIds.includes(topic.id) ? '★' : '☆'}
                  </button>
                  <button className="btn btn-sm btn-danger" onClick={e => handleDelete(e, topic.id)}>删除</button>
                </div>
              </div>
              <div className="title">{topic.title || topic.keyword}</div>
              {topic.description && <div className="description">{topic.description}</div>}
              <div className="meta">
                <span>{topic.keyword}</span>
                {topic.source_count !== undefined && topic.source_count > 0 && (
                  <span>{topic.source_count} 条来源</span>
                )}
                <span>{new Date(topic.created_at).toLocaleDateString('zh-CN')}</span>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}
