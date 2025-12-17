import { useState, useEffect, useMemo } from 'react'
import { Zap, Gauge, Rocket, Flame, Globe, MapPin, Package, Cpu, HardDrive, Network, Clock, DollarSign } from 'lucide-react'

const API_BASE = ''

// Speed tiers with enhanced info
const SPEED_TIERS = [
  {
    id: 'slow',
    name: 'Lentos',
    icon: Gauge,
    minSpeed: 100,
    maxSpeed: 500,
    color: '#ef4444',
    bgGradient: 'linear-gradient(135deg, #dc2626 0%, #991b1b 100%)',
    time: '~5 min',
    description: 'Menor velocidade & Custo'
  },
  {
    id: 'medium',
    name: 'Médio',
    icon: Zap,
    minSpeed: 500,
    maxSpeed: 2000,
    color: '#f59e0b',
    bgGradient: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
    time: '~1-2 min',
    description: 'Balanço entre velocidade e custo'
  },
  {
    id: 'fast',
    name: 'Rápida',
    icon: Rocket,
    minSpeed: 2000,
    maxSpeed: 4000,
    color: '#22c55e',
    bgGradient: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
    time: '~30s',
    description: 'Alta velocidade & Deploy rápido'
  },
  {
    id: 'ultra',
    name: 'Hiper',
    icon: Flame,
    minSpeed: 4000,
    maxSpeed: 99999,
    color: '#a855f7',
    bgGradient: 'linear-gradient(135deg, #a855f7 0%, #9333ea 100%)',
    time: '~15s',
    description: 'Máxima velocidade disponível'
  },
]

// Region options
const REGIONS = [
  { id: 'US', name: 'EUA', flag: '🇺🇸', continent: 'north-america' },
  { id: 'EU', name: 'Europa', flag: '🇪🇺', continent: 'europe' },
  { id: 'ASIA', name: 'Ásia', flag: '🌏', continent: 'asia' },
  { id: 'SA', name: 'América do Sul', flag: '🌎', continent: 'south-america' },
  { id: 'global', name: 'Global', flag: '🌐', continent: 'global' },
]

// GPU options
const GPU_OPTIONS = [
  'RTX 4090',
  'RTX 4080',
  'RTX 3090',
  'RTX 3080',
  'RTX A6000',
  'RTX A5000',
  'A100',
  'H100',
]

