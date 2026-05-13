/** Chat page — AI conversation + preview sidebar. */

import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import { getChatHistory, sendChat, confirmTopic, getTopic, rollbackChat } from '../lib/api'
import type { ChatMessage, Topic } from '../lib/types'
import { useToast } from './Toast'

export default function ChatPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { toast } = useToast()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [topic, setTopic] = useState<Topic | null>(null)
  const [preview, setPreview] = useState<{ title: string | null; description: string | null }>({ title: null, description: null })
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editContent, setEditContent] = useState('')
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!id) return
    getTopic(id).then(setTopic).catch(console.error)
    getChatHistory(id).then(setMessages).catch(console.error)
  }, [id])

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight
    }
  }, [messages])

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || sending || !id) return
    const content = input.trim()
    setInput('')
    setSending(true)

    const userMsg: ChatMessage = { id: Date.now(), role: 'user', content, created_at: new Date().toISOString() }
    setMessages(prev => [...prev, userMsg])

    try {
      const result = await sendChat(id, content)
      const aiMsg: ChatMessage = { id: Date.now() + 1, role: 'assistant', content: result.reply, created_at: new Date().toISOString() }
      setMessages(prev => [...prev, aiMsg])

      if (result.is_ready) {
        setPreview({ title: result.title, description: result.description })
      }
    } catch (err) {
      toast(err instanceof Error ? err.message : '发送失败', 'error')
    } finally {
      setSending(false)
    }
  }

  const handleConfirm = async () => {
    if (!id) return
    try {
      await confirmTopic(id, preview.title || undefined, preview.description || undefined)
      toast('主题已确认，开始爬取', 'success')
      navigate(`/topics/${id}`)
    } catch (err) {
      toast(err instanceof Error ? err.message : '确认失败', 'error')
    }
  }

  const handleSkip = async () => {
    if (!id) return
    try {
      await confirmTopic(id)
      toast('已跳过追问，开始爬取', 'success')
      navigate(`/topics/${id}`)
    } catch (err) {
      toast(err instanceof Error ? err.message : '确认失败', 'error')
    }
  }

  const handleRollback = async (msgId: number) => {
    if (!id) return
    try {
      await rollbackChat(id, msgId)
      const refreshed = await getChatHistory(id)
      setMessages(refreshed)
      toast('已回退', 'info')
    } catch (err) {
      toast(err instanceof Error ? err.message : '回退失败', 'error')
    }
  }

  const startEdit = (msg: ChatMessage) => {
    setEditingId(msg.id)
    setEditContent(msg.content)
  }

  const saveEdit = (msgId: number) => {
    setMessages(prev => prev.map(m => m.id === msgId ? { ...m, content: editContent } : m))
    setEditingId(null)
    toast('已修改', 'success')
  }

  if (topic && topic.status !== 'chatting') {
    return (
      <div className="empty-state">
        <h3>该主题已完成对话</h3>
        <button className="btn btn-primary" onClick={() => navigate(`/topics/${id}`)}>查看结果</button>
      </div>
    )
  }

  return (
    <div className="chat-page">
      <div className="chat-messages">
        <div className="chat-messages-list" ref={listRef}>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              className={`chat-message ${msg.role}`}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
            >
              {editingId === msg.id ? (
                <div>
                  <textarea
                    value={editContent}
                    onChange={e => setEditContent(e.target.value)}
                    style={{ width: '100%', minHeight: 60, padding: 8, borderRadius: 4, border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)', fontSize: 14 }}
                  />
                  <div style={{ marginTop: 4, display: 'flex', gap: 4 }}>
                    <button className="btn btn-sm btn-primary" onClick={() => saveEdit(msg.id)}>保存</button>
                    <button className="btn btn-sm" onClick={() => setEditingId(null)}>取消</button>
                  </div>
                </div>
              ) : (
                <div
                  onDoubleClick={() => msg.role === 'user' ? handleRollback(msg.id) : startEdit(msg)}
                  title={msg.role === 'user' ? '双击回退到此消息' : '双击编辑'}
                >
                  {msg.role === 'assistant' ? (
                    <ReactMarkdown>{msg.content.replace(/\[READY\].*/s, '').trim()}</ReactMarkdown>
                  ) : (
                    msg.content
                  )}
                </div>
              )}
            </motion.div>
          ))}
          {sending && (
            <div className="chat-message assistant">
              <span className="spinner" />
            </div>
          )}
        </div>
        <div style={{ padding: '8px 16px', display: 'flex', gap: 8 }}>
          <button className="btn btn-sm" onClick={handleSkip}>跳过追问，直接开始</button>
        </div>
        <form className="chat-input" onSubmit={handleSend}>
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="输入你的回答..."
            disabled={sending}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSend(e)
              }
            }}
          />
          <button className="btn btn-primary" type="submit" disabled={!input.trim() || sending}>
            发送
          </button>
        </form>
      </div>

      <div className="chat-preview">
        <h3>主题预览</h3>
        {preview.title ? (
          <>
            <div className="preview-title">{preview.title}</div>
            <div className="preview-desc">{preview.description}</div>
            <button className="btn btn-primary" onClick={handleConfirm}>确认主题，开始爬取</button>
          </>
        ) : (
          <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>
            对话中 AI 会自动理解你的研究方向，理解清楚后会显示确认按钮。
          </p>
        )}
      </div>
    </div>
  )
}
