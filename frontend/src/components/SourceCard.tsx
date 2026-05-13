/** Source card component — expandable with confidence, platform icon, Lightbox, editing. */

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import type { Source } from '../lib/types'
import Lightbox from './Lightbox'

const platformIcons: Record<string, string> = {
  web: '🌐', bilibili: '🎬', douyin: '🎵', weibo: '📱', zhihu: '📖', xiaohongshu: '📕',
}

function confidenceClass(c: number) {
  if (c >= 0.8) return 'confidence-high'
  if (c >= 0.5) return 'confidence-mid'
  return 'confidence-low'
}

interface Props {
  source: Source
  expanded: boolean
  onToggle: () => void
  onUpdate: (id: string, updates: Partial<Source>) => void
  delay?: number
}

export default function SourceCard({ source, expanded, onToggle, onUpdate, delay = 0 }: Props) {
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null)
  const [editing, setEditing] = useState(false)
  const [editTitle, setEditTitle] = useState(source.title)
  const [editSummary, setEditSummary] = useState(source.summary)
  const [editContent, setEditContent] = useState(source.content)
  const [editCategory, setEditCategory] = useState(source.category)

  const toggleUseful = (e: React.MouseEvent) => {
    e.stopPropagation()
    onUpdate(source.id, { useful: source.useful === 1 ? -1 : 1 })
  }

  const startEdit = (e: React.MouseEvent) => {
    e.stopPropagation()
    setEditTitle(source.title)
    setEditSummary(source.summary)
    setEditContent(source.content)
    setEditCategory(source.category)
    setEditing(true)
  }

  const saveEdit = (e: React.MouseEvent) => {
    e.stopPropagation()
    onUpdate(source.id, {
      title: editTitle,
      summary: editSummary,
      content: editContent,
      category: editCategory,
    })
    setEditing(false)
  }

  return (
    <>
      <motion.div
        className={`card source-card ${expanded ? 'expanded' : ''}`}
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95 }}
        transition={{ delay, duration: 0.25 }}
        onClick={onToggle}
        layout
      >
        <div className="source-card-top">
          <span className="platform-icon">{platformIcons[source.platform] || '🌐'}</span>
          <span className={`confidence ${confidenceClass(source.confidence)}`}>
            {(source.confidence * 100).toFixed(0)}%
          </span>
        </div>

        {editing ? (
          <div onClick={e => e.stopPropagation()}>
            <input
              value={editTitle}
              onChange={e => setEditTitle(e.target.value)}
              placeholder="标题"
              style={{ width: '100%', padding: 4, marginBottom: 4, borderRadius: 4, border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)', fontSize: 14 }}
            />
            <input
              value={editCategory}
              onChange={e => setEditCategory(e.target.value)}
              placeholder="分类"
              style={{ width: '100%', padding: 4, marginBottom: 4, borderRadius: 4, border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)', fontSize: 13 }}
            />
            <textarea
              value={editSummary}
              onChange={e => setEditSummary(e.target.value)}
              placeholder="摘要"
              style={{ width: '100%', minHeight: 40, padding: 4, marginBottom: 4, borderRadius: 4, border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)', fontSize: 13 }}
            />
            <textarea
              value={editContent}
              onChange={e => setEditContent(e.target.value)}
              placeholder="内容"
              style={{ width: '100%', minHeight: 80, padding: 4, marginBottom: 4, borderRadius: 4, border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)', fontSize: 13 }}
            />
            <div style={{ display: 'flex', gap: 4, marginBottom: 8 }}>
              <button className="btn btn-sm btn-primary" onClick={saveEdit}>保存</button>
              <button className="btn btn-sm" onClick={(e) => { e.stopPropagation(); setEditing(false) }}>取消</button>
            </div>
          </div>
        ) : (
          <>
            <div className="source-title">{source.title || '无标题'}</div>
            {!expanded && source.summary && (
              <div className="source-summary">{source.summary}</div>
            )}
          </>
        )}

        <div className="source-meta">
          {source.author && <span>{source.author}</span>}
          <span>{new Date(source.crawl_time).toLocaleDateString('zh-CN')}</span>
          <button
            className="btn btn-sm"
            onClick={toggleUseful}
            style={{ marginLeft: 'auto', color: source.useful === 1 ? 'var(--green)' : undefined }}
          >
            {source.useful === 1 ? '★ 有用' : '☆ 标记有用'}
          </button>
        </div>

        {expanded && !editing && (
          <motion.div
            className="source-detail"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            transition={{ duration: 0.3 }}
          >
            {source.images.length > 0 && (
              <div className="images">
                {source.images.map((img, i) => (
                  <img
                    key={i}
                    src={`/${img}`}
                    alt=""
                    style={{ cursor: 'pointer' }}
                    onClick={e => { e.stopPropagation(); setLightboxIndex(i) }}
                    onError={e => (e.currentTarget.style.display = 'none')}
                  />
                ))}
              </div>
            )}
            {source.summary && (
              <div style={{ marginBottom: 16 }}>
                <h4 style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8 }}>AI 总结</h4>
                <div style={{ fontSize: 14, color: 'var(--text)' }}><ReactMarkdown>{source.summary}</ReactMarkdown></div>
              </div>
            )}
            <div className="content markdown-body">
              <ReactMarkdown>{source.content || '无内容'}</ReactMarkdown>
            </div>
            <div style={{ marginTop: 16, fontSize: 12, color: 'var(--text-muted)', display: 'flex', gap: 8, alignItems: 'center' }}>
              {source.url && <a href={source.url} target="_blank" rel="noreferrer">原始链接</a>}
              {' · '}版本 v{source.crawl_version}
              {source.category && <span> · {source.category}</span>}
              <button className="btn btn-sm" onClick={startEdit} style={{ marginLeft: 'auto' }}>编辑</button>
            </div>
          </motion.div>
        )}
      </motion.div>

      <AnimatePresence>
        {lightboxIndex !== null && source.images.length > 0 && (
          <Lightbox
            images={source.images.map(img => `/${img}`)}
            startIndex={lightboxIndex}
            onClose={() => setLightboxIndex(null)}
          />
        )}
      </AnimatePresence>
    </>
  )
}
