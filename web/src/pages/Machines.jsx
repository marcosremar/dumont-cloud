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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu'
import { Button } from '../components/ui/button'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../components/ui/alert-dialog'
import { ChevronDown } from 'lucide-react'
import HibernationConfigModal from '../components/HibernationConfigModal'

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
  vscode: <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style={{ opacity: 0.9 }}><path d="M23.15 2.587L18.21.21a1.494 1.494 0 0 0-1.705.29l-9.46 8.63-4.12-3.128a.999.999 0 0 0-1.276.057L.327 7.261A1 1 0 0 0 .326 8.74L3.899 12 .326 15.26a1 1 0 0 0 .001 1.479L1.65 17.94a.999.999 0 0 0 1.276.057l4.12-3.128 9.46 8.63a1.492 1.492 0 0 0 1.704.29l4.942-2.377A1.5 1.5 0 0 0 24 20.06V3.939a1.5 1.5 0 0 0-.85-1.352zm-5.146 14.861L10.826 12l7.178-5.448v10.896z"/></svg>,
  cursor: <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style={{ opacity: 0.9 }}><path d="M3 3l7.07 16.97 2.51-7.39 7.39-2.51L3 3z"/><path d="M13 13l6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>,
  windsurf: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ opacity: 0.9 }}><path d="M4 12 L12 4 L20 12 M8 20 L12 12 L16 20" strokeLinecap="round" strokeLinejoin="round"/><circle cx="12" cy="12" r="2" fill="currentColor"/></svg>,
  codeium: <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style={{ opacity: 0.9 }}><circle cx="12" cy="8" r="3"/><circle cx="6" cy="16" r="2.5"/><circle cx="18" cy="16" r="2.5"/><path d="M12 11 L12 13 M12 13 L6 13.5 M12 13 L18 13.5"/></svg>,
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

