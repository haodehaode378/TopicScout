/** Config page — LLM / crawl / storage settings with provider cards. */

import { useState, useEffect } from 'react'
import { getConfig, updateConfig, testConnection } from '../lib/api'
import type { AppConfig } from '../lib/types'
import { useToast } from './Toast'

interface Provider {
  id: string
  name: string
  description: string
  icon: string
  base_url: string
  models: string[]
  default_model: string
  docs_url: string
}

const providers: Provider[] = [
  {
    id: 'deepseek',
    name: 'DeepSeek',
    description: '高性价比推理模型，支持长上下文',
    icon: '',
    base_url: 'https://api.deepseek.com',
    models: ['deepseek-v4-flash', 'deepseek-v4-pro', 'deepseek-chat', 'deepseek-reasoner'],
    default_model: 'deepseek-v4-flash',
    docs_url: 'https://platform.deepseek.com',
  },
  {
    id: 'kimi',
    name: 'Kimi (月之暗面)',
    description: '超长上下文，擅长文档理解和多轮对话',
    icon: '',
    base_url: 'https://api.moonshot.cn/v1',
    models: [
      'kimi-k2.6', 'kimi-k2.5',
      'kimi-k2-thinking', 'kimi-k2-thinking-turbo',
      'kimi-k2-0905-preview', 'kimi-k2-turbo-preview',
      'moonshot-v1-8k', 'moonshot-v1-32k', 'moonshot-v1-128k',
    ],
    default_model: 'kimi-k2.6',
    docs_url: 'https://platform.moonshot.cn',
  },
  {
    id: 'qwen',
    name: '通义千问 (阿里云)',
    description: '多模态大模型，百炼平台 OpenAI 兼容接口',
    icon: '',
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    models: ['qwen-max', 'qwen-plus', 'qwen-turbo', 'qwen-flash', 'qwen-long'],
    default_model: 'qwen-plus',
    docs_url: 'https://www.aliyun.com/product/bailian',
  },
  {
    id: 'minimax',
    name: 'MiniMax',
    description: '角色扮演和创意写作优秀，支持多模态',
    icon: '',
    base_url: 'https://api.minimaxi.com/v1',
    models: ['MiniMax-M2.7', 'MiniMax-M2.7-highspeed', 'MiniMax-M2.5', 'MiniMax-M2.5-highspeed'],
    default_model: 'MiniMax-M2.7',
    docs_url: 'https://platform.minimax.io',
  },
  {
    id: 'mimo',
    name: '小米 MiMo',
    description: '小米自研大模型，需小米平台账号',
    icon: '',
    base_url: 'https://api.xiaomimimo.com/v1',
    models: ['MiMo-V2.5-Pro', 'MiMo-V2.5', 'MiMo-V2-Pro', 'MiMo-V2-Flash'],
    default_model: 'MiMo-V2.5',
    docs_url: 'https://platform.xiaomimimo.com',
  },
  {
    id: 'custom',
    name: '自定义',
    description: '任意 OpenAI 兼容 API，自行填写地址和模型',
    icon: '⚙️',
    base_url: '',
    models: [],
    default_model: '',
    docs_url: '',
  },
]

