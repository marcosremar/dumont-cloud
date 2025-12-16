import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Filler,
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler)

const API_BASE = ''

// Feather Icons as inline SVGs
const icons = {
  grid: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>,
  server: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect><rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect><line x1="6" y1="6" x2="6.01" y2="6"></line><line x1="6" y1="18" x2="6.01" y2="18"></line></svg>,
  plus: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>,
  activity: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>,
  fileText: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>,
  settings: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>,
  cpu: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect><rect x="9" y="9" width="6" height="6"></rect><line x1="9" y1="1" x2="9" y2="4"></line><line x1="15" y1="1" x2="15" y2="4"></line><line x1="9" y1="20" x2="9" y2="23"></line><line x1="15" y1="20" x2="15" y2="23"></line><line x1="20" y1="9" x2="23" y2="9"></line><line x1="20" y1="14" x2="23" y2="14"></line><line x1="1" y1="9" x2="4" y2="9"></line><line x1="1" y1="14" x2="4" y2="14"></line></svg>,
  thermometer: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"></path></svg>,
  clock: <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>,
  code: <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>,
  chevronDown: <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>,
  moreVertical: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="1"></circle><circle cx="12" cy="5" r="1"></circle><circle cx="12" cy="19" r="1"></circle></svg>,
  zap: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>,
  bell: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>,
  user: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>,
}

// Mini sparkline chart component
function SparklineChart({ data, color }) {
  const chartData = {
    labels: data.map((_, i) => i),
    datasets: [{
      data,
      borderColor: color,
      backgroundColor: `${color}20`,
      borderWidth: 1.5,
      fill: true,
      tension: 0.4,
      pointRadius: 0,
    }]
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { display: false },
      y: { display: false, min: 0, max: 100 }
    },
    elements: { line: { borderCapStyle: 'round' } }
  }

  return (
    <div style={{ height: '32px', width: '100%' }}>
      <Line data={chartData} options={options} />
    </div>
  )
}

