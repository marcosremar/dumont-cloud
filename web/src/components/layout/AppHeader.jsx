import { useState, useRef, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { useSidebar } from "../../context/SidebarContext";
import { useTheme } from "../../context/ThemeContext";
import {
  Menu,
  X,
  Search,
  Bell,
  Moon,
  Sun,
  ChevronDown,
  User,
  LogOut,
  Cloud,
  Server,
  DollarSign,
  Shield,
  Building2,
  Check,
  Users
} from "lucide-react";
import DumontLogo from "../DumontLogo";
import CurrencySelector from "../CurrencySelector";
import { apiGet, apiPost, isDemoMode } from "../../utils/api";

// Demo data for team selector
const DEMO_TEAMS = [
  { id: 1, name: 'Engineering', role: 'Admin', member_count: 8 },
  { id: 2, name: 'Data Science', role: 'Developer', member_count: 5 },
  { id: 3, name: 'Research', role: 'Viewer', member_count: 3 },
];

// Helper to get base path based on demo mode
function useBasePath() {
  const location = useLocation();
  return location.pathname.startsWith('/demo-app') ? '/demo-app' : '/app';
}

const AppHeader = ({ user, onLogout, isDemo = false, dashboardStats = null }) => {
  const [isNotificationOpen, setNotificationOpen] = useState(false);
  const [isUserMenuOpen, setUserMenuOpen] = useState(false);
  const [isTeamSelectorOpen, setTeamSelectorOpen] = useState(false);
  const [teams, setTeams] = useState([]);
  const [currentTeam, setCurrentTeam] = useState(null);
  const [teamsLoading, setTeamsLoading] = useState(true);
  const [switchingTeam, setSwitchingTeam] = useState(false);

  const { isMobileOpen, toggleSidebar, toggleMobileSidebar } = useSidebar();
  const { theme, toggleTheme } = useTheme();
  const basePath = useBasePath();

  const notificationRef = useRef(null);
  const userMenuRef = useRef(null);
  const teamSelectorRef = useRef(null);

  const handleToggle = () => {
    if (window.innerWidth >= 1024) {
      toggleSidebar();
    } else {
      toggleMobileSidebar();
    }
  };

  // Fetch user's teams on mount
  useEffect(() => {
    const fetchTeams = async () => {
      try {
        if (isDemo || isDemoMode()) {
          // Use demo data
          await new Promise(r => setTimeout(r, 300));
          setTeams(DEMO_TEAMS);
          // Get current team from localStorage or default to first team
          const storedTeamId = localStorage.getItem('current_team_id');
          const storedTeam = storedTeamId
            ? DEMO_TEAMS.find(t => t.id === parseInt(storedTeamId))
            : DEMO_TEAMS[0];
          setCurrentTeam(storedTeam || DEMO_TEAMS[0]);
          setTeamsLoading(false);
          return;
        }

        const res = await apiGet('/api/v1/users/me/teams');
        if (res.ok) {
          const data = await res.json();
          const teamsList = data.teams || data || [];
          setTeams(teamsList);

          // Get current team from localStorage or token
          const storedTeamId = localStorage.getItem('current_team_id');
          if (storedTeamId) {
            const storedTeam = teamsList.find(t => t.id === parseInt(storedTeamId));
            setCurrentTeam(storedTeam || teamsList[0]);
          } else if (teamsList.length > 0) {
            setCurrentTeam(teamsList[0]);
            localStorage.setItem('current_team_id', teamsList[0].id.toString());
          }
        }
      } catch (err) {
        // Fall back to demo data on error
        if (isDemo || isDemoMode()) {
          setTeams(DEMO_TEAMS);
          setCurrentTeam(DEMO_TEAMS[0]);
        }
      } finally {
        setTeamsLoading(false);
      }
    };

    fetchTeams();
  }, [isDemo]);

  // Handle team switch
  const handleTeamSwitch = async (team) => {
    if (team.id === currentTeam?.id) {
      setTeamSelectorOpen(false);
      return;
    }

    setSwitchingTeam(true);
    try {
      if (isDemo || isDemoMode()) {
        // Demo mode - just update local state
        await new Promise(r => setTimeout(r, 500));
        setCurrentTeam(team);
        localStorage.setItem('current_team_id', team.id.toString());
        setTeamSelectorOpen(false);
        // Reload page to refresh context
        window.location.reload();
        return;
      }

      // Call switch-team API
      const res = await apiPost('/api/v1/users/me/switch-team', { team_id: team.id });
      if (res.ok) {
        const data = await res.json();
        // Update token in localStorage
        if (data.token) {
          localStorage.setItem('auth_token', data.token);
        }
        localStorage.setItem('current_team_id', team.id.toString());
        setCurrentTeam(team);
        setTeamSelectorOpen(false);
        // Reload page to refresh with new team context
        window.location.reload();
      } else {
        const error = await res.json().catch(() => ({}));
        console.error('Failed to switch team:', error);
      }
    } catch (err) {
      console.error('Error switching team:', err);
    } finally {
      setSwitchingTeam(false);
    }
  };

  // Close dropdowns on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (notificationRef.current && !notificationRef.current.contains(event.target)) {
        setNotificationOpen(false);
      }
      if (userMenuRef.current && !userMenuRef.current.contains(event.target)) {
        setUserMenuOpen(false);
      }
      if (teamSelectorRef.current && !teamSelectorRef.current.contains(event.target)) {
        setTeamSelectorOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header className="sticky top-0 flex w-full bg-white border-b border-gray-200 z-[99999] dark:border-white/5 dark:bg-[#0a0d0a]">
      <div className="flex items-center justify-between w-full px-4 py-3 lg:px-6">
        {/* Left side */}
        <div className="flex items-center gap-4">
          {/* Sidebar Toggle */}
          <button
            className="flex items-center justify-center w-10 h-10 text-gray-500 rounded-lg hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-[#1a1f1a]"
            onClick={handleToggle}
            aria-label="Toggle Sidebar"
          >
            {isMobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>

          {/* Mobile Logo */}
          <Link to={basePath} className="flex items-center gap-2 lg:hidden">
            <DumontLogo size={32} />
            <span className="text-lg font-bold text-gray-900 dark:text-white">Dumont Cloud</span>
          </Link>
        </div>

        {/* Right side */}
        <div className="flex items-center gap-3">
          {/* Dashboard Stats - Only show on dashboard page */}
          {dashboardStats && (
            <>
              <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/5 border border-white/10">
                <Server className="w-4 h-4 text-brand-400" />
                <div>
                  <p className="text-[10px] text-gray-400 leading-none">Máquinas</p>
                  <p className="text-xs font-bold text-white leading-none mt-0.5">{dashboardStats.activeMachines}/{dashboardStats.totalMachines}</p>
                </div>
              </div>

              <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/5 border border-white/10">
                <DollarSign className="w-4 h-4 text-yellow-400" />
                <div>
                  <p className="text-[10px] text-gray-400 leading-none">Custo/Dia</p>
                  <p className="text-xs font-bold text-white leading-none mt-0.5">${dashboardStats.dailyCost}</p>
                </div>
              </div>

              <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/5 border border-white/10">
                <Shield className="w-4 h-4 text-brand-400" />
                <div>
                  <p className="text-[10px] text-gray-400 leading-none">Economia</p>
                  <p className="text-xs font-bold text-brand-500 leading-none mt-0.5">${dashboardStats.savings} <span className="text-[9px] text-brand-400">+89%</span></p>
                </div>
              </div>

              <div className="h-8 w-px bg-white/10 hidden lg:block" />
            </>
          )}

          {/* Team Selector */}
          {teams.length > 0 && (
            <div className="relative" ref={teamSelectorRef}>
              <button
                onClick={() => setTeamSelectorOpen(!isTeamSelectorOpen)}
                disabled={switchingTeam}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-[#1a1f1a] border border-transparent hover:border-gray-200 dark:hover:border-white/10 transition-colors disabled:opacity-50"
                data-testid="team-selector"
              >
                <div className="w-7 h-7 bg-brand-500/20 rounded-lg flex items-center justify-center">
                  <Building2 size={14} className="text-brand-400" />
                </div>
                <div className="hidden sm:block text-left max-w-[120px]">
                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                    {teamsLoading ? '...' : (currentTeam?.name || 'Select Team')}
                  </p>
                  <p className="text-[10px] text-gray-500 leading-none">
                    {currentTeam?.role || 'Team'}
                  </p>
                </div>
                <ChevronDown size={14} className={`text-gray-400 hidden sm:block transition-transform ${isTeamSelectorOpen ? 'rotate-180' : ''}`} />
              </button>

              {/* Team Selector Dropdown */}
              {isTeamSelectorOpen && (
                <div className="absolute right-0 mt-2 w-72 bg-white rounded-xl shadow-theme-lg border border-gray-200 dark:bg-[#131713] dark:border-gray-800">
                  <div className="p-3 border-b border-gray-200 dark:border-gray-800">
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                      <Users size={14} className="text-gray-400" />
                      Switch Team
                    </h3>
                    <p className="text-xs text-gray-500 mt-0.5">{teams.length} team{teams.length !== 1 ? 's' : ''} available</p>
                  </div>
                  <div className="max-h-64 overflow-y-auto py-1">
                    {teams.map((team) => (
                      <button
                        key={team.id}
                        onClick={() => handleTeamSwitch(team)}
                        disabled={switchingTeam}
                        className={`w-full flex items-center gap-3 px-3 py-2.5 hover:bg-gray-50 dark:hover:bg-[#1a1f1a] transition-colors disabled:opacity-50 ${
                          currentTeam?.id === team.id ? 'bg-brand-500/5' : ''
                        }`}
                        data-testid={`team-option-${team.id}`}
                      >
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                          currentTeam?.id === team.id
                            ? 'bg-brand-500/20 border border-brand-500/30'
                            : 'bg-gray-100 dark:bg-white/5'
                        }`}>
                          <Building2 size={16} className={currentTeam?.id === team.id ? 'text-brand-400' : 'text-gray-400'} />
                        </div>
                        <div className="flex-1 text-left">
                          <p className={`text-sm font-medium ${
                            currentTeam?.id === team.id ? 'text-brand-400' : 'text-gray-800 dark:text-gray-200'
                          }`}>
                            {team.name}
                          </p>
                          <p className="text-xs text-gray-500 flex items-center gap-1">
                            <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] ${
                              team.role === 'Admin' ? 'bg-brand-500/10 text-brand-400' :
                              team.role === 'Developer' ? 'bg-success-500/10 text-success-400' :
                              'bg-gray-500/10 text-gray-400'
                            }`}>
                              {team.role}
                            </span>
                            <span>• {team.member_count} member{team.member_count !== 1 ? 's' : ''}</span>
                          </p>
                        </div>
                        {currentTeam?.id === team.id && (
                          <Check size={16} className="text-brand-400" />
                        )}
                      </button>
                    ))}
                  </div>
                  <div className="p-2 border-t border-gray-200 dark:border-gray-800">
                    <Link
                      to={`${basePath}/teams`}
                      className="flex items-center justify-center gap-2 w-full px-3 py-2 text-sm text-brand-500 hover:text-brand-600 hover:bg-brand-500/5 rounded-lg font-medium transition-colors"
                      onClick={() => setTeamSelectorOpen(false)}
                    >
                      <Users size={14} />
                      Manage Teams
                    </Link>
                  </div>
                </div>
              )}
            </div>
          )}

          {teams.length > 0 && <div className="h-8 w-px bg-white/10 hidden md:block" />}

          {/* TODO: Dark Mode Toggle - será implementado no futuro
          <button
            onClick={toggleTheme}
            className="flex items-center justify-center w-10 h-10 text-gray-500 rounded-lg hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-[#1a1f1a]"
            aria-label="Toggle Dark Mode"
          >
            {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
          </button>
          */}

          {/* Currency Selector */}
          <CurrencySelector compact />

          {/* Notifications */}
          <div className="relative" ref={notificationRef}>
            <button
              onClick={() => setNotificationOpen(!isNotificationOpen)}
              className="relative flex items-center justify-center w-10 h-10 text-gray-500 rounded-lg hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-[#1a1f1a]"
              aria-label="Notifications"
            >
              <Bell size={20} />
              <span className="absolute top-2 right-2 w-2 h-2 bg-error-500 rounded-full"></span>
            </button>

            {/* Notification Dropdown */}
            {isNotificationOpen && (
              <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-theme-lg border border-gray-200 dark:bg-[#131713] dark:border-gray-800">
                <div className="p-4 border-b border-gray-200 dark:border-gray-800">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Notificações</h3>
                </div>
                <div className="max-h-80 overflow-y-auto">
                  <div className="p-4 hover:bg-gray-50 dark:hover:bg-[#1a1f1a] border-b border-gray-100 dark:border-gray-800">
                    <p className="text-sm text-gray-800 dark:text-gray-200">Sua máquina GPU entrou em standby</p>
                    <p className="text-xs text-gray-500 mt-1">Há 2 minutos</p>
                  </div>
                  <div className="p-4 hover:bg-gray-50 dark:hover:bg-[#1a1f1a]">
                    <p className="text-sm text-gray-800 dark:text-gray-200">Economia de $12.50 hoje</p>
                    <p className="text-xs text-gray-500 mt-1">Há 1 hora</p>
                  </div>
                </div>
                <div className="p-3 border-t border-gray-200 dark:border-gray-800">
                  <Link
                    to={`${basePath}/settings`}
                    className="text-sm text-brand-500 hover:text-brand-600 font-medium"
                    onClick={() => setNotificationOpen(false)}
                  >
                    Ver todas
                  </Link>
                </div>
              </div>
            )}
          </div>

          {/* User Menu */}
          <div className="relative" ref={userMenuRef}>
            <button
              onClick={() => setUserMenuOpen(!isUserMenuOpen)}
              className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-[#1a1f1a]"
            >
              <div className="w-8 h-8 bg-brand-500 rounded-lg flex items-center justify-center shadow-lg shadow-brand-500/20">
                <User size={18} className="text-white" />
              </div>
              <div className="hidden md:block text-left">
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  {user?.username?.split('@')[0] || 'Usuário'}
                </p>
                <p className="text-xs text-gray-500">
                  {isDemo ? 'Demo Mode' : 'Admin'}
                </p>
              </div>
              <ChevronDown size={16} className="text-gray-400 hidden md:block" />
            </button>

            {/* User Dropdown */}
            {isUserMenuOpen && (
              <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-theme-lg border border-gray-200 dark:bg-[#131713] dark:border-gray-800">
                <div className="p-4 border-b border-gray-200 dark:border-gray-800">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {user?.username || 'Usuário'}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {isDemo ? 'Conta Demo' : 'Conta Pro'}
                  </p>
                </div>
                <div className="p-2">
                  <Link
                    to={`${basePath}/settings`}
                    className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 rounded-lg hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-[#1a1f1a]"
                    onClick={() => setUserMenuOpen(false)}
                  >
                    <User size={16} />
                    Meu Perfil
                  </Link>
                  <button
                    onClick={() => {
                      setUserMenuOpen(false);
                      onLogout();
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-error-600 rounded-lg hover:bg-error-50 dark:text-error-400 dark:hover:bg-error-500/10"
                  >
                    <LogOut size={16} />
                    {isDemo ? 'Sair do Demo' : 'Logout'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

export default AppHeader;
