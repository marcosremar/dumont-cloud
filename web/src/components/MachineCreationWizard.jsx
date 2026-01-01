import { useState, useEffect, useMemo } from 'react'

const API_BASE = ''

// Speed tiers based on inet_down
const SPEED_TIERS = [
  { id: 'slow', name: 'Lenta', minSpeed: 100, maxSpeed: 500, icon: 'stop', color: '#f85149', time: '~5 min' },
  { id: 'medium', name: 'Media', minSpeed: 500, maxSpeed: 2000, icon: 'bolt', color: '#d29922', time: '~1-2 min' },
  { id: 'fast', name: 'Rapida', minSpeed: 2000, maxSpeed: 4000, icon: 'forward', color: '#3fb950', time: '~30s' },
  { id: 'ultra', name: 'Ultra', minSpeed: 4000, maxSpeed: 99999, icon: 'fire', color: '#a371f7', time: '~15s' },
]

// GPU options
const GPU_OPTIONS = [
  'RTX 4090',
  'RTX 4080',
  'RTX 3090',
  'RTX 3080',
  'RTX A6000',
  'RTX A5000',
  'RTX A4000',
  'A100',
  'H100',
]

// Disk options
const DISK_OPTIONS = [30, 50, 100, 200, 500]

// Region options
const REGIONS = [
  { id: 'global', name: 'Global', icon: 'globe', flag: null },
  { id: 'US', name: 'US', icon: 'flag', flag: 'us' },
  { id: 'EU', name: 'Europa', icon: 'flag', flag: 'eu' },
  { id: 'ASIA', name: 'Asia', icon: 'flag', flag: 'asia' },
]