export default function ConfigPage() {
  const [config, setConfig] = useState<AppConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [testing, setTesting] = useState(false)
  const [selectedProvider, setSelectedProvider] = useState<string>('deepseek')
  const { toast } = useToast()

  useEffect(() => {
    getConfig()
      .then(c => {
        setConfig(c)
        // Detect which provider matches current config
        const match = providers.find(p => c.llm.base_url === p.base_url)
        if (match) setSelectedProvider(match.id)
        else setSelectedProvider('custom')
      })
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

  const selectProvider = (provider: Provider) => {
    setSelectedProvider(provider.id)
    if (provider.id !== 'custom') {
      const lockedModels = ['kimi-k2.5', 'kimi-k2.6', 'kimi-k2-thinking', 'kimi-k2-thinking-turbo']
      const isLocked = lockedModels.includes(provider.default_model)
      setConfig(prev => prev ? {
        ...prev,
        llm: {
          ...prev.llm,
          base_url: provider.base_url,
          model_name: provider.default_model,
          temperature: isLocked ? 1 : prev.llm.temperature,
        },
      } : prev)
    }
  }

  const updateLLM = (key: string, value: string | number) => {
    setConfig(prev => prev ? { ...prev, llm: { ...prev.llm, [key]: value } } : prev)
  }

  const updateCrawl = (key: string, value: number) => {
    setConfig(prev => prev ? { ...prev, crawl: { ...prev.crawl, [key]: value } } : prev)
  }

  if (loading || !config) return <div className="empty-state"><p>加载中...</p></div>

  const currentProvider = providers.find(p => p.id === selectedProvider)
  const lockedModels = ['kimi-k2.5', 'kimi-k2.6', 'kimi-k2-thinking', 'kimi-k2-thinking-turbo']
  const isTempLocked = lockedModels.includes(config.llm.model_name)

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>配置</h2>

      {/* LLM Provider Cards */}
      <div className="config-section">
        <h3>LLM 服务商</h3>
        <div className="provider-grid">
          {providers.map(p => (
            <div
              key={p.id}
              className={`provider-card ${selectedProvider === p.id ? 'selected' : ''}`}
              onClick={() => selectProvider(p)}
            >
              <div className="provider-icon">{p.icon || p.name.charAt(0)}</div>
              <div className="provider-info">
                <div className="provider-name">{p.name}</div>
                <div className="provider-desc">{p.description}</div>
              </div>
              {selectedProvider === p.id && (
                <div className="provider-check">✓</div>
              )}
            </div>
          ))}
        </div>

        {/* Selected provider details */}
        <div className="provider-detail">
          <div className="config-field">
            <label>API 地址</label>
            <input
              value={config.llm.base_url}
              onChange={e => updateLLM('base_url', e.target.value)}
              placeholder="https://api.example.com/v1"
              readOnly={selectedProvider !== 'custom'}
              style={selectedProvider !== 'custom' ? { opacity: 0.7 } : undefined}
            />
          </div>
          <div className="config-field">
            <label>API Key</label>
            <input
              type="password"
              value={(config.llm as Record<string, unknown>).api_key as string || ''}
              onChange={e => updateLLM('api_key', e.target.value)}
              placeholder="sk-xxxxxxxx"
            />
          </div>
          <div className="config-field">
            <label>模型</label>
            {currentProvider && currentProvider.models.length > 0 ? (
              <select
                value={config.llm.model_name}
                onChange={e => {
                  const modelName = e.target.value
                  const lockedModels = ['kimi-k2.5', 'kimi-k2.6', 'kimi-k2-thinking', 'kimi-k2-thinking-turbo']
                  setConfig(prev => prev ? {
                    ...prev,
                    llm: {
                      ...prev.llm,
                      model_name: modelName,
                      temperature: lockedModels.includes(modelName) ? 1 : prev.llm.temperature,
                    },
                  } : prev)
                }}
                className="config-select"
              >
                {currentProvider.models.map(m => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            ) : (
              <input
                value={config.llm.model_name}
                onChange={e => updateLLM('model_name', e.target.value)}
                placeholder="模型名称"
              />
            )}
          </div>
          <div className="config-field">
            <label>Temperature {isTempLocked && <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>(此模型固定为 1)</span>}</label>
            <input
              type="number"
              step="0.1"
              min="0"
              max="2"
              value={config.llm.temperature}
              onChange={e => updateLLM('temperature', parseFloat(e.target.value))}
              readOnly={isTempLocked}
              style={isTempLocked ? { opacity: 0.6 } : undefined}
            />
          </div>
          <div className="config-field">
            <label>Max Tokens</label>
            <input
              type="number"
              value={config.llm.max_tokens}
              onChange={e => updateLLM('max_tokens', parseInt(e.target.value))}
            />
          </div>
          {currentProvider && currentProvider.docs_url && (
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
              <a href={currentProvider.docs_url} target="_blank" rel="noreferrer">
                前往 {currentProvider.name} 控制台获取 API Key →
              </a>
            </div>
          )}
        </div>
      </div>

      {/* Crawl Config */}
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
      </div>

      {/* Storage Config */}
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
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', gap: 8 }}>
        <button className="btn btn-primary" onClick={handleSave}>保存配置</button>
        <button className="btn" onClick={handleTest} disabled={testing}>
          {testing ? <span className="spinner" /> : '测试连接'}
        </button>
      </div>
    </div>
  )
}
