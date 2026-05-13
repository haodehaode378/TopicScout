/** Config page — LLM / crawl / storage settings. */

import { useState, useEffect } from 'react'
import { getConfig, updateConfig, testConnection } from '../lib/api'
import type { AppConfig } from '../lib/types'
import { useToast } from './Toast'

export default function ConfigPage() {
  const [config, setConfig] = useState<AppConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [testing, setTesting] = useState(false)
  const { toast } = useToast()

  useEffect(() => {
    getConfig()
      .then(setConfig)
      .catch(err => toast(err instanceof Error ? err.message : '加载失败', 'error'))
      .finally(() => setLoading(false))
  }, [])

  const handleSave = async () => {
    if (!config) return
    try {
      await updateConfig(config)
      toast('配置已保存', 'success')
    } catch (err) {
      toast(err instanceof Error ? err.message : '保存失败', 'error')
    }
  }

  const handleTest = async () => {
    setTesting(true)
    try {
      const result = await testConnection()
      if (result.success) {
        toast(result.message, 'success')
      } else {
        toast(result.message, 'error')
      }
    } catch (err) {
      toast(err instanceof Error ? err.message : '测试失败', 'error')
    } finally {
      setTesting(false)
    }
  }

  if (loading || !config) return <div className="empty-state"><p>加载中...</p></div>

  const updateLLM = (key: string, value: string | number) => {
    setConfig(prev => prev ? { ...prev, llm: { ...prev.llm, [key]: value } } : prev)
  }

  const updateCrawl = (key: string, value: number) => {
    setConfig(prev => prev ? { ...prev, crawl: { ...prev.crawl, [key]: value } } : prev)
  }

  return (
    <div style={{ maxWidth: 600 }}>
      <h2 style={{ marginBottom: 24 }}>配置</h2>

      <div className="config-section">
        <h3>LLM 配置</h3>
        <div className="config-field">
          <label>API 地址</label>
          <input value={config.llm.base_url} onChange={e => updateLLM('base_url', e.target.value)} />
        </div>
        <div className="config-field">
          <label>模型名称</label>
          <input value={config.llm.model_name} onChange={e => updateLLM('model_name', e.target.value)} />
        </div>
        <div className="config-field">
          <label>Temperature</label>
          <input type="number" step="0.1" min="0" max="2" value={config.llm.temperature}
            onChange={e => updateLLM('temperature', parseFloat(e.target.value))} />
        </div>
        <div className="config-field">
          <label>Max Tokens</label>
          <input type="number" value={config.llm.max_tokens}
            onChange={e => updateLLM('max_tokens', parseInt(e.target.value))} />
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
          <button className="btn btn-primary" onClick={handleSave}>保存配置</button>
          <button className="btn" onClick={handleTest} disabled={testing}>
            {testing ? <span className="spinner" /> : '测试连接'}
          </button>
        </div>
      </div>

      <div className="config-section">
        <h3>爬取配置</h3>
        <div className="config-field">
          <label>最大递归深度</label>
          <input type="number" min="1" max="20" value={config.crawl.max_depth}
            onChange={e => updateCrawl('max_depth', parseInt(e.target.value))} />
        </div>
        <div className="config-field">
          <label>每源最大条数</label>
          <input type="number" min="1" max="1000" value={config.crawl.max_items_per_source}
            onChange={e => updateCrawl('max_items_per_source', parseInt(e.target.value))} />
        </div>
        <div className="config-field">
          <label>请求间隔（秒）</label>
          <input type="number" step="0.5" min="0.5" max="30" value={config.crawl.request_interval}
            onChange={e => updateCrawl('request_interval', parseFloat(e.target.value))} />
        </div>
        <div className="config-field">
          <label>超时时间（秒）</label>
          <input type="number" min="5" max="120" value={config.crawl.request_timeout}
            onChange={e => updateCrawl('request_timeout', parseInt(e.target.value))} />
        </div>
        <div className="config-field">
          <label>最大并发数</label>
          <input type="number" min="1" max="50" value={config.crawl.max_concurrent}
            onChange={e => updateCrawl('max_concurrent', parseInt(e.target.value))} />
        </div>
        <div className="config-field">
          <label>最大重试次数</label>
          <input type="number" min="0" max="10" value={config.crawl.max_retry}
            onChange={e => updateCrawl('max_retry', parseInt(e.target.value))} />
        </div>
        <button className="btn btn-primary" onClick={handleSave} style={{ marginTop: 16 }}>保存配置</button>
      </div>

      <div className="config-section">
        <h3>存储配置</h3>
        <div className="config-field">
          <label>数据目录</label>
          <input value={config.storage.data_dir} readOnly style={{ opacity: 0.6 }} />
        </div>
        <div className="config-field">
          <label>数据库路径</label>
          <input value={config.storage.db_path} readOnly style={{ opacity: 0.6 }} />
        </div>
        <div className="config-field">
          <label>存储上限（GB）</label>
          <input type="number" step="0.5" min="0.5" max="100" value={config.storage.storage_limit_gb}
            onChange={e => setConfig(prev => prev ? { ...prev, storage: { ...prev.storage, storage_limit_gb: parseFloat(e.target.value) } } : prev)} />
        </div>
        <button className="btn btn-primary" onClick={handleSave} style={{ marginTop: 16 }}>保存配置</button>
      </div>
    </div>
  )
}
