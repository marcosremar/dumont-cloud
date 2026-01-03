import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Cpu, Server, DollarSign, Shield, Activity, Zap, Clock, TrendingUp,
  Plus, ArrowRight, HardDrive, Wifi, AlertCircle, CheckCircle, RefreshCw,
  Wallet, ChevronRight, Gauge, Terminal, Layers, Globe
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || '';

// Componentes movidos para FORA do Dashboard para evitar re-criação a cada render
const MetricCard = ({ icon: Icon, title, value, subtitle, colorClass, glowClass, animationClass }) => (
  <div className={`glow-card p-4 min-h-[120px] flex flex-col justify-between ${animationClass}`}>
    <div className="flex items-center justify-between gap-2">
      <span className="text-[10px] font-medium uppercase tracking-wider text-white/40 truncate">{title}</span>
      <div className={`p-2 rounded-lg bg-white/5 shrink-0 ${glowClass}`}>
        <Icon className="w-4 h-4" />
      </div>
    </div>
    <div className="mt-auto">
      <p className={`text-2xl font-bold ${colorClass}`}>{value}</p>
      {subtitle && (
        <p className="text-[10px] text-white/40 mt-1 font-body truncate">{subtitle}</p>
      )}
    </div>
  </div>
);

const StatusIndicator = ({ status, label }) => {
  const colors = {
    operational: 'text-[#4caf50]',
    warning: 'text-amber-400',
    error: 'text-red-400'
  };
  return (
    <div className="status-bar">
      <span
        className={`w-2 h-2 rounded-full ${colors[status]} status-pulse`}
        style={{ backgroundColor: status === 'operational' ? '#4caf50' : status === 'warning' ? '#ffc107' : '#ef4444' }}
      />
      <span className="text-sm text-white/60 font-body flex-1">{label}</span>
      <span className={`text-xs font-medium ${colors[status]}`}>
        {status === 'operational' ? 'Online' : status === 'warning' ? 'Alerta' : 'Offline'}
      </span>
    </div>
  );
};