export default function DeployWizard2({ snapshots, machines, onRefresh }) {
  const [selectedRegion, setSelectedRegion] = useState('global')
  const [selectedSpeed, setSelectedSpeed] = useState('fast')
  const [selectedGpu, setSelectedGpu] = useState('RTX 4090')
  const [offers, setOffers] = useState([])
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [selectedSnapshot, setSelectedSnapshot] = useState(snapshots?.[0] || null)
  const [latencies, setLatencies] = useState({})
  const [loadingLatency, setLoadingLatency] = useState(false)
  const [balance, setBalance] = useState(null)
  const [loadingBalance, setLoadingBalance] = useState(false)

  useEffect(() => {
    if (snapshots?.length > 0 && !selectedSnapshot) {
      setSelectedSnapshot(snapshots[0])
    }
  }, [snapshots])

  // Fetch latency on mount
  useEffect(() => {
    const fetchLatency = async () => {
      setLoadingLatency(true)
      try {
        const res = await fetch(`${API_BASE}/api/latency`, { credentials: 'include' })
        const data = await res.json()
        setLatencies(data)
      } catch (e) {
        console.error('Failed to fetch latency:', e)
      }
      setLoadingLatency(false)
    }
    fetchLatency()
  }, [])

  // Fetch balance on mount
  useEffect(() => {
    const fetchBalance = async () => {
      setLoadingBalance(true)
      try {
        const res = await fetch(`${API_BASE}/api/balance`, { credentials: 'include' })
        const data = await res.json()
        setBalance(data)
      } catch (e) {
        console.error('Failed to fetch balance:', e)
      }
      setLoadingBalance(false)
    }
    fetchBalance()
  }, [])

  // Fetch offers based on current filters
  const fetchOffers = async () => {
    setLoading(true)

    let params = new URLSearchParams()
    const speedTier = SPEED_TIERS.find(t => t.id === selectedSpeed)
    params.append('inet_down', speedTier?.minSpeed || 500)
    params.append('disk_space', 50)

    if (selectedGpu) {
      params.append('gpu_name', selectedGpu)
    }
    if (selectedRegion !== 'global') {
      params.append('region', selectedRegion)
    }

    params.append('limit', 100)

    try {
      const res = await fetch(`${API_BASE}/api/offers?${params}`, { credentials: 'include' })
      const data = await res.json()
      setOffers(data.offers || [])
    } catch (e) {
      console.error('Failed to fetch offers:', e)
    }
    setLoading(false)
  }

  useEffect(() => {
    fetchOffers()
  }, [selectedRegion, selectedSpeed, selectedGpu])

  // Group offers by speed tier
  const offersByTier = useMemo(() => {
    const grouped = {}
    SPEED_TIERS.forEach(tier => {
      grouped[tier.id] = offers.filter(o =>
        o.inet_down >= tier.minSpeed && o.inet_down < tier.maxSpeed
      )
    })
    return grouped
  }, [offers])

  // Get detailed stats for each tier
  const tierStats = useMemo(() => {
    const stats = {}
    SPEED_TIERS.forEach(tier => {
      const tierOffers = offersByTier[tier.id] || []
      if (tierOffers.length > 0) {
        const prices = tierOffers.map(o => o.dph_total).sort((a, b) => a - b)
        const speeds = tierOffers.map(o => o.inet_down).sort((a, b) => a - b)
        const rams = tierOffers.map(o => o.cpu_ram).sort((a, b) => a - b)
        const cpuCores = tierOffers.map(o => o.cpu_cores_effective || o.cpu_cores).sort((a, b) => a - b)

        stats[tier.id] = {
          count: tierOffers.length,
          minPrice: prices[0],
          maxPrice: prices[prices.length - 1],
          avgPrice: prices.reduce((a, b) => a + b, 0) / prices.length,
          minSpeed: speeds[0],
          maxSpeed: speeds[speeds.length - 1],
          avgRam: rams.reduce((a, b) => a + b, 0) / rams.length,
          avgCpu: cpuCores.reduce((a, b) => a + b, 0) / cpuCores.length,
          cheapestOffer: tierOffers[0]
        }
      }
    })
    return stats
  }, [offersByTier])

  const handleCreate = async (speed = selectedSpeed) => {
    const tierOffers = offersByTier[speed] || []
    if (tierOffers.length === 0) {
      alert('Nenhuma oferta disponível para este tier')
      return
    }

    // Sort by price and pick cheapest
    const bestOffer = [...tierOffers].sort((a, b) => a.dph_total - b.dph_total)[0]

    setCreating(true)
    try {
      const res = await fetch(`${API_BASE}/api/instances`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          offer_id: bestOffer.id,
          snapshot_id: selectedSnapshot?.id,
          hot_start: false
        }),
        credentials: 'include'
      })
      const data = await res.json()
      if (data.success) {
        onRefresh?.()
      } else {
        alert(data.error || 'Falha ao criar instância')
      }
    } catch (e) {
      alert('Erro de conexão')
    }
    setCreating(false)
  }

  return (
    <div className="deploy-wizard-v2">
      {/* Header with title and balance */}
      <div className="deploy-v2-header">
        <div className="header-title-section">
          <h2 className="deploy-v2-title">Deploy 2 Migrate</h2>
          {balance && (
            <div className="balance-display">
              <DollarSign size={18} />
              <span className="balance-label">Saldo Vast.ai:</span>
              <span className="balance-amount">${balance.credit?.toFixed(2) || '0.00'}</span>
            </div>
          )}
        </div>
      </div>

      {/* Region tabs */}
      <div className="deploy-v2-tabs">
        {REGIONS.map(region => {
          const latencyInfo = latencies[region.id]
          const latencyMs = latencyInfo?.latency
          const latencyClass = latencyMs ? (latencyMs < 50 ? 'good' : latencyMs < 150 ? 'medium' : 'bad') : ''

          return (
            <button
              key={region.id}
              className={`deploy-v2-tab ${selectedRegion === region.id ? 'active' : ''}`}
              onClick={() => setSelectedRegion(region.id)}
            >
              <span className="tab-flag">{region.flag}</span>
              <span className="tab-name">{region.name}</span>
              {latencyMs && (
                <span className={`tab-latency latency-${latencyClass}`}>
                  {Math.round(latencyMs)}ms
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* World map visualization */}
      <div className="deploy-v2-map">
        <div className="map-container">
          <Globe className="map-icon" size={48} />
          <div className="map-label">
            <MapPin size={16} />
            <span>Região: {REGIONS.find(r => r.id === selectedRegion)?.name}</span>
          </div>
        </div>
      </div>

      {/* GPU Selector */}
      <div className="deploy-v2-gpu-selector">
        <label className="gpu-label">Qualquer GPU</label>
        <select
          className="gpu-select"
          value={selectedGpu}
          onChange={e => setSelectedGpu(e.target.value)}
        >
          {GPU_OPTIONS.map(gpu => (
            <option key={gpu} value={gpu}>{gpu}</option>
          ))}
        </select>
      </div>

      {/* Speed Tier Cards */}
      <div className="deploy-v2-section">
        <h3 className="section-title-v2">Velocidade & Custo (Quanto de Tempo de Reinstalação)</h3>

        <div className="speed-cards-v2">
          {SPEED_TIERS.map(tier => {
            const Icon = tier.icon
            const stats = tierStats[tier.id]
            const isSelected = selectedSpeed === tier.id

            return (
              <div
                key={tier.id}
                className={`speed-card-v2 ${isSelected ? 'selected' : ''} ${!stats ? 'disabled' : ''}`}
                onClick={() => stats && setSelectedSpeed(tier.id)}
                style={{ '--tier-color': tier.color }}
              >
                <div className="card-header-v2">
                  <Icon size={28} style={{ color: tier.color }} />
                  <h4 className="card-title-v2">{tier.name}</h4>
                </div>

                {stats ? (
                  <>
                    <div className="card-stats-v2">
                      <div className="stat-row-v2">
                        <Network size={16} />
                        <span className="stat-label">Velocidade:</span>
                        <span className="stat-value">{Math.round(stats.minSpeed)}-{Math.round(stats.maxSpeed)} Mbps</span>
                      </div>

                      <div className="stat-row-v2 highlight">
                        <DollarSign size={16} />
                        <span className="stat-label">Preço:</span>
                        <span className="stat-value price">${stats.minPrice.toFixed(2)} - ${stats.maxPrice.toFixed(2)}/h</span>
                      </div>

                      <div className="stat-row-v2">
                        <Clock size={16} />
                        <span className="stat-label">Tempo:</span>
                        <span className="stat-value" style={{ color: tier.color }}>{tier.time}</span>
                      </div>

                      <div className="stat-divider-v2"></div>

                      <div className="stat-row-v2">
                        <Cpu size={16} />
                        <span className="stat-label">CPU:</span>
                        <span className="stat-value">{Math.round(stats.avgCpu)} cores</span>
                      </div>

                      <div className="stat-row-v2">
                        <HardDrive size={16} />
                        <span className="stat-label">RAM:</span>
                        <span className="stat-value">{Math.round(stats.avgRam)} GB</span>
                      </div>

                      <div className="stat-row-v2">
                        <Package size={16} />
                        <span className="stat-label">Disponíveis:</span>
                        <span className="stat-value">{stats.count} máquinas</span>
                      </div>
                    </div>

                    <div className="card-description-v2">{tier.description}</div>
                  </>
                ) : (
                  <div className="card-empty-v2">
                    <p>Sem ofertas disponíveis</p>
                    <p className="empty-hint">Tente outra região ou GPU</p>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Action buttons */}
      <div className="deploy-v2-actions">
        <div className="action-buttons-row">
          <button
            className="btn-action-v2 btn-secondary-v2"
            onClick={() => handleCreate('slow')}
            disabled={creating || !tierStats['slow']}
          >
            <Clock size={18} />
            Continue Slow
          </button>

          <button
            className="btn-action-v2 btn-primary-v2"
            onClick={() => handleCreate('fast')}
            disabled={creating || !tierStats['fast']}
          >
            <Rocket size={18} />
            Start Fast
          </button>

          <button
            className="btn-action-v2 btn-secondary-v2"
            disabled
          >
            <Network size={18} />
            Transfer
          </button>
        </div>

        <button
          className="btn-create-v2"
          onClick={() => handleCreate(selectedSpeed)}
          disabled={creating || !tierStats[selectedSpeed]}
        >
          {creating ? (
            <>
              <div className="spinner-sm"></div>
              Criando máquina...
            </>
          ) : (
            <>
              <Package size={20} />
              Criar Máquina e Restore
            </>
          )}
        </button>

        <div className="deploy-v2-info">
          {selectedSnapshot && (
            <p className="info-text">
              <strong>Snapshot selecionado:</strong> {selectedSnapshot.short_id} • {new Date(selectedSnapshot.time).toLocaleString('pt-BR')}
            </p>
          )}
          {tierStats[selectedSpeed] && (
            <p className="info-text">
              <strong>Melhor preço ({SPEED_TIERS.find(t => t.id === selectedSpeed)?.name}):</strong> ${tierStats[selectedSpeed].minPrice.toFixed(3)}/h
            </p>
          )}
        </div>
      </div>

      {loading && (
        <div className="deploy-v2-loading">
          <div className="spinner-large"></div>
          <p>Buscando ofertas...</p>
        </div>
      )}
    </div>
  )
}
