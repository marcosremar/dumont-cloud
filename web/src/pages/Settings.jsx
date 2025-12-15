import { useState, useEffect } from 'react'

const API_BASE = ''

export default function Settings() {
  const [settings, setSettings] = useState({
    vast_api_key: '',
    r2_access_key: '',
    r2_secret_key: '',
    r2_endpoint: '',
    r2_bucket: '',
    restic_password: ''
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState(null)

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/settings`, { credentials: 'include' })
      const data = await res.json()
      if (data.settings) {
        setSettings(data.settings)
      }
    } catch (e) {
      console.error('Failed to load settings:', e)
    }
    setLoading(false)
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setSettings(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setMessage(null)

    try {
      const res = await fetch(`${API_BASE}/api/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
        credentials: 'include'
      })
      const data = await res.json()

      if (data.success) {
        setMessage({ type: 'success', text: 'Settings saved successfully' })
      } else {
        setMessage({ type: 'error', text: data.error || 'Failed to save settings' })
      }
    } catch (e) {
      setMessage({ type: 'error', text: 'Connection error' })
    }
    setSaving(false)
  }

  if (loading) {
    return (
      <div className="container">
        <div className="empty-state">
          <div className="spinner" />
        </div>
      </div>
    )
  }

  return (
    <div className="container">
      <h2 className="page-title">Settings</h2>

      <form onSubmit={handleSubmit}>
        {message && (
          <div className={`alert alert-${message.type}`}>{message.text}</div>
        )}

        <div className="card">
          <div className="card-header">
            <span className="card-title">Vast.ai Configuration</span>
          </div>
          <div className="card-body">
            <div className="form-group">
              <label className="form-label">API Key</label>
              <input
                type="password"
                name="vast_api_key"
                className="form-input"
                value={settings.vast_api_key}
                onChange={handleChange}
                placeholder="Enter your vast.ai API key"
              />
            </div>
          </div>
        </div>

        <div className="card" style={{ marginTop: '24px' }}>
          <div className="card-header">
            <span className="card-title">Cloudflare R2 Configuration</span>
          </div>
          <div className="card-body">
            <div className="grid grid-2">
              <div className="form-group">
                <label className="form-label">Access Key</label>
                <input
                  type="password"
                  name="r2_access_key"
                  className="form-input"
                  value={settings.r2_access_key}
                  onChange={handleChange}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Secret Key</label>
                <input
                  type="password"
                  name="r2_secret_key"
                  className="form-input"
                  value={settings.r2_secret_key}
                  onChange={handleChange}
                />
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Endpoint URL</label>
              <input
                type="text"
                name="r2_endpoint"
                className="form-input"
                value={settings.r2_endpoint}
                onChange={handleChange}
                placeholder="https://xxx.r2.cloudflarestorage.com"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Bucket Name</label>
              <input
                type="text"
                name="r2_bucket"
                className="form-input"
                value={settings.r2_bucket}
                onChange={handleChange}
              />
            </div>
          </div>
        </div>

        <div className="card" style={{ marginTop: '24px' }}>
          <div className="card-header">
            <span className="card-title">Restic Configuration</span>
          </div>
          <div className="card-body">
            <div className="form-group">
              <label className="form-label">Repository Password</label>
              <input
                type="password"
                name="restic_password"
                className="form-input"
                value={settings.restic_password}
                onChange={handleChange}
              />
            </div>
          </div>
        </div>

        <div style={{ marginTop: '24px' }}>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? <span className="spinner" /> : 'Save Settings'}
          </button>
        </div>
      </form>
    </div>
  )
}