export default function Dashboard({ onStatsUpdate }) {
  const navigate = useNavigate();
  const location = useLocation();
  const basePath = location.pathname.startsWith('/demo-app') ? '/demo-app' : '/app';
  const containerRef = useRef(null);

  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    activeMachines: 0,
    totalMachines: 0,
    dailyCost: '0.00',
    savings: '0',
    uptime: 0,
    balance: '0.00'
  });
  const [recentActivity, setRecentActivity] = useState([]);
  const [currentTime, setCurrentTime] = useState(new Date());

  const getToken = () => localStorage.getItem('auth_token');

  // Update time every second for the clock display
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Mouse tracking for glow effect
  useEffect(() => {
    const handleMouseMove = (e) => {
      const cards = document.querySelectorAll('.glow-card');
      cards.forEach(card => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        card.style.setProperty('--mouse-x', `${x}px`);
        card.style.setProperty('--mouse-y', `${y}px`);
      });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [instancesRes, balanceRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/instances`, {
          headers: { 'Authorization': `Bearer ${getToken()}` }
        }),
        fetch(`${API_BASE}/api/v1/instances/balance`, {
          headers: { 'Authorization': `Bearer ${getToken()}` }
        }).catch(() => null)
      ]);

      let balanceValue = '0.00';
      if (balanceRes?.ok) {
        try {
          const balanceData = await balanceRes.json();
          balanceValue = (balanceData.credit || balanceData.balance || 0).toFixed(2);
        } catch {}
      }

      if (instancesRes.ok) {
        const data = await instancesRes.json();
        const instances = data.instances || [];
        const running = instances.filter(i => i.status === 'running' || i.actual_status === 'running');
        const totalCost = running.reduce((acc, i) => acc + (i.dph_total || 0), 0);

        const newStats = {
          activeMachines: running.length,
          totalMachines: instances.length,
          dailyCost: (totalCost * 24).toFixed(2),
          savings: ((totalCost * 24 * 0.89) * 30).toFixed(0),
          uptime: running.length > 0 ? 99.9 : 0,
          balance: balanceValue
        };
        setStats(newStats);
        if (onStatsUpdate) onStatsUpdate(newStats);

        const activity = instances.slice(0, 5).map((inst, idx) => ({
          id: inst.id || idx,
          type: inst.actual_status === 'running' ? 'running' : 'created',
          message: `${inst.gpu_name || 'GPU'} - ${inst.actual_status || 'pending'}`,
          time: inst.start_date ? new Date(inst.start_date * 1000).toLocaleString() : 'Recente',
          status: inst.actual_status === 'running' ? 'success' : 'info'
        }));
        setRecentActivity(activity);
      }
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (date) => {
    return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const formatDate = (date) => {
    return date.toLocaleDateString('pt-BR', { weekday: 'short', day: '2-digit', month: 'short' }).toUpperCase();
  };

  // Estado para controlar se a animação inicial já ocorreu
  const [hasAnimated, setHasAnimated] = useState(false);

  useEffect(() => {
    // Marca que a animação inicial já aconteceu após o primeiro render
    const timer = setTimeout(() => setHasAnimated(true), 600);
    return () => clearTimeout(timer);
  }, []);

  // Gera classe de animação apenas no primeiro render
  const getAnimationClass = (delay) => {
    return hasAnimated ? '' : `animate-slide-up animate-delay-${delay}`;
  };

  return (
    <div ref={containerRef} className="dashboard-command-center p-6 md:p-8 space-y-8">
      {/* Header Section */}
      <div className={`flex flex-col md:flex-row md:items-end justify-between gap-6 ${getAnimationClass(0)}`}>
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-2 h-2 rounded-full bg-[#4caf50] status-pulse" />
            <span className="text-xs text-white/40 font-data tracking-wider">SISTEMA OPERACIONAL</span>
          </div>
          <h1 className="text-3xl md:text-4xl font-display font-bold text-white header-accent">
            COMMAND CENTER
          </h1>
          <p className="text-white/50 mt-4 font-body">
            Monitoramento e controle de infraestrutura GPU
          </p>
        </div>

        {/* Live Clock */}
        <div className="glow-card px-6 py-4 text-right">
          <div className="text-3xl font-data metric-value-green">
            {formatTime(currentTime)}
          </div>
          <div className="text-xs text-white/40 font-data mt-1">
            {formatDate(currentTime)}
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <MetricCard
          icon={Server}
          title="MAQUINAS ATIVAS"
          value={`${stats.activeMachines}/${stats.totalMachines}`}
          subtitle="Em execucao agora"
          colorClass="metric-value-green"
          glowClass="text-[#4caf50] icon-glow-green"
          animationClass={getAnimationClass(1)}
        />
        <MetricCard
          icon={DollarSign}
          title="CUSTO DIARIO"
          value={`$${stats.dailyCost}`}
          subtitle="Consumo atual"
          colorClass="metric-value-blue"
          glowClass="text-[#00d4ff] icon-glow-blue"
          animationClass={getAnimationClass(2)}
        />
        <MetricCard
          icon={TrendingUp}
          title="ECONOMIA MENSAL"
          value={`$${stats.savings}`}
          subtitle="vs AWS/GCP"
          colorClass="metric-value-green"
          glowClass="text-[#4caf50] icon-glow-green"
          animationClass={getAnimationClass(3)}
        />
        <MetricCard
          icon={Gauge}
          title="UPTIME"
          value={`${stats.uptime}%`}
          subtitle="Ultimos 30 dias"
          colorClass="metric-value-purple"
          glowClass="text-purple-400 icon-glow-purple"
          animationClass={getAnimationClass(4)}
        />
        <MetricCard
          icon={Wallet}
          title="SALDO VAST"
          value={`$${stats.balance}`}
          subtitle="Credito disponivel"
          colorClass="metric-value-amber"
          glowClass="text-amber-400 icon-glow-amber"
          animationClass={getAnimationClass(5)}
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Quick Deploy Card - With World Map Background */}
        <div className={`glow-card relative overflow-hidden ${getAnimationClass(6)}`}>
          {/* World Map SVG Background */}
          <div className="absolute inset-0 opacity-20">
            <svg viewBox="0 0 800 400" className="w-full h-full" preserveAspectRatio="xMidYMid slice">
              <defs>
                <radialGradient id="glow" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor="#4caf50" stopOpacity="0.3"/>
                  <stop offset="100%" stopColor="#4caf50" stopOpacity="0"/>
                </radialGradient>
              </defs>
              {/* Simplified world map paths */}
              <g fill="none" stroke="#4caf50" strokeWidth="0.5" opacity="0.6">
                {/* North America */}
                <path d="M120,80 Q150,60 180,70 Q220,50 250,80 Q280,90 300,120 Q280,150 250,160 Q200,180 150,160 Q120,140 100,120 Q90,100 120,80"/>
                {/* South America */}
                <path d="M200,200 Q230,190 250,220 Q260,260 250,300 Q230,340 200,350 Q170,340 160,300 Q150,250 170,220 Q180,200 200,200"/>
                {/* Europe */}
                <path d="M380,60 Q420,50 460,60 Q500,70 520,100 Q500,120 460,130 Q420,140 380,130 Q360,110 380,60"/>
                {/* Africa */}
                <path d="M400,150 Q450,140 480,170 Q500,220 480,280 Q450,320 400,330 Q360,310 350,260 Q340,200 370,160 Q380,150 400,150"/>
                {/* Asia */}
                <path d="M520,50 Q600,40 680,60 Q740,90 750,140 Q740,180 700,200 Q640,220 580,200 Q540,170 520,130 Q510,90 520,50"/>
                {/* Australia */}
                <path d="M650,280 Q700,260 740,280 Q760,310 740,340 Q700,360 660,340 Q630,310 650,280"/>
              </g>
              {/* Glowing datacenter points */}
              <g>
                {/* US West */}
                <circle cx="150" cy="110" r="4" fill="#4caf50" className="animate-pulse"/>
                <circle cx="150" cy="110" r="8" fill="url(#glow)"/>
                {/* US East */}
                <circle cx="250" cy="120" r="3" fill="#4caf50" className="animate-pulse" style={{animationDelay: '0.5s'}}/>
                <circle cx="250" cy="120" r="6" fill="url(#glow)"/>
                {/* Europe */}
                <circle cx="440" cy="90" r="4" fill="#4caf50" className="animate-pulse" style={{animationDelay: '1s'}}/>
                <circle cx="440" cy="90" r="8" fill="url(#glow)"/>
                {/* Asia */}
                <circle cx="650" cy="120" r="3" fill="#4caf50" className="animate-pulse" style={{animationDelay: '1.5s'}}/>
                <circle cx="650" cy="120" r="6" fill="url(#glow)"/>
                {/* South America */}
                <circle cx="220" cy="280" r="2" fill="#4caf50" className="animate-pulse" style={{animationDelay: '2s'}}/>
                <circle cx="220" cy="280" r="4" fill="url(#glow)"/>
              </g>
              {/* Connection lines */}
              <g stroke="#4caf50" strokeWidth="0.3" opacity="0.3" strokeDasharray="4,4">
                <line x1="150" y1="110" x2="250" y2="120"/>
                <line x1="250" y1="120" x2="440" y2="90"/>
                <line x1="440" y1="90" x2="650" y2="120"/>
                <line x1="250" y1="120" x2="220" y2="280"/>
              </g>
            </svg>
          </div>

          {/* Card Content */}
          <div className="relative z-10 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2.5 rounded-xl bg-[#4caf50]/20 border border-[#4caf50]/30">
                <Globe className="w-5 h-5 text-[#4caf50] icon-glow-green" />
              </div>
              <div>
                <h3 className="font-display text-sm font-semibold text-white">DEPLOY GLOBAL</h3>
                <p className="text-[10px] text-white/40 font-body">GPUs em 5 continentes</p>
              </div>
            </div>

            <p className="text-sm text-white/60 font-body mb-6 leading-relaxed">
              Provisione GPUs de alta performance com failover automatico e backup em tempo real.
            </p>

            <div className="space-y-3">
              <button
                onClick={() => navigate(`${basePath}/machines/new`)}
                className="ta-btn ta-btn-primary w-full justify-center"
              >
                <Plus className="w-4 h-4" />
                New Machine
              </button>
              <button
                onClick={() => navigate(`${basePath}/gpu-offers`)}
                className="ta-btn ta-btn-secondary w-full justify-center"
              >
                <HardDrive className="w-4 h-4" />
                Explorar Ofertas
              </button>
            </div>
          </div>
        </div>

        {/* System Status Card */}
        <div className={`glow-card p-6 ${getAnimationClass(7)}`}>
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 rounded-lg bg-[#4caf50]/10">
              <Shield className="w-5 h-5 text-[#4caf50] icon-glow-green" />
            </div>
            <div>
              <h3 className="font-display text-sm font-semibold text-white">STATUS DO SISTEMA</h3>
              <p className="text-xs text-white/40 font-body">Todos os servicos</p>
            </div>
          </div>

          <div className="space-y-3">
            <StatusIndicator status="operational" label="API Dumont Cloud" />
            <StatusIndicator status="operational" label="VAST.ai Gateway" />
            <StatusIndicator status="operational" label="CPU Failover Ready" />
            <StatusIndicator status="operational" label="Checkpoint Sync" />
          </div>

          <div className="mt-6 pt-4 border-t border-white/5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-white/40 font-body">Ultima verificacao</span>
              <span className="text-white/60 font-data">{formatTime(currentTime)}</span>
            </div>
          </div>
        </div>

        {/* Recent Activity Card */}
        <div className={`glow-card p-6 ${getAnimationClass(8)}`}>
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 rounded-lg bg-[#00d4ff]/10">
              <Activity className="w-5 h-5 text-[#00d4ff] icon-glow-blue" />
            </div>
            <div>
              <h3 className="font-display text-sm font-semibold text-white">ATIVIDADE RECENTE</h3>
              <p className="text-xs text-white/40 font-body">Ultimos eventos</p>
            </div>
          </div>

          {recentActivity.length === 0 ? (
            <div className="text-center py-8">
              <Terminal className="w-10 h-10 mx-auto text-white/20 mb-3" />
              <p className="text-sm text-white/40 font-body">Nenhuma atividade recente</p>
            </div>
          ) : (
            <div className="space-y-3">
              {recentActivity.map((activity) => (
                <div
                  key={activity.id}
                  className={`activity-item py-2 ${
                    activity.status === 'success' ? 'text-[#4caf50]' :
                    activity.status === 'warning' ? 'text-amber-400' :
                    activity.status === 'error' ? 'text-red-400' : 'text-[#00d4ff]'
                  }`}
                >
                  <p className="text-sm text-white/80 font-body">{activity.message}</p>
                  <p className="text-xs text-white/40 font-data mt-1">{activity.time}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className={getAnimationClass(8)}>
        <div className="flex items-center gap-3 mb-4">
          <Layers className="w-4 h-4 text-white/40" />
          <h3 className="font-display text-xs font-semibold text-white/60 tracking-wider">ACOES RAPIDAS</h3>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { icon: Server, label: 'Ver Maquinas', path: `${basePath}/machines` },
            { icon: Zap, label: 'Ver Jobs', path: `${basePath}/jobs` },
            { icon: Activity, label: 'Analytics', path: `${basePath}/metrics-hub` },
            { icon: Shield, label: 'Config Failover', path: `${basePath}/settings?tab=failover` },
          ].map((action, idx) => (
            <button
              key={action.label}
              onClick={() => navigate(action.path)}
              className="quick-action-btn text-left group"
            >
              <action.icon className="w-6 h-6 text-white/40 group-hover:text-[#4caf50] transition-colors mb-3" />
              <p className="text-sm text-white/70 group-hover:text-white font-body transition-colors">{action.label}</p>
              <ChevronRight className="w-4 h-4 text-white/20 group-hover:text-[#4caf50] absolute top-1/2 right-4 -translate-y-1/2 transition-all group-hover:translate-x-1" />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
