import { Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import HomePage from './components/HomePage'
import ChatPage from './components/ChatPage'
import ResultPage from './components/ResultPage'
import TasksPage from './components/TasksPage'
import ConfigPage from './components/ConfigPage'
import { ToastProvider } from './components/Toast'

function AppContent() {
  const location = useLocation()
  const navigate = useNavigate()
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'light')
  const [offline, setOffline] = useState(false)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch('/api/topics', { signal: AbortSignal.timeout(3000) })
        setOffline(!res.ok && res.status !== 404)
      } catch {
        setOffline(true)
      }
    }
    check()
    const interval = setInterval(check, 10000)
    return () => clearInterval(interval)
  }, [])

  const toggleTheme = () => setTheme(t => t === 'light' ? 'dark' : 'light')

  return (
    <div className="app-layout">
      {offline && (
        <div style={{
          background: 'var(--red)',
          color: '#fff',
          padding: '8px 16px',
          textAlign: 'center',
          fontSize: 14,
        }}>
          服务未启动，请运行 <code>python -m topic_scout serve</code>
        </div>
      )}
      <header className="app-header">
        <h1 onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>TopicScout</h1>
        <nav>
          <Link to="/" className={location.pathname === '/' ? 'active' : ''}>首页</Link>
          <Link to="/tasks" className={location.pathname === '/tasks' ? 'active' : ''}>任务</Link>
          <Link to="/config" className={location.pathname === '/config' ? 'active' : ''}>配置</Link>
          <button className="theme-toggle" onClick={toggleTheme} title="切换主题">
            {theme === 'light' ? '🌙' : '☀️'}
          </button>
        </nav>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/topics/:id/chat" element={<ChatPage />} />
          <Route path="/topics/:id" element={<ResultPage />} />
          <Route path="/tasks" element={<TasksPage />} />
          <Route path="/config" element={<ConfigPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <ToastProvider>
      <AppContent />
    </ToastProvider>
  )
}