// Machine card component
function MachineCard({ machine, onVSCode, onDestroy }) {
  const [showMenu, setShowMenu] = useState(false)
  const [hibernateTime, setHibernateTime] = useState(10)
  const [budgetCap, setBudgetCap] = useState('')
  const [smartIdle, setSmartIdle] = useState(false)

  // Historical data for sparklines (simulated for now, would come from API)
  const [gpuHistory] = useState(() => Array.from({ length: 20 }, () => Math.random() * 40 + 30))
  const [memHistory] = useState(() => Array.from({ length: 20 }, () => Math.random() * 30 + 40))
  const [cpuHistory] = useState(() => Array.from({ length: 20 }, () => Math.random() * 20 + 10))
  const [tempHistory] = useState(() => Array.from({ length: 20 }, () => Math.random() * 15 + 55))

  const gpuUtil = machine.gpu_util || Math.round(gpuHistory[gpuHistory.length - 1])
  const memUtil = machine.mem_usage || Math.round(memHistory[memHistory.length - 1])
  const cpuUtil = machine.cpu_util || Math.round(cpuHistory[cpuHistory.length - 1])
  const temp = machine.gpu_temp || Math.round(tempHistory[tempHistory.length - 1])

  const gpuName = machine.gpu_name || 'GPU'
  const isRunning = machine.actual_status === 'running'

  return (
    <div className="dumont-machine-card">
      {/* Card Header */}
      <div className="dumont-card-header">
        <div className="dumont-card-title">
          <span className="dumont-gpu-icon">{icons.cpu}</span>
          <span>{gpuName}</span>
        </div>
        <div style={{ position: 'relative' }}>
          <button
            className="dumont-menu-btn"
            onClick={() => setShowMenu(!showMenu)}
          >
            {icons.moreVertical}
          </button>
          {showMenu && (
            <>
              <div className="dumont-menu-backdrop" onClick={() => setShowMenu(false)} />
              <div className="dumont-dropdown-menu">
                <button className="dumont-dropdown-item">Startup Script</button>
                <button className="dumont-dropdown-item">View Logs</button>
                <button className="dumont-dropdown-item">Force Snapshot</button>
                <div className="dumont-dropdown-divider" />
                <button
                  className="dumont-dropdown-item dumont-danger"
                  onClick={() => { setShowMenu(false); onDestroy(machine.id) }}
                >
                  Destroy Machine
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="dumont-metrics-grid">
        <div className="dumont-metric">
          <div className="dumont-metric-header">
            <span className="dumont-metric-label">GPU %</span>
            <span className="dumont-metric-value" style={{ color: '#009c3b' }}>{gpuUtil}%</span>
          </div>
          <SparklineChart data={gpuHistory} color="#009c3b" />
        </div>
        <div className="dumont-metric">
          <div className="dumont-metric-header">
            <span className="dumont-metric-label">Memoria</span>
            <span className="dumont-metric-value" style={{ color: '#ffdf00' }}>{memUtil}%</span>
          </div>
          <SparklineChart data={memHistory} color="#ffdf00" />
        </div>
        <div className="dumont-metric">
          <div className="dumont-metric-header">
            <span className="dumont-metric-label">CPU %</span>
            <span className="dumont-metric-value" style={{ color: '#009c3b' }}>{cpuUtil}%</span>
          </div>
          <SparklineChart data={cpuHistory} color="#009c3b" />
        </div>
        <div className="dumont-metric">
          <div className="dumont-metric-header">
            <span className="dumont-metric-label">Temp</span>
            <span className="dumont-metric-value" style={{ color: temp > 70 ? '#ef4444' : '#ffdf00' }}>{temp}C</span>
          </div>
          <SparklineChart data={tempHistory} color={temp > 70 ? '#ef4444' : '#ffdf00'} />
        </div>
      </div>

      {/* Control Rows */}
      <div className="dumont-controls">
        {/* Hibernate Row */}
        <div className="dumont-control-row">
          <div className="dumont-control-label">
            {icons.clock}
            <span>Hibernar apos:</span>
            <select
              value={hibernateTime}
              onChange={(e) => setHibernateTime(e.target.value)}
              className="dumont-select-inline"
            >
              <option value={5}>5</option>
              <option value={10}>10</option>
              <option value={15}>15</option>
              <option value={30}>30</option>
            </select>
            <span>Minutes</span>
          </div>
          <button
            className="dumont-btn-vscode"
            onClick={() => onVSCode(machine)}
            disabled={!isRunning}
          >
            {icons.code}
            <span>VS Code</span>
          </button>
        </div>

        {/* Budget Cap Row */}
        <div className="dumont-control-row">
          <div className="dumont-control-label">
            <span>Budget Cap ($):</span>
            <input
              type="text"
              placeholder="$"
              value={budgetCap}
              onChange={(e) => setBudgetCap(e.target.value)}
              className="dumont-input-inline"
            />
          </div>
          <div className="dumont-dropdown-inline">
            <button className="dumont-btn-dropdown">
              <span>Manage</span>
              {icons.chevronDown}
            </button>
          </div>
        </div>

        {/* Smart Idle Row */}
        <div className="dumont-control-row">
          <label className="dumont-checkbox-label">
            <input
              type="checkbox"
              checked={smartIdle}
              onChange={(e) => setSmartIdle(e.target.checked)}
            />
            <span>Smart Idle Detection (GPU &lt; 5%)</span>
          </label>
        </div>
      </div>
    </div>
  )
}

export default function MinhasMaquinas() {
  const [machines, setMachines] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [balance, setBalance] = useState(null)
  const [simulationMode, setSimulationMode] = useState(false)

  useEffect(() => {
    fetchMachines()
    fetchBalance()
    const interval = setInterval(() => {
      fetchMachines()
      fetchBalance()
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  const fetchMachines = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/instances`, { credentials: 'include' })
      if (!res.ok) throw new Error('Erro ao buscar maquinas')
      const data = await res.json()
      setMachines(data.instances || [])
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const fetchBalance = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/balance`, { credentials: 'include' })
      if (res.ok) {
        const data = await res.json()
        setBalance(data.credit || 0)
      }
    } catch (err) {
      console.error('Error fetching balance:', err)
    }
  }

  const openVSCode = (machine) => {
    if (!machine.ssh_host || !machine.ssh_port) {
      alert('SSH nao disponivel ainda')
      return
    }
    window.open(`https://${machine.id}.dumontcloud.com/?folder=/workspace`, '_blank')
  }

  const handleDestroy = async (machineId) => {
    if (!confirm('Tem certeza que deseja destruir esta maquina?')) return
    try {
      const res = await fetch(`${API_BASE}/api/instances/${machineId}`, {
        method: 'DELETE',
        credentials: 'include'
      })
      if (!res.ok) throw new Error('Erro ao destruir maquina')
      fetchMachines()
    } catch (err) {
      alert(err.message)
    }
  }

  const activeMachines = machines.filter(m => m.actual_status === 'running')
  const totalGpuMem = activeMachines.reduce((acc, m) => acc + (m.gpu_ram || 24000), 0)
  const totalUptime = activeMachines.reduce((acc, m) => {
    if (m.start_date) {
      const uptimeHours = (Date.now() / 1000 - m.start_date) / 3600
      return acc + uptimeHours
    }
    return acc
  }, 0)
  const totalCostToday = activeMachines.reduce((acc, m) => acc + (m.dph_total || 0) * Math.min(totalUptime, 24), 0)

  if (loading) {
    return (
      <div className="dumont-layout">
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', flex: 1 }}>
          <div className="spinner" />
        </div>
      </div>
    )
  }

  return (
    <div className="dumont-layout">
      {/* Sidebar */}
      <aside className="dumont-sidebar">
        <div className="dumont-logo">
          <span className="dumont-logo-icon">{icons.zap}</span>
          <span className="dumont-logo-text">Dumont</span>
        </div>
        <nav className="dumont-nav">
          <Link to="/" className="dumont-nav-item">
            {icons.grid}
            <span>Dashboard</span>
          </Link>
          <Link to="/machines" className="dumont-nav-item active">
            {icons.server}
            <span>Maquinas</span>
          </Link>
          <Link to="/" className="dumont-nav-item">
            {icons.plus}
            <span>Nova Maquina</span>
          </Link>
          <Link to="/machines" className="dumont-nav-item">
            {icons.activity}
            <span>Metricas</span>
          </Link>
          <Link to="/machines" className="dumont-nav-item">
            {icons.fileText}
            <span>Logs</span>
          </Link>
          <Link to="/settings" className="dumont-nav-item">
            {icons.settings}
            <span>Configuracoes</span>
          </Link>
        </nav>
      </aside>

      {/* Main Content */}
      <main className="dumont-main">
        {/* Header */}
        <header className="dumont-header">
          <div className="dumont-breadcrumb">
            Dashboard / <span className="dumont-breadcrumb-current">Maquinas</span>
          </div>
          <div className="dumont-header-actions">
            <div className="dumont-simulation-toggle">
              <label className="dumont-toggle">
                <input
                  type="checkbox"
                  checked={simulationMode}
                  onChange={(e) => setSimulationMode(e.target.checked)}
                />
                <span className="dumont-toggle-slider"></span>
              </label>
              <span className="dumont-toggle-label">Modo Simulacao</span>
            </div>
            <button className="dumont-icon-btn">
              {icons.bell}
            </button>
            <div className="dumont-user-menu">
              <button className="dumont-user-btn">
                {icons.user}
                {icons.chevronDown}
              </button>
            </div>
          </div>
        </header>

        {/* Stats Grid */}
        <div className="dumont-stats-grid">
          <div className="dumont-stat-card">
            <div className="dumont-stat-icon dumont-stat-green">{icons.server}</div>
            <div className="dumont-stat-content">
              <div className="dumont-stat-value">{activeMachines.length}</div>
              <div className="dumont-stat-label">Maquinas Ativas</div>
            </div>
          </div>
          <div className="dumont-stat-card">
            <div className="dumont-stat-icon dumont-stat-yellow">{icons.cpu}</div>
            <div className="dumont-stat-content">
              <div className="dumont-stat-value">{Math.round(totalGpuMem / 1024)} GB</div>
              <div className="dumont-stat-label">Memoria Total</div>
            </div>
          </div>
          <div className="dumont-stat-card">
            <div className="dumont-stat-icon dumont-stat-blue">{icons.clock}</div>
            <div className="dumont-stat-content">
              <div className="dumont-stat-value">{totalUptime.toFixed(1)}h</div>
              <div className="dumont-stat-label">Uptime Hoje</div>
            </div>
          </div>
          <div className="dumont-stat-card">
            <div className="dumont-stat-icon dumont-stat-green">{icons.activity}</div>
            <div className="dumont-stat-content">
              <div className="dumont-stat-value">${totalCostToday.toFixed(2)}</div>
              <div className="dumont-stat-label">Custo Hoje</div>
            </div>
          </div>
        </div>

        {/* Machines Section */}
        <div className="dumont-section">
          <div className="dumont-section-header">
            <h2 className="dumont-section-title">Minhas Maquinas</h2>
            <Link to="/" className="dumont-btn-primary">
              {icons.plus}
              <span>Nova Maquina</span>
            </Link>
          </div>

          {error && (
            <div className="alert alert-error" style={{ marginBottom: '20px' }}>
              {error}
            </div>
          )}

          {activeMachines.length === 0 ? (
            <div className="dumont-empty-state">
              <p>Nenhuma maquina ativa no momento</p>
              <Link to="/" className="dumont-btn-primary" style={{ marginTop: '16px' }}>
                Criar primeira maquina
              </Link>
            </div>
          ) : (
            <div className="dumont-machines-grid">
              {activeMachines.map((machine) => (
                <MachineCard
                  key={machine.id}
                  machine={machine}
                  onVSCode={openVSCode}
                  onDestroy={handleDestroy}
                />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