// Unified Machine card component (active and inactive)
function MachineCard({ machine, onVSCode, onDestroy, onStart, onRestoreToNew }) {
  const [showMenu, setShowMenu] = useState(false)
  const [hibernateTime, setHibernateTime] = useState(10)
  const [budgetCap, setBudgetCap] = useState('')
  const [smartIdle, setSmartIdle] = useState(false)
  const [showConfigModal, setShowConfigModal] = useState(false)

  // Alert Dialog states
  const [alertDialog, setAlertDialog] = useState({ open: false, title: '', description: '', action: null })

  // Historical data for sparklines (simulated for now, would come from API)
  const [gpuHistory] = useState(() => Array.from({ length: 20 }, () => Math.random() * 40 + 30))
  const [memHistory] = useState(() => Array.from({ length: 20 }, () => Math.random() * 30 + 40))
  const [cpuHistory] = useState(() => Array.from({ length: 20 }, () => Math.random() * 20 + 10))
  const [tempHistory] = useState(() => Array.from({ length: 20 }, () => Math.random() * 15 + 55))

  const gpuUtil = machine.gpu_util ? Number(machine.gpu_util).toFixed(1) : Math.round(gpuHistory[gpuHistory.length - 1])
  const memUtil = machine.mem_usage ? Number(machine.mem_usage).toFixed(1) : Math.round(memHistory[memHistory.length - 1])
  const cpuUtil = machine.cpu_util ? Number(machine.cpu_util).toFixed(1) : Math.round(cpuHistory[cpuHistory.length - 1])
  const temp = machine.gpu_temp ? Number(machine.gpu_temp).toFixed(1) : Math.round(tempHistory[tempHistory.length - 1])

  const gpuName = machine.gpu_name || 'GPU'
  const isRunning = machine.actual_status === 'running'
  const costPerHour = machine.dph_total || 0
  const status = machine.actual_status || 'stopped'

  const [showSSHInstructions, setShowSSHInstructions] = useState(false)

  // SSH Config generator with SSH key support
  const generateSSHConfig = () => {
    return `# Adicione ao arquivo ~/.ssh/config
Host dumont-${machine.id}
  HostName ${machine.ssh_host || 'ssh.vast.ai'}
  Port ${machine.ssh_port || 22}
  User root
  StrictHostKeyChecking no
  UserKnownHostsFile /dev/null
  IdentityFile ~/.ssh/vast_rsa

# Passos para configurar:
# 1. Salve este bloco no arquivo ~/.ssh/config
# 2. Obtenha sua chave SSH privada do vast.ai em:
#    https://cloud.vast.ai/account/
# 3. Salve a chave em ~/.ssh/vast_rsa
# 4. Execute: chmod 600 ~/.ssh/vast_rsa
# 5. Teste: ssh dumont-${machine.id}`
  }

  const copySSHConfig = () => {
    navigator.clipboard.writeText(generateSSHConfig())
    setShowSSHInstructions(true)
    setTimeout(() => setShowSSHInstructions(false), 8000)
  }

  const downloadSSHConfig = () => {
    const config = generateSSHConfig()
    const blob = new Blob([config], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `dumont-${machine.id}-ssh-config.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    setShowSSHInstructions(true)
    // Optionally mark as configured (user still needs to run the setup)
    console.log(`[SSH] Config baixado para máquina ${machine.id}`)
  }

  const downloadSSHSetupScript = () => {
    const sshConfig = `Host dumont-${machine.id}
  HostName ${machine.ssh_host || 'ssh.vast.ai'}
  Port ${machine.ssh_port || 22}
  User root
  StrictHostKeyChecking no
  UserKnownHostsFile /dev/null
  IdentityFile ~/.ssh/vast_rsa`

    const setupScript = `#!/bin/bash
# Script de Setup SSH para Dumont Cloud
# Máquina: ${machine.id}
# Host: ${machine.ssh_host}
# Port: ${machine.ssh_port}

echo "🚀 Configurando SSH para dumont-${machine.id}..."

# Cria diretório .ssh se não existir
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Cria arquivo config se não existir
touch ~/.ssh/config

# Adiciona configuração ao ~/.ssh/config
if grep -q "Host dumont-${machine.id}" ~/.ssh/config 2>/dev/null; then
  echo "⚠️  Configuração já existe para dumont-${machine.id}"
  echo "    Atualizando..."
  # Remove configuração antiga
  sed -i.bak '/Host dumont-${machine.id}/,/^$/d' ~/.ssh/config
fi

echo ""
echo "Adicionando configuração SSH..."
cat >> ~/.ssh/config << EOF

Host dumont-${machine.id}
  HostName ${machine.ssh_host || 'ssh.vast.ai'}
  Port ${machine.ssh_port || 22}
  User root
  StrictHostKeyChecking no
  UserKnownHostsFile /dev/null
  IdentityFile ~/.ssh/vast_rsa
EOF

chmod 600 ~/.ssh/config
echo "✅ Configuração SSH adicionada!"

echo ""
echo "📥 Agora você precisa baixar a chave SSH do vast.ai:"
echo "   1. Acesse: https://cloud.vast.ai/account/"
echo "   2. Copie a chave privada (Private Key)"
echo "   3. Execute os comandos:"
echo ""
echo "      nano ~/.ssh/vast_rsa"
echo "      # Cole a chave, pressione Ctrl+O, Enter, Ctrl+X"
echo "      chmod 600 ~/.ssh/vast_rsa"
echo ""
echo "🧪 Teste a conexão:"
echo "   ssh dumont-${machine.id}"
echo ""
echo "Se o teste funcionar, as IDEs (Cursor, Windsurf, Antigravity) também vão funcionar!"
echo ""
echo "✨ Configuração completa!"
`

    const blob = new Blob([setupScript], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `setup-ssh-dumont-${machine.id}.sh`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    // Show instructions after download
    setTimeout(() => {
      const executed = confirm(
        `✅ Script baixado: setup-ssh-dumont-${machine.id}.sh\n\n` +
        `Execute agora no terminal:\n\n` +
        `  bash ~/Downloads/setup-ssh-dumont-${machine.id}.sh\n\n` +
        `Depois, baixe a chave SSH do vast.ai e salve em ~/.ssh/vast_rsa\n\n` +
        `Clique OK quando terminar de configurar (isso desativará os avisos)`
      )
      if (executed) {
        localStorage.setItem(`ssh-configured-${machine.id}`, 'true')
        alert('✅ SSH marcado como configurado!\n\nAgora você pode usar as IDEs sem avisos.')
      }
    }, 500)
  }

  const testSSHConnection = () => {
    const sshAlias = `dumont-${machine.id}`
    const command = `ssh ${sshAlias} "echo 'Conexão SSH funcionando!' && hostname"`
    navigator.clipboard.writeText(command)
    alert(`Comando copiado!\n\nCole no terminal para testar:\n${command}\n\nSe funcionar, as IDEs também vão funcionar.`)
  }

  // Validate SSH configuration
  const validateSSHConfig = (ideName) => {
    const sshConfigured = localStorage.getItem(`ssh-configured-${machine.id}`)
    if (!sshConfigured) {
      const setup = confirm(
        `⚠️ SSH NÃO está configurado para esta máquina!\n\n` +
        `Erro esperado: "Could not resolve hostname dumont-${machine.id}"\n\n` +
        `Para corrigir e usar ${ideName}:\n` +
        `1. Clique em "Baixar Script de Setup" (logo abaixo)\n` +
        `2. Execute no terminal: bash setup-ssh-dumont-${machine.id}.sh\n` +
        `3. Baixe a chave SSH do vast.ai e salve em ~/.ssh/vast_rsa\n` +
        `4. Teste: ssh dumont-${machine.id}\n\n` +
        `Deseja tentar abrir mesmo assim? (vai falhar)`
      )
      if (!setup) return false
    }
    return true
  }

  // Open IDE with error handling
  const openIDE = (ideName, protocol, machineId) => {
    console.log(`[IDE] Tentando abrir ${ideName} para máquina ${machineId}`)

    if (!validateSSHConfig(ideName)) {
      return
    }

    const sshAlias = `dumont-${machineId}`
    const url = `${protocol}://vscode-remote/ssh-remote+${sshAlias}/workspace`

    console.log(`[IDE] URL gerada: ${url}`)

    try {
      const opened = window.open(url, '_blank')

      // Check if window.open returned null (protocol handler not registered)
      if (opened === null) {
        alert(
          `❌ Não foi possível abrir ${ideName}\n\n` +
          `Possíveis causas:\n` +
          `• ${ideName} não está instalado\n` +
          `• Protocolo "${protocol}://" não está registrado\n` +
          `• Navegador bloqueou o popup\n\n` +
          `Solução:\n` +
          `1. Instale ${ideName}\n` +
          `2. Abra ${ideName} pelo menos uma vez\n` +
          `3. Verifique se a configuração SSH está correta`
        )
        console.error(`[IDE] ${ideName} falhou: window.open retornou null`)
        return
      }

      // Set timeout to check if app actually launched
      setTimeout(() => {
        if (opened && !opened.closed) {
          console.log(`[IDE] ${ideName} parece ter sido aberto com sucesso`)
          // Mark SSH as configured for future checks
          localStorage.setItem(`ssh-configured-${machineId}`, 'true')
        }
      }, 1000)

      console.log(`[IDE] ${ideName} iniciado com sucesso`)
    } catch (err) {
      console.error(`[IDE] Erro ao abrir ${ideName}:`, err)
      alert(
        `❌ Erro ao abrir ${ideName}\n\n` +
        `Erro: ${err.message}\n\n` +
        `Verifique:\n` +
        `• ${ideName} está instalado\n` +
        `• SSH está configurado (execute o script de setup)\n` +
        `• Permissões do navegador para abrir links externos`
      )
    }
  }

  const openInCursor = () => {
    openIDE('Cursor', 'cursor', machine.id)
  }

  const openInWindsurf = () => {
    openIDE('Windsurf', 'windsurf', machine.id)
  }

  const openInAntigravity = () => {
    openIDE('Antigravity', 'antigravity', machine.id)
  }

  const openVSCodeOnline = async () => {
    console.log(`[VSCode Online] Abrindo code-server para máquina ${machine.id}`)

    try {
      // Usar dados da máquina diretamente (já vem do backend)
      const ports = machine.ports || {}
      const publicIp = machine.public_ipaddr

      // Encontrar porta 8080 (code-server)
      const port8080Mapping = ports['8080/tcp']

      if (!port8080Mapping || !port8080Mapping[0]) {
        setAlertDialog({
          open: true,
          title: 'VS Code Online não disponível',
          description: 'A porta 8080 (code-server) não está mapeada. O code-server pode ainda estar sendo instalado. Aguarde alguns minutos e tente novamente.',
          action: null
        })
        console.error('[VSCode Online] Porta 8080 não encontrada:', ports)
        return
      }

      const hostPort = port8080Mapping[0].HostPort
      const directUrl = `http://${publicIp}:${hostPort}/`

      console.log(`[VSCode Online] Abrindo: ${directUrl}`)
      console.log(`[VSCode Online] IP: ${publicIp}`)
      console.log(`[VSCode Online] Porta: ${hostPort}`)

      // Copiar URL para clipboard
      if (navigator.clipboard) {
        navigator.clipboard.writeText(directUrl).catch(() => {})
      }

      // Abrir em nova aba
      const opened = window.open(directUrl, '_blank')

      if (!opened) {
        // Se bloqueado por popup, mostrar a URL
        const retry = confirm(
          `🔗 VS Code Online\n\n` +
          `URL: ${directUrl}\n\n` +
          `O navegador bloqueou o popup.\n` +
          `A URL foi copiada para a área de transferência.\n\n` +
          `Clique OK para abrir.`
        )
        if (retry) {
          window.location.href = directUrl
        }
      }
    } catch (err) {
      console.error('[VSCode Online] Erro:', err)
      setAlertDialog({
        open: true,
        title: 'Erro ao abrir VS Code Online',
        description: `${err.message}\n\nVerifique se a máquina está rodando e tente novamente.`,
        action: null
      })
    }
  }

  const openSSHGuide = () => {
    window.open('https://cloud.vast.ai/account/', '_blank')
  }

  // Mark SSH as configured when user downloads config
  const markSSHConfigured = () => {
    localStorage.setItem(`ssh-configured-${machine.id}`, 'true')
  }

  return (
    <div className={`dumont-machine-card ${!isRunning ? 'dumont-machine-inactive' : ''}`}>
      {/* Card Header */}
      <div className="dumont-card-header">
        <div>
          <div className="dumont-card-title">
            <span className="dumont-gpu-icon" style={!isRunning ? { color: '#999' } : {}}>{icons.cpu}</span>
            <span>{gpuName}</span>
            {!isRunning && (
              <span className="dumont-status-badge dumont-status-stopped" style={{ marginLeft: '8px' }}>
                {status}
              </span>
            )}
          </div>
          {/* Machine Info */}
          <div style={{
            marginTop: '8px',
            display: 'flex',
            gap: '12px',
            flexWrap: 'wrap',
            fontSize: '12px',
            color: 'var(--text-secondary)'
          }}>
            {machine.public_ipaddr && (
              <a
                href={`http://${machine.public_ipaddr}`}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  color: 'var(--accent-blue)',
                  textDecoration: 'none',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
                onMouseOver={(e) => e.currentTarget.style.textDecoration = 'underline'}
                onMouseOut={(e) => e.currentTarget.style.textDecoration = 'none'}
              >
                🌐 {machine.public_ipaddr}
              </a>
            )}
            <span>💾 {machine.disk_space || 100} GB SSD</span>
            <span>🧠 {Math.round((machine.cpu_ram || 16000) / 1024)} GB RAM</span>
            <span>⚙️ {machine.cpu_cores || 4} CPU Cores</span>
            <span>🎮 {Math.round((machine.gpu_ram || 24000) / 1024)} GB VRAM</span>
          </div>
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
                <button
                  className="dumont-dropdown-item"
                  onClick={() => { setShowMenu(false); setShowConfigModal(true) }}
                >
                  {icons.settings} Auto-Hibernation Config
                </button>
                <div className="dumont-dropdown-divider" />
                {isRunning && <button className="dumont-dropdown-item">Startup Script</button>}
                <button className="dumont-dropdown-item">View Logs</button>
                {isRunning && <button className="dumont-dropdown-item">Force Snapshot</button>}
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

      {/* Metrics Grid - Redesigned */}
      {isRunning ? (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '12px',
          marginTop: '16px'
        }}>
          {/* GPU Metric */}
          <div style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            padding: '12px'
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'baseline',
              marginBottom: '8px'
            }}>
              <span style={{
                fontSize: '11px',
                fontWeight: '600',
                color: 'var(--text-secondary)',
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>GPU</span>
              <span style={{
                fontSize: '18px',
                fontWeight: '700',
                color: '#3fb950'
              }}>{gpuUtil}%</span>
            </div>
            <SparklineChart data={gpuHistory} color="#3fb950" />
          </div>

          {/* Memory Metric */}
          <div style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            padding: '12px'
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'baseline',
              marginBottom: '8px'
            }}>
              <span style={{
                fontSize: '11px',
                fontWeight: '600',
                color: 'var(--text-secondary)',
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>MEMÓRIA</span>
              <span style={{
                fontSize: '18px',
                fontWeight: '700',
                color: '#d29922'
              }}>{memUtil}%</span>
            </div>
            <SparklineChart data={memHistory} color="#d29922" />
          </div>

          {/* CPU Metric */}
          <div style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            padding: '12px'
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'baseline',
              marginBottom: '8px'
            }}>
              <span style={{
                fontSize: '11px',
                fontWeight: '600',
                color: 'var(--text-secondary)',
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>CPU</span>
              <span style={{
                fontSize: '18px',
                fontWeight: '700',
                color: '#58a6ff'
              }}>{cpuUtil}%</span>
            </div>
            <SparklineChart data={cpuHistory} color="#58a6ff" />
          </div>

          {/* Temperature Metric */}
          <div style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            padding: '12px'
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'baseline',
              marginBottom: '8px'
            }}>
              <span style={{
                fontSize: '11px',
                fontWeight: '600',
                color: 'var(--text-secondary)',
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>TEMP</span>
              <span style={{
                fontSize: '18px',
                fontWeight: '700',
                color: temp > 75 ? '#f85149' : temp > 65 ? '#d29922' : '#3fb950'
              }}>{temp}°C</span>
            </div>
            <SparklineChart data={tempHistory} color={temp > 75 ? '#f85149' : temp > 65 ? '#d29922' : '#3fb950'} />
          </div>
        </div>
      ) : (
        /* Static Info for Inactive Machines */
        <div className="dumont-inactive-info">
          <div className="dumont-inactive-cost">
            <div className="dumont-metric-label">Custo por Hora</div>
            <div className="dumont-metric-value" style={{ fontSize: '20px', color: '#ffdf00' }}>
              ${costPerHour.toFixed(3)}/h
            </div>
          </div>
          <div className="dumont-inactive-specs">
            <div className="dumont-spec-item">
              <span className="dumont-spec-label">GPU RAM:</span>
              <span className="dumont-spec-value">{Math.round((machine.gpu_ram || 24000) / 1024)} GB</span>
            </div>
            <div className="dumont-spec-item">
              <span className="dumont-spec-label">CPU:</span>
              <span className="dumont-spec-value">{machine.cpu_cores || 4} cores</span>
            </div>
            <div className="dumont-spec-item">
              <span className="dumont-spec-label">RAM:</span>
              <span className="dumont-spec-value">{Math.round((machine.cpu_ram || 16000) / 1024)} GB</span>
            </div>
            <div className="dumont-spec-item">
              <span className="dumont-spec-label">Disk:</span>
              <span className="dumont-spec-value">{machine.disk_space || 100} GB</span>
            </div>
          </div>
        </div>
      )}

      {/* IDEs Section - Clean & Simple */}
      {isRunning && (
        <>
          <div style={{
            marginTop: '16px',
            padding: '16px',
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border)',
            borderRadius: '8px'
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '12px'
            }}>
              <span style={{
                fontSize: '13px',
                fontWeight: '600',
                color: 'var(--text-primary)',
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                Abrir IDE
              </span>
              <button
                onClick={downloadSSHSetupScript}
                style={{
                  padding: '4px 10px',
                  fontSize: '12px',
                  color: 'var(--accent-blue)',
                  background: 'transparent',
                  border: '1px solid var(--border)',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
                onMouseOver={(e) => e.currentTarget.style.background = 'var(--bg-tertiary)'}
                onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
              >
                📥 Setup SSH
              </button>
            </div>

            <div style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '8px'
            }}>
              {/* VS Code with Dropdown */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button className="dumont-ide-btn dumont-ide-vscode" style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', fontSize: '12px' }}>
                    {icons.vscode}
                    <span>VS Code</span>
                    <ChevronDown className="h-3 w-3 opacity-50" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start">
                  <DropdownMenuItem onClick={openVSCodeOnline}>
                    {icons.vscode}
                    <span>VS Code Online (Web)</span>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => openIDE('VS Code', 'vscode', machine.id)}>
                    {icons.vscode}
                    <span>VS Code Desktop (SSH)</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>

              {/* Cursor */}
              <button className="dumont-ide-btn dumont-ide-cursor" onClick={openInCursor} style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', fontSize: '12px' }}>
                {icons.cursor}
                <span>Cursor</span>
              </button>

              {/* Windsurf */}
              <button className="dumont-ide-btn dumont-ide-windsurf" onClick={openInWindsurf} style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', fontSize: '12px' }}>
                {icons.windsurf}
                <span>Windsurf</span>
              </button>

              {/* Antigravity */}
              <button className="dumont-ide-btn dumont-ide-antigravity" onClick={openInAntigravity} style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', fontSize: '12px' }}>
                {icons.codeium}
                <span>Antigravity</span>
              </button>
            </div>
          </div>

          {/* SSH Configuration Section - Redesigned */}
          <div style={{
            marginTop: '16px',
            padding: '16px',
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border)',
            borderRadius: '8px'
          }}>
            <div style={{
              fontSize: '13px',
              fontWeight: '600',
              color: 'var(--text-primary)',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              marginBottom: '12px'
            }}>
              Configuração SSH
            </div>

            <div style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '8px'
            }}>
              <Button variant="outline" size="sm" onClick={downloadSSHConfig} style={{ gap: '6px' }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                  <polyline points="7 10 12 15 17 10"></polyline>
                  <line x1="12" y1="15" x2="12" y2="3"></line>
                </svg>
                <span>Baixar Config</span>
              </Button>

              <Button variant="outline" size="sm" onClick={copySSHConfig} style={{ gap: '6px' }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
                <span>Copiar</span>
              </Button>

              <Button variant="outline" size="sm" onClick={openSSHGuide} style={{ gap: '6px' }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>
                </svg>
                <span>Chave SSH</span>
              </Button>

              <Button variant="outline" size="sm" onClick={testSSHConnection} style={{ gap: '6px' }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
                </svg>
                <span>Testar</span>
              </Button>
            </div>

            {showSSHInstructions && (
              <div className="dumont-ssh-instructions">
                <div className="dumont-ssh-instructions-header">
                  <strong>⚙️ Configuração SSH - Instruções</strong>
                </div>
                <ol className="dumont-ssh-steps">
                  <li><strong>Abra/Crie</strong> o arquivo <code>~/.ssh/config</code> no seu Mac/Linux</li>
                  <li><strong>Cole</strong> a configuração copiada/baixada no final do arquivo</li>
                  <li><strong>Obtenha</strong> sua chave SSH privada em <a href="https://cloud.vast.ai/account/" target="_blank" rel="noopener">vast.ai/account</a></li>
                  <li><strong>Salve</strong> a chave privada em <code>~/.ssh/vast_rsa</code></li>
                  <li><strong>Ajuste permissões:</strong> <code>chmod 600 ~/.ssh/vast_rsa</code></li>
                  <li><strong>Teste</strong> a conexão: <code>ssh dumont-{machine.id}</code></li>
                  <li><strong>Clique</strong> nos botões de IDE acima - agora vai funcionar! ✅</li>
                </ol>
              </div>
            )}
          </div>
        </>
      )}

      {/* Control Rows */}
      <div className="dumont-controls">
        {isRunning ? (
          <>
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
          </>
        ) : (
          /* Actions for Inactive Machines */
          <>
            <button
              className="dumont-btn-primary"
              onClick={() => onStart && onStart(machine.id)}
              style={{ width: '100%', marginBottom: '8px' }}
            >
              {icons.server}
              <span>Iniciar Maquina</span>
            </button>
            <button
              className="dumont-btn-secondary"
              onClick={() => onRestoreToNew && onRestoreToNew(machine)}
              style={{ width: '100%' }}
            >
              {icons.plus}
              <span>Restaurar em Nova Maquina</span>
            </button>
          </>
        )}
      </div>

      {/* Modal de Configuração de Auto-Hibernação */}
      <HibernationConfigModal
        instance={{ id: machine.id, name: machine.gpu_name || `Instance ${machine.id}` }}
        isOpen={showConfigModal}
        onClose={() => setShowConfigModal(false)}
        onSave={(config) => {
          console.log('Config saved:', config)
          // Você pode atualizar o estado da máquina aqui se necessário
        }}
      />

      {/* Alert Dialog - substitui alert() feio */}
      <AlertDialog open={alertDialog.open} onOpenChange={(open) => setAlertDialog({ ...alertDialog, open })}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{alertDialog.title}</AlertDialogTitle>
            <AlertDialogDescription className="whitespace-pre-line">
              {alertDialog.description}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            {alertDialog.action ? (
              <>
                <AlertDialogCancel>Cancelar</AlertDialogCancel>
                <AlertDialogAction onClick={alertDialog.action}>Confirmar</AlertDialogAction>
              </>
            ) : (
              <AlertDialogAction>OK</AlertDialogAction>
            )}
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

export default function Machines() {
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

  const handleStartMachine = async (machineId) => {
    if (!confirm('Deseja iniciar esta maquina?')) return
    try {
      const res = await fetch(`${API_BASE}/api/instances/${machineId}/start`, {
        method: 'POST',
        credentials: 'include'
      })
      if (!res.ok) throw new Error('Erro ao iniciar maquina')
      fetchMachines()
      alert('Maquina iniciada com sucesso!')
    } catch (err) {
      alert(err.message)
    }
  }

  const handleRestoreToNew = (machine) => {
    // Redirecionar para a pagina de deploy com o snapshot da maquina
    window.location.href = `/?restore_from=${machine.id}`
  }

  const activeMachines = machines.filter(m => m.actual_status === 'running')
  const inactiveMachines = machines.filter(m => m.actual_status !== 'running')
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
    <div className="container" style={{ maxWidth: '1400px', margin: '0 auto', padding: '24px' }}>
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
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              {activeMachines.length > 0 && (
                <span className="dumont-badge dumont-badge-success">{activeMachines.length} Ativas</span>
              )}
              {inactiveMachines.length > 0 && (
                <span className="dumont-badge dumont-badge-inactive">{inactiveMachines.length} Desativadas</span>
              )}
              <Link to="/" className="dumont-btn-primary">
                {icons.plus}
                <span>Nova Maquina</span>
              </Link>
            </div>
          </div>

          {error && (
            <div className="alert alert-error" style={{ marginBottom: '20px' }}>
              {error}
            </div>
          )}

          {machines.length === 0 ? (
            <div className="dumont-empty-state">
              <p>Nenhuma maquina no momento</p>
              <Link to="/" className="dumont-btn-primary" style={{ marginTop: '16px' }}>
                Criar primeira maquina
              </Link>
            </div>
          ) : (
            <div className="dumont-machines-grid">
              {/* Active Machines First */}
              {activeMachines.map((machine) => (
                <MachineCard
                  key={machine.id}
                  machine={machine}
                  onVSCode={openVSCode}
                  onDestroy={handleDestroy}
                  onStart={handleStartMachine}
                  onRestoreToNew={handleRestoreToNew}
                />
              ))}
              {/* Then Inactive Machines */}
              {inactiveMachines.map((machine) => (
                <MachineCard
                  key={machine.id}
                  machine={machine}
                  onVSCode={openVSCode}
                  onDestroy={handleDestroy}
                  onStart={handleStartMachine}
                  onRestoreToNew={handleRestoreToNew}
                />
              ))}
            </div>
          )}
        </div>
    </div>
  )
}