export default function MachineCreationWizard({ snapshots, machines, onRefresh }) {
  const [tab, setTab] = useState('new') // 'new' or 'existing'
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [offers, setOffers] = useState([])
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [hotStartEnabled, setHotStartEnabled] = useState(false)

  // Wizard filters
  const [selectedRegion, setSelectedRegion] = useState('global')
  const [selectedSpeed, setSelectedSpeed] = useState('fast')
  const [selectedGpu, setSelectedGpu] = useState('')
  const [selectedDisk, setSelectedDisk] = useState(50)
  const [selectedSnapshot, setSelectedSnapshot] = useState(snapshots?.[0] || null)

  // Advanced filters
  const [advancedFilters, setAdvancedFilters] = useState({
    num_gpus: 1,
    gpu_ram: 16,
    cpu_cores: 4,
    cpu_ram: 16,
    disk_space: 50,
    inet_down: 500,
    inet_up: 100,
    dph_total: 2.0,
    cuda_max_good: '12.0',
    reliability2: 0.95,
    verified: true,
    static_ip: false,
    direct_port_count: 1,
  })

  // Existing machine selection
  const [selectedMachine, setSelectedMachine] = useState(null)

  // Latency state
  const [latencies, setLatencies] = useState({})
  const [loadingLatency, setLoadingLatency] = useState(false)

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

  // Fetch offers based on current filters
  const fetchOffers = async () => {
    setLoading(true)

    let params = new URLSearchParams()

    if (showAdvanced) {
      // Use advanced filters
      Object.entries(advancedFilters).forEach(([key, value]) => {
        if (value !== '' && value !== null) {
          params.append(key, value)
        }
      })
    } else {
      // Use wizard filters
      const speedTier = SPEED_TIERS.find(t => t.id === selectedSpeed)
      params.append('inet_down', speedTier?.minSpeed || 500)
      params.append('disk_space', selectedDisk)

      if (selectedGpu) {
        params.append('gpu_name', selectedGpu)
      }
      if (selectedRegion !== 'global') {
        params.append('region', selectedRegion)
      }
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
  }, [selectedRegion, selectedSpeed, selectedGpu, selectedDisk, showAdvanced])

  // Group offers by speed tier for display
  const offersByTier = useMemo(() => {
    const grouped = {}
    SPEED_TIERS.forEach(tier => {
      grouped[tier.id] = offers.filter(o =>
        o.inet_down >= tier.minSpeed && o.inet_down < tier.maxSpeed
      )
    })
    return grouped
  }, [offers])

  // Get price range for each tier
  const tierPrices = useMemo(() => {
    const prices = {}
    SPEED_TIERS.forEach(tier => {
      const tierOffers = offersByTier[tier.id] || []
      if (tierOffers.length > 0) {
        const sortedPrices = tierOffers.map(o => o.dph_total).sort((a, b) => a - b)
        prices[tier.id] = {
          min: sortedPrices[0],
          max: sortedPrices[sortedPrices.length - 1],
          count: tierOffers.length
        }
      }
    })
    return prices
  }, [offersByTier])

  const handleCreate = async () => {
    // CRITICAL FIX: Prevent multiple simultaneous executions
    // This fixes the bug where rapid clicks create multiple machines
    if (creating) {
      console.warn('Machine creation already in progress, ignoring duplicate click');
      return;
    }

    setCreating(true);

    if (tab === 'new') {
      // Find best offer for selected tier
      const tierOffers = offersByTier[selectedSpeed] || []
      if (tierOffers.length === 0) {
        alert('Nenhuma oferta disponivel para este tier')
        setCreating(false);
        return
      }

      // Sort by price and pick cheapest
      const bestOffer = [...tierOffers].sort((a, b) => a.dph_total - b.dph_total)[0]
      try {
        const res = await fetch(`${API_BASE}/api/instances`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            offer_id: bestOffer.id,
            snapshot_id: selectedSnapshot?.id,
            hot_start: hotStartEnabled
          }),
          credentials: 'include'
        })
        const data = await res.json()
        if (data.success) {
          onRefresh?.()
        } else {
          alert(data.error || 'Falha ao criar instancia')
        }
      } catch (e) {
        alert('Erro de conexao')
      }
      setCreating(false)
    } else {
      // Restore to existing machine
      if (!selectedMachine) {
        alert('Selecione uma maquina')
        setCreating(false);
        return
      }
      try {
        const res = await fetch(`${API_BASE}/api/instances/${selectedMachine.id}/restore`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ snapshot_id: selectedSnapshot?.id }),
          credentials: 'include'
        })
        const data = await res.json()
        if (!data.success) {
          alert(data.error || 'Falha ao restaurar')
        }
      } catch (e) {
        alert('Erro de conexao')
      }
      setCreating(false)
    }
  }

  const renderSpeedIcon = (iconName, color) => {
    const icons = {
      stop: (
        <svg viewBox="0 0 24 24" fill={color} width="28" height="28">
          <circle cx="12" cy="12" r="10"/>
        </svg>
      ),
      bolt: (
        <svg viewBox="0 0 24 24" fill={color} width="28" height="28">
          <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
        </svg>
      ),
      forward: (
        <svg viewBox="0 0 24 24" fill={color} width="28" height="28">
          <path d="M13 19V5l7 7-7 7zm-9 0V5l7 7-7 7z"/>
        </svg>
      ),
      fire: (
        <svg viewBox="0 0 24 24" fill={color} width="28" height="28">
          <path d="M12 23c-4.97 0-9-3.58-9-8 0-2.52.74-4.83 2-6.83 1.73 2.5 4.28 3.83 5 3.83.73 0 1-1 1-1s.55 1 1.5 1.5c.67.35 1.5.5 1.5.5s0-3-2-5c2.28.54 4.56 2.28 5.86 5.17C18.82 14.68 19 16.31 19 17c0 3.87-3.13 6-7 6z"/>
        </svg>
      ),
    }
    return icons[iconName] || null
  }

  return (
    <div className="deploy-wizard">
      <div className="deploy-header">
        <h3>Deploy</h3>
      </div>

      {/* Tabs */}
      <div className="deploy-tabs">
        <button
          className={`deploy-tab ${tab === 'new' ? 'active' : ''}`}
          onClick={() => setTab('new')}
        >
          Nova Maquina
        </button>
        <button
          className={`deploy-tab ${tab === 'existing' ? 'active' : ''}`}
          onClick={() => setTab('existing')}
        >
          Maquina Existente
        </button>
      </div>

      {tab === 'new' ? (
        <div className="deploy-content">
          {/* Advanced toggle */}
          <button
            className="advanced-toggle"
            onClick={() => setShowAdvanced(!showAdvanced)}
          >
            <span className="filter-icon">
              <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
                <path d="M3 4h18l-7 8v8l-4-2v-6L3 4z"/>
              </svg>
            </span>
            {showAdvanced ? 'Modo simples' : 'Mostrar filtros avancados'}
          </button>

          {!showAdvanced ? (
            /* WIZARD MODE */
            <>
              {/* Region selector */}
              <div className="filter-section">
                <label className="filter-label">Regiao {loadingLatency && <span className="latency-loading">(medindo latencia...)</span>}</label>
                <div className="region-buttons">
                  {REGIONS.map(region => {
                    const latencyInfo = latencies[region.id]
                    const latencyMs = latencyInfo?.latency
                    const latencyClass = latencyMs ? (latencyMs < 50 ? 'latency-good' : latencyMs < 150 ? 'latency-medium' : 'latency-bad') : ''
                    return (
                      <button
                        key={region.id}
                        className={`region-btn ${selectedRegion === region.id ? 'selected' : ''}`}
                        onClick={() => setSelectedRegion(region.id)}
                      >
                        <span className="region-flag">
                          {region.flag === 'us' && '🇺🇸'}
                          {region.flag === 'eu' && '🇪🇺'}
                          {region.flag === 'asia' && '🌏'}
                          {region.id === 'global' && '🌐'}
                        </span>
                        <span className="region-name">{region.name}</span>
                        {latencyMs && (
                          <span className={`region-latency ${latencyClass}`}>
                            {Math.round(latencyMs)}ms
                          </span>
                        )}
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Speed selector */}
              <div className="filter-section">
                <label className="filter-label">Velocidade (mais rapido = mais caro)</label>
                <div className="speed-cards">
                  {SPEED_TIERS.map(tier => {
                    const priceInfo = tierPrices[tier.id]
                    return (
                      <div
                        key={tier.id}
                        className={`speed-card ${selectedSpeed === tier.id ? 'selected' : ''}`}
                        onClick={() => setSelectedSpeed(tier.id)}
                        style={{ '--tier-color': tier.color }}
                      >
                        <div className="speed-icon">
                          {renderSpeedIcon(tier.icon, tier.color)}
                        </div>
                        <div className="speed-name">{tier.name}</div>
                        <div className="speed-range">{tier.minSpeed}-{tier.maxSpeed === 99999 ? '4000+' : tier.maxSpeed} Mbps</div>
                        <div className="speed-time" style={{ color: tier.color }}>{tier.time}</div>
                        {priceInfo ? (
                          <div className="speed-price">
                            ${priceInfo.min.toFixed(2)} - ${priceInfo.max.toFixed(2)}/h
                          </div>
                        ) : (
                          <div className="speed-price muted">Sem ofertas</div>
                        )}
                        <div className="speed-count">{priceInfo?.count || 0} maquinas</div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* GPU and Disk selectors */}
              <div className="filter-row">
                <div className="filter-section half">
                  <label className="filter-label">GPU</label>
                  <select
                    className="form-select"
                    value={selectedGpu}
                    onChange={e => setSelectedGpu(e.target.value)}
                  >
                    <option value="">Qualquer GPU</option>
                    {GPU_OPTIONS.map(gpu => (
                      <option key={gpu} value={gpu}>{gpu}</option>
                    ))}
                  </select>
                </div>
                <div className="filter-section half">
                  <label className="filter-label">Disco Minimo</label>
                  <select
                    className="form-select"
                    value={selectedDisk}
                    onChange={e => setSelectedDisk(Number(e.target.value))}
                  >
                    {DISK_OPTIONS.map(disk => (
                      <option key={disk} value={disk}>{disk} GB</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Offer preview */}
              {selectedGpu && offersByTier[selectedSpeed]?.length > 0 && (
                <div className="offer-preview">
                  Selecione uma GPU para ver ofertas
                </div>
              )}

              {!selectedGpu && (
                <div className="offer-hint">
                  Selecione uma GPU para ver ofertas
                </div>
              )}
            </>
          ) : (
            /* ADVANCED MODE */
            <div className="advanced-filters">
              <div className="advanced-grid">
                <div className="form-group">
                  <label className="form-label">Num GPUs</label>
                  <input
                    type="number"
                    className="form-input"
                    value={advancedFilters.num_gpus}
                    onChange={e => setAdvancedFilters({...advancedFilters, num_gpus: e.target.value})}
                    min="1"
                    max="8"
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">GPU RAM (GB)</label>
                  <input
                    type="number"
                    className="form-input"
                    value={advancedFilters.gpu_ram}
                    onChange={e => setAdvancedFilters({...advancedFilters, gpu_ram: e.target.value})}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">CPU Cores</label>
                  <input
                    type="number"
                    className="form-input"
                    value={advancedFilters.cpu_cores}
                    onChange={e => setAdvancedFilters({...advancedFilters, cpu_cores: e.target.value})}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">CPU RAM (GB)</label>
                  <input
                    type="number"
                    className="form-input"
                    value={advancedFilters.cpu_ram}
                    onChange={e => setAdvancedFilters({...advancedFilters, cpu_ram: e.target.value})}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Disco (GB)</label>
                  <input
                    type="number"
                    className="form-input"
                    value={advancedFilters.disk_space}
                    onChange={e => setAdvancedFilters({...advancedFilters, disk_space: e.target.value})}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Download (Mbps)</label>
                  <input
                    type="number"
                    className="form-input"
                    value={advancedFilters.inet_down}
                    onChange={e => setAdvancedFilters({...advancedFilters, inet_down: e.target.value})}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Upload (Mbps)</label>
                  <input
                    type="number"
                    className="form-input"
                    value={advancedFilters.inet_up}
                    onChange={e => setAdvancedFilters({...advancedFilters, inet_up: e.target.value})}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Max $/hora</label>
                  <input
                    type="number"
                    className="form-input"
                    value={advancedFilters.dph_total}
                    onChange={e => setAdvancedFilters({...advancedFilters, dph_total: e.target.value})}
                    step="0.01"
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">CUDA Min</label>
                  <input
                    type="text"
                    className="form-input"
                    value={advancedFilters.cuda_max_good}
                    onChange={e => setAdvancedFilters({...advancedFilters, cuda_max_good: e.target.value})}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Reliability Min</label>
                  <input
                    type="number"
                    className="form-input"
                    value={advancedFilters.reliability2}
                    onChange={e => setAdvancedFilters({...advancedFilters, reliability2: e.target.value})}
                    step="0.01"
                    min="0"
                    max="1"
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Direct Ports</label>
                  <input
                    type="number"
                    className="form-input"
                    value={advancedFilters.direct_port_count}
                    onChange={e => setAdvancedFilters({...advancedFilters, direct_port_count: e.target.value})}
                  />
                </div>
              </div>

              <div className="checkbox-row">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={advancedFilters.verified}
                    onChange={e => setAdvancedFilters({...advancedFilters, verified: e.target.checked})}
                  />
                  Apenas verificados
                </label>

                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={advancedFilters.static_ip}
                    onChange={e => setAdvancedFilters({...advancedFilters, static_ip: e.target.checked})}
                  />
                  IP Estatico
                </label>
              </div>

              <button className="btn" onClick={fetchOffers}>
                {loading ? 'Buscando...' : 'Buscar ofertas'}
              </button>

              {/* Advanced offers table */}
              {offers.length > 0 && (
                <div className="advanced-offers">
                  <table className="offers-table">
                    <thead>
                      <tr>
                        <th>GPU</th>
                        <th>VRAM</th>
                        <th>CPU</th>
                        <th>RAM</th>
                        <th>Disco</th>
                        <th>DL</th>
                        <th>UL</th>
                        <th>$/h</th>
                        <th>Regiao</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {offers.slice(0, 30).map(offer => (
                        <tr key={offer.id}>
                          <td>{offer.gpu_name}</td>
                          <td>{Math.round(offer.gpu_ram / 1024)} GB</td>
                          <td>{offer.cpu_cores}</td>
                          <td>{Math.round(offer.cpu_ram / 1024)} GB</td>
                          <td>{Math.round(offer.disk_space)} GB</td>
                          <td>{Math.round(offer.inet_down)}</td>
                          <td>{Math.round(offer.inet_up)}</td>
                          <td>${offer.dph_total?.toFixed(3)}</td>
                          <td>{offer.geolocation?.split(',')[0] || '-'}</td>
                          <td>
                            <button
                              className="btn btn-sm btn-primary"
                              onClick={() => {
                                // Direct create with this offer
                              }}
                            >
                              Usar
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Hot Start toggle */}
          <div className="hotstart-toggle">
            <div className="hotstart-info">
              <span className="hotstart-icon">🔥</span>
              <div>
                <div className="hotstart-title">Hot Start + Migrate</div>
                <div className="hotstart-desc">Inicie rapido, economize depois</div>
              </div>
            </div>
            <label className="switch">
              <input
                type="checkbox"
                checked={hotStartEnabled}
                onChange={e => setHotStartEnabled(e.target.checked)}
              />
              <span className="slider"></span>
            </label>
          </div>

          {/* Create button */}
          <button
            className="btn btn-primary btn-create"
            onClick={handleCreate}
            disabled={creating || loading}
          >
            {creating ? 'Criando...' : 'Criar Maquina + Restore'}
          </button>
        </div>
      ) : (
        /* EXISTING MACHINE TAB */
        <div className="deploy-content">
          <div className="filter-section">
            <label className="filter-label">Selecione uma maquina</label>
            {machines?.length === 0 ? (
              <div className="empty-state">Nenhuma maquina ativa</div>
            ) : (
              <div className="machine-select-list">
                {machines?.map(machine => (
                  <div
                    key={machine.id}
                    className={`machine-select-item ${selectedMachine?.id === machine.id ? 'selected' : ''}`}
                    onClick={() => setSelectedMachine(machine)}
                  >
                    <div className="machine-select-gpu">{machine.gpu_name}</div>
                    <div className="machine-select-meta">
                      <span className={`badge badge-${machine.actual_status === 'running' ? 'success' : 'warning'}`}>
                        {machine.actual_status}
                      </span>
                      {machine.ssh_host && (
                        <span className="machine-ssh">{machine.ssh_host}:{machine.ssh_port}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <button
            className="btn btn-primary btn-create"
            onClick={handleCreate}
            disabled={creating || !selectedMachine || selectedMachine.actual_status !== 'running'}
          >
            {creating ? 'Restaurando...' : 'Restaurar Snapshot'}
          </button>
        </div>
      )}
    </div>
  )
}
