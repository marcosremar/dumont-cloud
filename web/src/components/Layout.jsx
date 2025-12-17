import { NavLink } from 'react-router-dom'
import { useState } from 'react'
import { ChevronDown, BarChart3 } from 'lucide-react'

export default function Layout({ user, onLogout, children }) {
  const [metricsOpen, setMetricsOpen] = useState(false)

  return (
    <div className="layout">
      <header className="header">
        <div className="header-left">
          <h1 className="logo">Dumont Cloud</h1>
          <nav className="nav">
            <NavLink to="/" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              Dashboard
            </NavLink>
            <NavLink to="/machines" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              Machines
            </NavLink>
            <div
              className="nav-dropdown"
              onMouseEnter={() => setMetricsOpen(true)}
              onMouseLeave={() => setMetricsOpen(false)}
            >
              <span className="nav-link">
                Métricas
                <ChevronDown size={14} style={{ marginLeft: '4px' }} />
              </span>
              {metricsOpen && (
                <div className="dropdown-menu">
                  <NavLink to="/metrics" className="dropdown-item">
                    <BarChart3 size={16} />
                    Métricas de GPU
                  </NavLink>
                </div>
              )}
            </div>
            <NavLink to="/settings" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              Settings
            </NavLink>
          </nav>
        </div>
        <div className="header-right">
          <span className="user-name">{user?.username}</span>
          <button className="btn btn-sm" onClick={onLogout}>Logout</button>
        </div>
      </header>
      <main className="main">
        {children}
      </main>
    </div>
  )
}
