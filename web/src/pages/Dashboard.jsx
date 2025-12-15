import { useState, useEffect, useCallback } from 'react'
import DeployWizard from '../components/DeployWizard'

const API_BASE = ''

// Tree Node component for expandable directory tree
function TreeNode({ node, level = 0, formatSize, expanded, onToggle }) {
  const isFolder = node.type === 'dir' || node.children
  const hasChildren = node.children && node.children.length > 0
  const isExpanded = expanded[node.path]

  return (
    <div className="tree-node">
      <div
        className={`tree-item ${isFolder ? 'tree-folder' : 'tree-file'}`}
        style={{ paddingLeft: `${level * 16 + 8}px` }}
        onClick={() => hasChildren && onToggle(node.path)}
      >
        {isFolder && (
          <span className="tree-toggle">
            {hasChildren ? (isExpanded ? '▼' : '▶') : ''}
          </span>
        )}
        <span className="tree-icon">
          {isFolder ? (
            <svg viewBox="0 0 24 24" fill="#d29922" width="16" height="16">
              <path d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/>
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" fill="#8b949e" width="16" height="16">
              <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11z"/>
            </svg>
          )}
        </span>
        <span className="tree-name">{node.name}</span>
        {node.size > 0 && (
          <span className="tree-size">{formatSize(node.size)}</span>
        )}
        {node.mtime && (
          <span className="tree-mtime">{node.mtime}</span>
        )}
      </div>
      {isExpanded && hasChildren && (
        <div className="tree-children">
          {node.children.map((child, idx) => (
            <TreeNode
              key={child.path || idx}
              node={child}
              level={level + 1}
              formatSize={formatSize}
              expanded={expanded}
              onToggle={onToggle}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default function Dashboard() {
  const [snapshots, setSnapshots] = useState([])
  const [machines, setMachines] = useState([])
  const [selectedSnapshot, setSelectedSnapshot] = useState(null)
  const [loading, setLoading] = useState({ snapshots: true, machines: true })
  const [restoring, setRestoring] = useState(null)

  // Modal state for folder browser
  const [showModal, setShowModal] = useState(false)
  const [modalSnapshot, setModalSnapshot] = useState(null)
  const [treeData, setTreeData] = useState([])
  const [loadingTree, setLoadingTree] = useState(false)
  const [expandedNodes, setExpandedNodes] = useState({})

  // Machine lock state (stored in localStorage)
  const [lockedMachines, setLockedMachines] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('lockedMachines') || '[]')
    } catch {
      return []
    }
  })

  // Save locked machines to localStorage
  useEffect(() => {
    localStorage.setItem('lockedMachines', JSON.stringify(lockedMachines))
  }, [lockedMachines])

  const fetchData = useCallback(async () => {
    // Fetch snapshots
    fetch(`${API_BASE}/api/snapshots`, { credentials: 'include' })
      .then(res => res.json())
      .then(data => {
        const snaps = data.deduplicated || data.snapshots || []
        setSnapshots(snaps)
        if (snaps.length > 0 && !selectedSnapshot) {
          setSelectedSnapshot(snaps[0])
        }
        setLoading(prev => ({ ...prev, snapshots: false }))
      })
      .catch(() => setLoading(prev => ({ ...prev, snapshots: false })))

    // Fetch my machines
    fetch(`${API_BASE}/api/machines`, { credentials: 'include' })
      .then(res => res.json())
      .then(data => {
        setMachines(data.instances || [])
        setLoading(prev => ({ ...prev, machines: false }))
      })
      .catch(() => setLoading(prev => ({ ...prev, machines: false })))
  }, [selectedSnapshot])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [fetchData])

  // Fetch folder tree when opening modal
  const fetchFolderTree = async (snapshotId) => {
    setLoadingTree(true)
    setTreeData([])
    try {
      const res = await fetch(`${API_BASE}/api/snapshots/${snapshotId}/tree`, { credentials: 'include' })
      const data = await res.json()
      if (data.tree) {
        setTreeData(data.tree)
        // Expand first level by default
        const firstLevelExpanded = {}
        data.tree.forEach(node => {
          if (node.type === 'dir' || node.children) {
            firstLevelExpanded[node.path] = true
          }
        })
        setExpandedNodes(firstLevelExpanded)
      } else if (data.folders) {
        // Fallback to old format if tree not available
        const converted = data.folders.map(f => ({
          name: f.name,
          path: f.path,
          type: 'dir',
          size: f.size,
          children: []
        }))
        setTreeData(converted)
      }
    } catch (e) {
      console.error('Failed to fetch tree:', e)
      setTreeData([])
    }
    setLoadingTree(false)
  }

  const handleSnapshotClick = (snap) => {
    setSelectedSnapshot(snap)
  }

  const handleViewFolders = async (snap, e) => {
    e.stopPropagation()
    setModalSnapshot(snap)
    setShowModal(true)
    await fetchFolderTree(snap.short_id)
  }

  const closeModal = () => {
    setShowModal(false)
    setModalSnapshot(null)
    setTreeData([])
    setExpandedNodes({})
  }

  const toggleNode = (path) => {
    setExpandedNodes(prev => ({
      ...prev,
      [path]: !prev[path]
    }))
  }

  const expandAll = () => {
    const allExpanded = {}
    const expandRecursive = (nodes) => {
      nodes.forEach(node => {
        if (node.type === 'dir' || node.children) {
          allExpanded[node.path] = true
          if (node.children) expandRecursive(node.children)
        }
      })
    }
    expandRecursive(treeData)
    setExpandedNodes(allExpanded)
  }

  const collapseAll = () => {
    setExpandedNodes({})
  }

  const toggleMachineLock = (machineId) => {
    setLockedMachines(prev =>
      prev.includes(machineId)
        ? prev.filter(id => id !== machineId)
        : [...prev, machineId]
    )
  }

  const isMachineLocked = (machineId) => lockedMachines.includes(machineId)

  const destroyInstance = async (instanceId) => {
    if (isMachineLocked(instanceId)) {
      alert('Esta maquina esta bloqueada. Desbloqueie primeiro para destruir.')
      return
    }
    if (!confirm('Destruir esta instancia?')) return
    try {
      await fetch(`${API_BASE}/api/instances/${instanceId}`, {
        method: 'DELETE',
        credentials: 'include'
      })
      fetchData()
    } catch (e) {
      alert('Falha ao destruir instancia')
    }
  }

  const restoreInstance = async (instanceId) => {
    if (isMachineLocked(instanceId)) {
      alert('Esta maquina esta bloqueada. Desbloqueie primeiro para restaurar.')
      return
    }
    if (!selectedSnapshot) {
      alert('Selecione um snapshot primeiro')
      return
    }
    setRestoring(instanceId)
    try {
      const res = await fetch(`${API_BASE}/api/instances/${instanceId}/restore`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ snapshot_id: selectedSnapshot.id }),
        credentials: 'include'
      })
      const data = await res.json()
      if (!data.success) {
        alert(data.error || 'Restore falhou')
      }
    } catch (e) {
      alert('Erro de conexao')
    }
    setRestoring(null)
  }

  // Format date string "2025-12-15 06:40:36" to readable format
  const formatDate = (dateStr) => {
    if (!dateStr) return '-'
    try {
      const [datePart, timePart] = dateStr.split(' ')
      if (!datePart || !timePart) return dateStr

      const [year, month, day] = datePart.split('-')
      const [hour, minute] = timePart.split(':')

      return `${day}/${month} ${hour}:${minute}`
    } catch {
      return dateStr
    }
  }

  // Get relative time
  const getRelativeTime = (dateStr) => {
    if (!dateStr) return ''
    try {
      const date = new Date(dateStr.replace(' ', 'T') + 'Z')
      const now = new Date()
      const diffMs = now - date
      const diffMins = Math.floor(diffMs / 60000)
      const diffHours = Math.floor(diffMins / 60)
      const diffDays = Math.floor(diffHours / 24)

      if (diffMins < 1) return 'agora'
      if (diffMins < 60) return `${diffMins} min atras`
      if (diffHours < 24) return `${diffHours}h atras`
      return `${diffDays}d atras`
    } catch {
      return ''
    }
  }

  const formatSize = (bytes) => {
    if (!bytes) return '-'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
  }

  return (
    <div className="container">
      {/* Modal Popup for Folder Browser */}
      {showModal && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>
                <svg viewBox="0 0 24 24" fill="#d29922" width="20" height="20" style={{ marginRight: '8px', verticalAlign: 'middle' }}>
                  <path d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/>
                </svg>
                Snapshot: {modalSnapshot?.short_id}
              </h3>
              <div className="modal-actions">
                <button className="btn btn-sm" onClick={expandAll}>Expandir Tudo</button>
                <button className="btn btn-sm" onClick={collapseAll}>Colapsar</button>
                <button className="btn-close" onClick={closeModal}>
                  <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                    <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                  </svg>
                </button>
              </div>
            </div>
            <div className="modal-info">
              <span>Data: {formatDate(modalSnapshot?.time)}</span>
              <span>Path: {modalSnapshot?.paths?.[0] || '/workspace'}</span>
            </div>
            <div className="modal-body">
              {loadingTree ? (
                <div className="empty-state"><div className="spinner" /></div>
              ) : treeData.length === 0 ? (
                <div className="empty-state">Nenhum arquivo encontrado</div>
              ) : (
                <div className="tree-container">
                  {treeData.map((node, idx) => (
                    <TreeNode
                      key={node.path || idx}
                      node={node}
                      formatSize={formatSize}
                      expanded={expandedNodes}
                      onToggle={toggleNode}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="dashboard-grid-new">
        {/* Left column: Snapshots */}
        <div className="dashboard-left">
          <div className="card">
            <div className="card-header">
              <span className="card-title">Snapshots</span>
              <span className="badge">{snapshots.length}</span>
            </div>
            <div className="snapshot-list">
              {loading.snapshots ? (
                <div className="empty-state"><div className="spinner" /></div>
              ) : snapshots.length === 0 ? (
                <div className="empty-state">Nenhum snapshot encontrado</div>
              ) : (
                <ul className="list">
                  {snapshots.map(snap => (
                    <li
                      key={snap.id}
                      className={`list-item ${selectedSnapshot?.id === snap.id ? 'selected' : ''}`}
                      onClick={() => handleSnapshotClick(snap)}
                    >
                      <div className="snapshot-item-new">
                        <div className="snapshot-header">
                          <span className="snapshot-date-main">{formatDate(snap.time)}</span>
                          <span className="snapshot-relative">{getRelativeTime(snap.time)}</span>
                        </div>
                        <div className="snapshot-path">{snap.paths?.[0] || '/workspace'}</div>
                        <div className="snapshot-footer">
                          <span className="snapshot-id">{snap.short_id}</span>
                          {snap.tags?.length > 0 && (
                            <span className="snapshot-tag">{snap.tags[0]}</span>
                          )}
                          <button
                            className="btn-icon"
                            onClick={(e) => handleViewFolders(snap, e)}
                            title="Ver arquivos"
                          >
                            <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
                              <path d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/>
                            </svg>
                          </button>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>

        {/* Center: Deploy Wizard */}
        <div className="dashboard-center">
          <DeployWizard
            snapshots={snapshots}
            machines={machines}
            onRefresh={fetchData}
          />
        </div>

        {/* Right column: My Machines */}
        <div className="dashboard-right">
          <div className="card">
            <div className="card-header">
              <span className="card-title">Minhas Maquinas</span>
              <span className="badge">{machines.length}</span>
            </div>
            <div className="machines-list">
              {loading.machines ? (
                <div className="empty-state"><div className="spinner" /></div>
              ) : machines.length === 0 ? (
                <div className="empty-state">Nenhuma maquina ativa</div>
              ) : (
                <ul className="list">
                  {machines.map(machine => {
                    const isLocked = isMachineLocked(machine.id)
                    return (
                      <li key={machine.id} className={`list-item machine-item-new ${isLocked ? 'locked' : ''}`}>
                        <div className="machine-main">
                          <div className="machine-header">
                            <span className="machine-gpu">{machine.gpu_name}</span>
                            <button
                              className={`btn-lock ${isLocked ? 'active' : ''}`}
                              onClick={() => toggleMachineLock(machine.id)}
                              title={isLocked ? 'Desbloquear maquina' : 'Bloquear maquina'}
                            >
                              {isLocked ? (
                                <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
                                  <path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z"/>
                                </svg>
                              ) : (
                                <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
                                  <path d="M12 17c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm6-9h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6h1.9c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm0 12H6V10h12v10z"/>
                                </svg>
                              )}
                            </button>
                          </div>
                          <div className="machine-meta">
                            <span className={`badge badge-${machine.actual_status === 'running' ? 'success' : 'warning'}`}>
                              {machine.actual_status}
                            </span>
                            {machine.dph_total && (
                              <span className="machine-price">${machine.dph_total?.toFixed(3)}/h</span>
                            )}
                          </div>
                          {machine.ssh_host && (
                            <>
                              <div className="machine-ssh">
                                ssh root@{machine.ssh_host} -p {machine.ssh_port}
                              </div>
                              <button
                                className="btn-vscode"
                                onClick={() => window.open(`vscode://vscode-remote/ssh-remote+root@${machine.ssh_host}:${machine.ssh_port}/workspace`, '_blank')}
                                title="Abrir no VS Code"
                              >
                                <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
                                  <path d="M17.583 2.127L12.05 6.53l-5.05-3.92L2.4 4.49v15.02l4.6 1.88 5.05-3.92 5.533 4.4L22 19.5V4.5l-4.417-2.373zm-12.2 13.49V8.383L9.5 12l-4.117 3.617zm12.2 1.54l-3.1-2.44V9.283l3.1-2.44v10.314z"/>
                                </svg>
                                VS Code
                              </button>
                            </>
                          )}
                          {isLocked && (
                            <div className="machine-locked-badge">
                              <svg viewBox="0 0 24 24" fill="currentColor" width="12" height="12">
                                <path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2z"/>
                              </svg>
                              BLOQUEADA
                            </div>
                          )}
                        </div>
                        <div className="machine-actions">
                          {machine.actual_status === 'running' && (
                            <button
                              className="btn btn-sm"
                              onClick={() => restoreInstance(machine.id)}
                              disabled={restoring === machine.id || !selectedSnapshot || isLocked}
                              title={isLocked ? 'Maquina bloqueada' : 'Restaurar snapshot'}
                            >
                              {restoring === machine.id ? '...' : 'Restore'}
                            </button>
                          )}
                          <button
                            className="btn btn-sm btn-danger"
                            onClick={() => destroyInstance(machine.id)}
                            disabled={isLocked}
                            title={isLocked ? 'Maquina bloqueada' : 'Destruir maquina'}
                          >
                            Destruir
                          </button>
                        </div>
                      </li>
                    )
                  })}
                </ul>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
