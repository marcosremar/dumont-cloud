import { useState } from 'react'
import { Cloud } from 'lucide-react'

// Logo do Dumont Cloud para a página de login
function DumontLogo() {
  return (
    <div className="login-logo">
      <svg width="64" height="64" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
        {/* Cloud shape */}
        <path
          d="M26 16.5C26 13.46 23.54 11 20.5 11C20.17 11 19.85 11.03 19.54 11.08C18.44 8.17 15.62 6 12.32 6C8.11 6 4.68 9.36 4.53 13.55C2.47 14.17 1 16.06 1 18.32C1 21.16 3.34 23.5 6.18 23.5H25C28.04 23.5 30.5 21.04 30.5 18C30.5 15.35 28.62 13.13 26.12 12.58"
          fill="url(#cloudGradientLogin)"
          stroke="url(#cloudStrokeLogin)"
          strokeWidth="1.5"
        />
        {/* D letter stylized */}
        <path
          d="M10 11V20H13C15.76 20 18 17.76 18 15C18 12.24 15.76 10 13 10H10V11Z"
          fill="#0e110e"
          stroke="#4ade80"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Accent dots */}
        <circle cx="22" cy="15" r="1.5" fill="#4ade80"/>
        <circle cx="24" cy="18" r="1" fill="#22c55e"/>
        <defs>
          <linearGradient id="cloudGradientLogin" x1="1" y1="6" x2="30.5" y2="23.5" gradientUnits="userSpaceOnUse">
            <stop stopColor="#1a1f1a"/>
            <stop offset="1" stopColor="#131713"/>
          </linearGradient>
          <linearGradient id="cloudStrokeLogin" x1="1" y1="6" x2="30.5" y2="23.5" gradientUnits="userSpaceOnUse">
            <stop stopColor="#22c55e"/>
            <stop offset="1" stopColor="#4ade80"/>
          </linearGradient>
        </defs>
      </svg>
    </div>
  )
}

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    const result = await onLogin(username, password)

    if (result.error) {
      setError(result.error)
      setLoading(false)
    }
  }

  return (
    <div className="login-container">
      <div className="login-card">
        <DumontLogo />
        <h1 className="login-title">Dumont Cloud</h1>
        <p className="login-subtitle">GPU Cloud Manager</p>

        <form onSubmit={handleSubmit}>
          {error && <div className="alert alert-error">{error}</div>}

          <div className="form-group">
            <label className="form-label">Username</label>
            <input
              type="text"
              className="form-input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              type="password"
              className="form-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button type="submit" className="btn btn-primary login-btn" disabled={loading}>
            {loading ? <span className="spinner" /> : 'Login'}
          </button>
        </form>
      </div>
    </div>
  )
}
