import { useState, useEffect } from 'react'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { BarChart3, TrendingUp, TrendingDown, ArrowRight, Package, Cpu, AlertTriangle, Search } from 'lucide-react'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const API_BASE = ''

export default function GPUMetrics() {
  const [loading, setLoading] = useState(true)
  const [agentStatus, setAgentStatus] = useState(null)
  const [summary, setSummary] = useState([])
  const [history, setHistory] = useState([])
  const [alerts, setAlerts] = useState([])

  // Filtros
  const [selectedGPUs, setSelectedGPUs] = useState(['all'])
  const [timeRange, setTimeRange] = useState(24)
  const [priceRange, setPriceRange] = useState([0, 2])
  const [minOffers, setMinOffers] = useState(0)
  const [showOnlyDrops, setShowOnlyDrops] = useState(false)

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 60000)
    return () => clearInterval(interval)
  }, [timeRange])

  const loadData = async () => {
    try {
      // Status do agente
      const statusRes = await fetch(`${API_BASE}/api/price-monitor/status`, { credentials: 'include' })
      const statusData = await statusRes.json()
      if (statusData.success) setAgentStatus(statusData.agent)

      // Resumo
      const summaryRes = await fetch(`${API_BASE}/api/price-monitor/summary`, { credentials: 'include' })
      const summaryData = await summaryRes.json()
      if (summaryData.success) setSummary(summaryData.summary)

      // Histórico
      const historyRes = await fetch(`${API_BASE}/api/price-monitor/history?hours=${timeRange}&limit=200`, { credentials: 'include' })
      const historyData = await historyRes.json()
      if (historyData.success) setHistory(historyData.history)

      // Alertas
      const alertsRes = await fetch(`${API_BASE}/api/price-monitor/alerts?hours=24&limit=20`, { credentials: 'include' })
      const alertsData = await alertsRes.json()
      if (alertsData.success) setAlerts(alertsData.alerts)

      setLoading(false)
    } catch (error) {
      console.error('Erro ao carregar métricas:', error)
      setLoading(false)
    }
  }

  // Filtrar dados
  const filteredSummary = summary.filter(gpu => {
    if (selectedGPUs.includes('all')) return true
    return selectedGPUs.includes(gpu.gpu_name)
  }).filter(gpu => {
    return gpu.current.avg_price >= priceRange[0] && gpu.current.avg_price <= priceRange[1]
  }).filter(gpu => {
    return gpu.current.total_offers >= minOffers
  }).filter(gpu => {
    if (!showOnlyDrops) return true
    return gpu.trend_24h?.direction === 'down'
  })

  const filteredAlerts = showOnlyDrops
    ? alerts.filter(a => a.alert_type === 'price_drop')
    : alerts

  // Preparar dados do gráfico
  const getChartData = (gpuName) => {
    const gpuHistory = history
      .filter(h => h.gpu_name === gpuName)
      .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
      .slice(-20)

    return {
      labels: gpuHistory.map(h => {
        const date = new Date(h.timestamp)
        return `${date.getHours()}:${date.getMinutes().toString().padStart(2, '0')}`
      }),
      datasets: [
        {
          label: 'Preço Médio',
          data: gpuHistory.map(h => h.avg_price),
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          fill: true,
          tension: 0.4,
        },
        {
          label: 'Preço Mín',
          data: gpuHistory.map(h => h.min_price),
          borderColor: '#10b981',
          backgroundColor: 'rgba(16, 185, 129, 0.05)',
          fill: false,
          tension: 0.4,
          borderDash: [5, 5],
        },
        {
          label: 'Preço Máx',
          data: gpuHistory.map(h => h.max_price),
          borderColor: '#ef4444',
          backgroundColor: 'rgba(239, 68, 68, 0.05)',
          fill: false,
          tension: 0.4,
          borderDash: [5, 5],
        },
      ],
    }
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'bottom',
        labels: {
          color: '#9ca3af',
          font: { size: 11 },
          usePointStyle: true,
        },
      },
      tooltip: {
        callbacks: {
          label: (context) => `${context.dataset.label}: $${context.parsed.y.toFixed(4)}/h`,
        },
      },
    },
    scales: {
      y: {
        ticks: {
          color: '#9ca3af',
          callback: (value) => `$${value.toFixed(2)}`,
        },
        grid: {
          color: '#30363d',
        },
      },
      x: {
        ticks: {
          color: '#9ca3af',
          maxRotation: 0,
        },
        grid: {
          display: false,
        },
      },
    },
  }

  const formatPrice = (price) => `$${price.toFixed(4)}/h`
  const formatTime = (timestamp) => new Date(timestamp).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })

  const getTrendIcon = (direction) => {
    if (direction === 'up') return <TrendingUp size={20} />
    if (direction === 'down') return <TrendingDown size={20} />
    return <ArrowRight size={20} />
  }

  const getTrendColor = (direction) => {
    if (direction === 'up') return '#ef4444'
    if (direction === 'down') return '#22c55e'
    return '#6b7280'
  }

  const toggleGPU = (gpu) => {
    if (gpu === 'all') {
      setSelectedGPUs(['all'])
    } else {
      const newSelection = selectedGPUs.filter(g => g !== 'all')
      if (newSelection.includes(gpu)) {
        const filtered = newSelection.filter(g => g !== gpu)
        setSelectedGPUs(filtered.length === 0 ? ['all'] : filtered)
      } else {
        setSelectedGPUs([...newSelection, gpu])
      }
    }
  }

  if (loading) {
    return (
      <div className="metrics-container">
        <div className="loading-state">
          <div className="spinner-large"></div>
          <p>Carregando métricas...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="metrics-container">
      {/* Header */}
      <div className="metrics-header">
        <div>
          <h1 className="metrics-title"><BarChart3 size={28} style={{display: 'inline', verticalAlign: 'middle', marginRight: '12px'}} /> Métricas de GPU</h1>
          <p className="metrics-subtitle">Análise de preços em tempo real da Vast.ai</p>
        </div>
        {agentStatus && (
          <div className="agent-status-badge">
            <span className={`status-dot ${agentStatus.running ? 'status-active' : 'status-inactive'}`}></span>
            <span>{agentStatus.running ? 'Monitorando' : 'Parado'}</span>
            <span className="status-interval">• {agentStatus.interval_minutes}min</span>
          </div>
        )}
      </div>

      {/* Filtros Avançados */}
      <div className="filters-panel">
        <div className="filter-section">
          <label className="filter-label">GPUs</label>
          <div className="filter-chips">
            <button
              className={`filter-chip ${selectedGPUs.includes('all') ? 'active' : ''}`}
              onClick={() => toggleGPU('all')}
            >
              Todas
            </button>
            <button
              className={`filter-chip ${selectedGPUs.includes('RTX 4090') ? 'active' : ''}`}
              onClick={() => toggleGPU('RTX 4090')}
            >
              RTX 4090
            </button>
            <button
              className={`filter-chip ${selectedGPUs.includes('RTX 4080') ? 'active' : ''}`}
              onClick={() => toggleGPU('RTX 4080')}
            >
              RTX 4080
            </button>
          </div>
        </div>

        <div className="filter-section">
          <label className="filter-label">Período</label>
          <div className="filter-chips">
            {[1, 6, 24, 168].map(hours => (
              <button
                key={hours}
                className={`filter-chip ${timeRange === hours ? 'active' : ''}`}
                onClick={() => setTimeRange(hours)}
              >
                {hours === 1 ? '1h' : hours === 6 ? '6h' : hours === 24 ? '24h' : '7d'}
              </button>
            ))}
          </div>
        </div>

        <div className="filter-section">
          <label className="filter-label">Preço ($/h): ${priceRange[0].toFixed(2)} - ${priceRange[1].toFixed(2)}</label>
          <div className="filter-range">
            <input
              type="range"
              min="0"
              max="2"
              step="0.05"
              value={priceRange[0]}
              onChange={(e) => setPriceRange([parseFloat(e.target.value), priceRange[1]])}
            />
            <input
              type="range"
              min="0"
              max="2"
              step="0.05"
              value={priceRange[1]}
              onChange={(e) => setPriceRange([priceRange[0], parseFloat(e.target.value)])}
            />
          </div>
        </div>

        <div className="filter-section">
          <label className="filter-label">Min. Ofertas: {minOffers}</label>
          <input
            type="range"
            min="0"
            max="50"
            value={minOffers}
            onChange={(e) => setMinOffers(parseInt(e.target.value))}
            className="filter-slider"
          />
        </div>

        <div className="filter-section">
          <label className="filter-checkbox">
            <input
              type="checkbox"
              checked={showOnlyDrops}
              onChange={(e) => setShowOnlyDrops(e.target.checked)}
            />
            <span style={{display: 'flex', alignItems: 'center', gap: '6px'}}>Apenas Quedas de Preço <TrendingDown size={16} /></span>
          </label>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="stats-grid">
        {filteredSummary.map((gpu) => (
          <div key={gpu.gpu_name} className="stat-card">
            <div className="stat-card-header">
              <h3>{gpu.gpu_name}</h3>
              <div className="stat-trend" style={{ color: getTrendColor(gpu.trend_24h?.direction) }}>
                <span className="trend-icon">{getTrendIcon(gpu.trend_24h?.direction)}</span>
                {gpu.trend_24h?.change_percent !== null && (
                  <span className="trend-value">
                    {gpu.trend_24h.change_percent > 0 ? '+' : ''}
                    {gpu.trend_24h.change_percent.toFixed(1)}%
                  </span>
                )}
              </div>
            </div>

            <div className="stat-main-price">
              <div className="price-label">Preço Médio</div>
              <div className="price-value">{formatPrice(gpu.current.avg_price)}</div>
            </div>

            <div className="stat-price-range">
              <div className="price-range-item">
                <span className="range-label">Mínimo</span>
                <span className="range-value green">{formatPrice(gpu.current.min_price)}</span>
              </div>
              <div className="price-range-divider"></div>
              <div className="price-range-item">
                <span className="range-label">Máximo</span>
                <span className="range-value red">{formatPrice(gpu.current.max_price)}</span>
              </div>
            </div>

            <div className="stat-chart">
              <Line data={getChartData(gpu.gpu_name)} options={chartOptions} />
            </div>

            <div className="stat-footer">
              <div className="stat-footer-item">
                <span className="footer-icon"><Package size={18} /></span>
                <span className="footer-value">{gpu.current.total_offers}</span>
                <span className="footer-label">Ofertas</span>
              </div>
              <div className="stat-footer-item">
                <span className="footer-icon"><Cpu size={18} /></span>
                <span className="footer-value">{gpu.current.available_gpus}</span>
                <span className="footer-label">GPUs</span>
              </div>
              <div className="stat-footer-item">
                <span className="footer-icon"><BarChart3 size={18} /></span>
                <span className="footer-value">{formatPrice(gpu.current.median_price)}</span>
                <span className="footer-label">Mediana</span>
              </div>
            </div>

            <div className="stat-updated">
              Atualizado {formatTime(gpu.current.timestamp)}
            </div>
          </div>
        ))}
      </div>

      {filteredSummary.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon"><Search size={64} /></div>
          <h3>Nenhum resultado encontrado</h3>
          <p>Ajuste os filtros para ver os dados</p>
        </div>
      )}

      {/* Alertas */}
      {filteredAlerts.length > 0 && (
        <div className="alerts-section">
          <h2 className="section-title"><AlertTriangle size={22} style={{display: 'inline', verticalAlign: 'middle', marginRight: '8px'}} /> Alertas Recentes (24h)</h2>
          <div className="alerts-grid">
            {filteredAlerts.slice(0, 6).map((alert) => (
              <div key={alert.id} className={`alert-card ${alert.alert_type}`}>
                <div className="alert-header">
                  <span className="alert-gpu">{alert.gpu_name}</span>
                  <span className="alert-change" style={{
                    color: alert.alert_type === 'price_drop' ? '#22c55e' : '#ef4444'
                  }}>
                    {alert.change_percent > 0 ? '+' : ''}{alert.change_percent.toFixed(1)}%
                  </span>
                </div>
                <div className="alert-message">{alert.message}</div>
                <div className="alert-time">{formatTime(alert.timestamp)}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Histórico Completo */}
      <div className="history-section">
        <h2 className="section-title"><TrendingUp size={22} style={{display: 'inline', verticalAlign: 'middle', marginRight: '8px'}} /> Histórico Completo</h2>
        <div className="history-table-container">
          <table className="history-table">
            <thead>
              <tr>
                <th>GPU</th>
                <th>Data/Hora</th>
                <th>Preço Médio</th>
                <th>Mínimo</th>
                <th>Máximo</th>
                <th>Mediana</th>
                <th>Ofertas</th>
                <th>GPUs</th>
              </tr>
            </thead>
            <tbody>
              {history.slice(0, 50).map((record) => (
                <tr key={record.id}>
                  <td className="table-gpu">{record.gpu_name}</td>
                  <td className="table-time">{formatTime(record.timestamp)}</td>
                  <td className="table-price-main">{formatPrice(record.avg_price)}</td>
                  <td className="table-price green">{formatPrice(record.min_price)}</td>
                  <td className="table-price red">{formatPrice(record.max_price)}</td>
                  <td className="table-price">{formatPrice(record.median_price)}</td>
                  <td className="table-number">{record.total_offers}</td>
                  <td className="table-number">{record.available_gpus}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
