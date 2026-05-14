/** Config page — LLM / crawl / storage settings with provider cards. */

import { useState, useEffect } from 'react'
import { getConfig, updateConfig, testConnection, wxLogin, wxLoginStatus, wxLogout, wxSearch, wxSubscribe, wxAccounts, wxUnsubscribe } from '../lib/api'
import type { AppConfig, WxLoginStatus as WxLoginStatusType, WxSearchResult, WxAccount } from '../lib/types'
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

  // WeChat state
  const [wxStatus, setWxStatus] = useState<WxLoginStatusType>({ status: 'idle', logged_in: false, error: '', qr_exists: false })
  const [wxPolling, setWxPolling] = useState(false)
  const [wxSearchKeyword, setWxSearchKeyword] = useState('')
  const [wxSearchResults, setWxSearchResults] = useState<WxSearchResult[]>([])
  const [wxSearching, setWxSearching] = useState(false)
  const [wxSubscribed, setWxSubscribed] = useState<WxAccount[]>([])

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

    // Load WeChat status and subscribed accounts
    wxLoginStatus().then(setWxStatus).catch(() => {})
    wxAccounts().then(setWxSubscribed).catch(() => {})
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

  // WeChat handlers
  const handleWxLogin = async () => {
    try {
      const result = await wxLogin()
      setWxStatus(prev => ({ ...prev, status: result.status as WxLoginStatusType['status'] }))
      // Start polling for status changes
      setWxPolling(true)
      const poll = async () => {
        for (let i = 0; i < 120; i++) {
          await new Promise(r => setTimeout(r, 2000))
          try {
            const status = await wxLoginStatus()
            setWxStatus(status)
            if (status.logged_in || status.status === 'error') {
              setWxPolling(false)
              if (status.logged_in) {
                const accounts = await wxAccounts()
                setWxSubscribed(accounts)
              }
              return
            }
          } catch { break }
        }
        setWxPolling(false)
      }
      poll()
    } catch (err) {
      toast(err instanceof Error ? err.message : '启动登录失败', 'error')
    }
  }

  const handleWxLogout = async () => {
    try {
      await wxLogout()
      setWxStatus({ status: 'idle', logged_in: false, error: '', qr_exists: false })
      setWxSubscribed([])
      setWxSearchResults([])
    } catch (err) {
      toast(err instanceof Error ? err.message : '退出登录失败', 'error')
    }
  }

  const handleWxSearch = async () => {
    if (!wxSearchKeyword.trim()) return
    setWxSearching(true)
    try {
      const result = await wxSearch(wxSearchKeyword.trim())
      setWxSearchResults(result.accounts)
      if (result.accounts.length === 0) toast('未找到公众号', 'error')
    } catch (err) {
      toast(err instanceof Error ? err.message : '搜索失败', 'error')
    } finally {
      setWxSearching(false)
    }
  }

  const handleWxSubscribe = async (account: WxSearchResult) => {
    try {
      await wxSubscribe({
        fakeid: account.fakeid,
        nickname: account.nickname,
        alias: account.alias,
        avatar_url: account.round_head_img,
      })
      toast(`已订阅: ${account.nickname}`, 'success')
      const accounts = await wxAccounts()
      setWxSubscribed(accounts)
    } catch (err) {
      toast(err instanceof Error ? err.message : '订阅失败', 'error')
    }
  }

  const handleWxUnsubscribe = async (fakeid: string) => {
    try {
      await wxUnsubscribe(fakeid)
      setWxSubscribed(prev => prev.filter(a => a.id !== fakeid))
      toast('已取消订阅', 'success')
    } catch (err) {
      toast(err instanceof Error ? err.message : '取消订阅失败', 'error')
    }
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

      {/* WeChat MP Config */}
      <div className="config-section">
        <h3>微信公众号</h3>
        <div style={{ padding: '12px 0' }}>
          {!wxStatus.logged_in ? (
            <div>
              <p style={{ color: 'var(--text-muted)', marginBottom: 12, fontSize: 14 }}>
                扫码登录微信公众号管理平台，即可搜索和订阅公众号、自动爬取文章。
              </p>
              <button className="btn btn-primary" onClick={handleWxLogin} disabled={wxPolling}>
                {wxStatus.status === 'loading' ? '正在加载...' :
                 wxStatus.status === 'qr_ready' ? '请扫码' :
                 wxPolling ? <span className="spinner" /> : '登录微信公众号'}
              </button>
              {wxStatus.status === 'qr_ready' && (
                <div style={{ marginTop: 16 }}>
                  <img
                    src={`/api/wx/qrcode?t=${Date.now()}`}
                    alt="微信登录二维码"
                    style={{ width: 200, height: 200, border: '1px solid var(--border)', borderRadius: 8 }}
                  />
                  <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>
                    请使用微信扫描二维码登录（二维码约60秒过期）
                  </p>
                </div>
              )}
              {wxStatus.error && (
                <p style={{ color: 'var(--danger)', marginTop: 8, fontSize: 13 }}>{wxStatus.error}</p>
              )}
            </div>
          ) : (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
                <span style={{ color: 'var(--success)' }}>已登录</span>
                <button className="btn" onClick={handleWxLogout} style={{ fontSize: 12, padding: '4px 12px' }}>退出登录</button>
              </div>

              {/* Search */}
              <div style={{ marginBottom: 20 }}>
                <label style={{ display: 'block', marginBottom: 6, fontWeight: 500 }}>搜索公众号</label>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input
                    value={wxSearchKeyword}
                    onChange={e => setWxSearchKeyword(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleWxSearch()}
                    placeholder="输入公众号名称"
                    style={{ flex: 1 }}
                  />
                  <button className="btn" onClick={handleWxSearch} disabled={wxSearching}>
                    {wxSearching ? <span className="spinner" /> : '搜索'}
                  </button>
                </div>
                {wxSearchResults.length > 0 && (
                  <div style={{ marginTop: 8, border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
                    {wxSearchResults.map(r => (
                      <div key={r.fakeid} style={{
                        display: 'flex', alignItems: 'center', gap: 12, padding: '10px 12px',
                        borderBottom: '1px solid var(--border)',
                      }}>
                        {r.round_head_img && (
                          <img src={r.round_head_img} alt="" style={{ width: 36, height: 36, borderRadius: '50%' }} />
                        )}
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontWeight: 500 }}>{r.nickname}</div>
                          {r.alias && <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{r.alias}</div>}
                        </div>
                        <button
                          className="btn btn-primary"
                          onClick={() => handleWxSubscribe(r)}
                          disabled={wxSubscribed.some(a => a.id === r.fakeid)}
                          style={{ fontSize: 12, padding: '4px 12px' }}
                        >
                          {wxSubscribed.some(a => a.id === r.fakeid) ? '已订阅' : '订阅'}
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Subscribed accounts */}
              <div>
                <label style={{ display: 'block', marginBottom: 6, fontWeight: 500 }}>
                  已订阅公众号 {wxSubscribed.length > 0 && `(${wxSubscribed.length})`}
                </label>
                {wxSubscribed.length === 0 ? (
                  <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>暂无订阅，搜索公众号后点击"订阅"添加</p>
                ) : (
                  <div style={{ border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
                    {wxSubscribed.map(a => (
                      <div key={a.id} style={{
                        display: 'flex', alignItems: 'center', gap: 12, padding: '10px 12px',
                        borderBottom: '1px solid var(--border)',
                      }}>
                        {a.avatar_url && (
                          <img src={a.avatar_url} alt="" style={{ width: 36, height: 36, borderRadius: '50%' }} />
                        )}
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontWeight: 500 }}>{a.nickname}</div>
                          {a.alias && <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{a.alias}</div>}
                        </div>
                        <button
                          className="btn"
                          onClick={() => handleWxUnsubscribe(a.id)}
                          style={{ fontSize: 12, padding: '4px 12px', color: 'var(--danger)' }}
                        >
                          取消订阅
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
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
