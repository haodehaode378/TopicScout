/** Tasks page — background task list with progress. */

import { useState, useEffect } from 'react'
import { listTasks, retryTask } from '../lib/api'
import type { TaskItem } from '../lib/types'
import { useToast } from './Toast'
import ProgressBar from './ProgressBar'

const statusLabels: Record<string, string> = {
  pending: '等待中',
  running: '运行中',
  done: '已完成',
  error: '出错',
}

const typeLabels: Record<string, string> = {
  crawl: '爬取',
  summarize: '总结',
  export_pdf: '导出PDF',
  export_json: '导出JSON',
}

export default function TasksPage() {
  const [tasks, setTasks] = useState<TaskItem[]>([])
  const [loading, setLoading] = useState(true)
  const { toast } = useToast()

  useEffect(() => {
    const load = () => listTasks().then(setTasks).catch(console.error).finally(() => setLoading(false))
    load()
    const interval = setInterval(load, 3000)
    return () => clearInterval(interval)
  }, [])

  const handleRetry = async (taskId: string) => {
    try {
      await retryTask(taskId)
      toast('已重新开始', 'success')
      const refreshed = await listTasks()
      setTasks(refreshed)
    } catch (err) {
      toast(err instanceof Error ? err.message : '重试失败', 'error')
    }
  }

  if (loading) return <div className="empty-state"><p>加载中...</p></div>

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>后台任务</h2>
      {tasks.length === 0 ? (
        <div className="empty-state">
          <h3>暂无任务</h3>
          <p>创建主题并开始爬取后，任务会显示在这里</p>
        </div>
      ) : (
        <table className="tasks-table">
          <thead>
            <tr>
              <th>主题</th>
              <th>类型</th>
              <th>状态</th>
              <th>进度</th>
              <th>详情</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map(task => (
              <tr key={task.id}>
                <td style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  <a href={`/topics/${task.topic_id}`}>{task.topic_id}</a>
                </td>
                <td>{typeLabels[task.type] || task.type}</td>
                <td>
                  <span className={`badge badge-${task.status === 'pending' ? 'chatting' : task.status}`}>
                    {statusLabels[task.status] || task.status}
                  </span>
                </td>
                <td>
                  <div style={{ width: 150 }}>
                    <ProgressBar value={task.progress} showLabel />
                  </div>
                </td>
                <td style={{ maxWidth: 200, fontSize: 13, color: 'var(--text-secondary)' }}>
                  {task.detail || task.error_msg}
                  {task.retry_count > 0 && (
                    <span style={{ marginLeft: 4, color: 'var(--orange)' }}>已重试 {task.retry_count} 次</span>
                  )}
                </td>
                <td>
                  {task.status === 'error' && (
                    <button className="btn btn-sm" onClick={() => handleRetry(task.id)}>重试</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
