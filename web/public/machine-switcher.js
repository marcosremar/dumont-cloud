// Dumont Cloud Machine Switcher
// Este script é injetado no code-server para adicionar o botão de troca de máquinas

(function() {
  'use strict';

  // Configuração - será preenchida pelo backend
  const CONFIG = {
    apiUrl: window.DUMONT_API_URL || 'https://dumontcloud.com',
    authToken: window.DUMONT_AUTH_TOKEN || '',
    machineId: window.DUMONT_MACHINE_ID || ''
  };

  class MachineSwitcher {
    constructor() {
      this.container = null;
      this.isOpen = false;
      this.machines = [];
      this.currentMachine = null;
    }

    init() {
      // Esperar o VS Code carregar
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => this.mount());
      } else {
        this.mount();
      }
    }

    mount() {
      // Aguardar um pouco para garantir que o VS Code carregou
      setTimeout(() => {
        this.createWidget();
        this.addStyles();
        this.fetchMachines();
        setInterval(() => this.fetchMachines(), 30000);
      }, 2000);
    }

    createWidget() {
      this.container = document.createElement('div');
      this.container.className = 'dumont-machine-switcher';
      this.container.innerHTML = this.getButtonHTML();
      document.body.appendChild(this.container);

      this.container.addEventListener('click', (e) => {
        if (e.target.closest('.dumont-switcher-btn')) {
          this.toggle();
        }
      });

      document.addEventListener('click', (e) => {
        if (this.isOpen && !this.container.contains(e.target)) {
          this.close();
        }
      });
    }

    getButtonHTML() {
      const machine = this.currentMachine;
      const gpuName = machine?.gpu_name || 'GPU';
      const status = machine?.actual_status || 'unknown';
      const statusClass = status === 'running' ? 'online' : 'offline';

      return `
        <button class="dumont-switcher-btn">
          <svg class="dumont-switcher-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="3" width="20" height="14" rx="2"></rect>
            <line x1="8" y1="21" x2="16" y2="21"></line>
            <line x1="12" y1="17" x2="12" y2="21"></line>
          </svg>
          <span class="dumont-switcher-label">${gpuName}</span>
          <span class="dumont-switcher-status ${statusClass}"></span>
          <svg class="dumont-switcher-arrow" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </button>
      `;
    }

    getDropdownHTML() {
      const online = this.machines.filter(m => m.actual_status === 'running');
      const offline = this.machines.filter(m => m.actual_status !== 'running');

      let html = '<div class="dumont-dropdown"><div class="dumont-dropdown-header">Switch Machine</div>';

      if (this.machines.length === 0) {
        html += '<div class="dumont-dropdown-empty">No machines available</div>';
      } else {
        if (online.length > 0) {
          html += '<div class="dumont-dropdown-section"><div class="dumont-dropdown-section-title">● Online</div>';
          online.forEach(m => { html += this.getMachineItemHTML(m); });
          html += '</div>';
        }
        if (offline.length > 0) {
          html += '<div class="dumont-dropdown-section"><div class="dumont-dropdown-section-title">○ Offline</div>';
          offline.forEach(m => { html += this.getMachineItemHTML(m); });
          html += '</div>';
        }
      }

      html += '<div class="dumont-dropdown-footer">';
      html += '<a href="' + CONFIG.apiUrl + '/machines" target="_blank" class="dumont-dropdown-link">Manage</a>';
      html += '<a href="' + CONFIG.apiUrl + '/deploy" target="_blank" class="dumont-dropdown-link primary">+ New</a>';
      html += '</div></div>';
      return html;
    }

    getMachineItemHTML(m) {
      const selected = CONFIG.machineId && m.id.toString() === CONFIG.machineId;
      const statusClass = m.actual_status === 'running' ? 'online' : 'offline';
      const cost = m.hourly_cost ? '$' + m.hourly_cost.toFixed(2) + '/hr' : '';
      const specs = m.gpu_ram ? m.gpu_ram + 'GB' + (cost ? ' • ' + cost : '') : cost;

      return `
        <button class="dumont-dropdown-item ${selected ? 'selected' : ''}" data-id="${m.id}">
          <span class="dumont-dropdown-item-info">
            <span class="dumont-dropdown-item-name">${m.gpu_name || 'Machine ' + m.id}</span>
            <span class="dumont-dropdown-item-specs">${specs}</span>
          </span>
          <span class="dumont-status-badge ${statusClass}">${m.actual_status === 'running' ? 'On' : 'Off'}</span>
          ${selected ? '<span class="dumont-check">✓</span>' : ''}
        </button>
      `;
    }

    toggle() {
      this.isOpen ? this.close() : this.open();
    }

    open() {
      const existing = this.container.querySelector('.dumont-dropdown');
      if (existing) existing.remove();

      const dropdown = document.createElement('div');
      dropdown.innerHTML = this.getDropdownHTML();
      this.container.appendChild(dropdown.firstElementChild);
      this.isOpen = true;

      this.container.querySelectorAll('.dumont-dropdown-item').forEach(item => {
        item.addEventListener('click', (e) => {
          const id = e.currentTarget.dataset.id;
          if (id) this.selectMachine(parseInt(id));
        });
      });
    }

    close() {
      const dropdown = this.container.querySelector('.dumont-dropdown');
      if (dropdown) dropdown.remove();
      this.isOpen = false;
    }

    async fetchMachines() {
      try {
        const headers = {};
        if (CONFIG.authToken) {
          headers['Authorization'] = 'Bearer ' + CONFIG.authToken;
        }

        const res = await fetch(CONFIG.apiUrl + '/api/v1/instances', { headers });
        if (res.ok) {
          this.machines = await res.json();
          this.currentMachine = CONFIG.machineId
            ? this.machines.find(m => m.id.toString() === CONFIG.machineId)
            : this.machines.find(m => m.actual_status === 'running') || this.machines[0];
          this.updateButton();
        }
      } catch (e) {
        console.error('Dumont: Failed to fetch machines:', e);
      }
    }

    updateButton() {
      const btn = this.container.querySelector('.dumont-switcher-btn');
      if (btn) {
        const temp = document.createElement('div');
        temp.innerHTML = this.getButtonHTML();
        btn.replaceWith(temp.firstElementChild);
      }
    }

    async selectMachine(id) {
      const m = this.machines.find(x => x.id === id);
      if (!m) return;

      if (m.actual_status !== 'running') {
        alert('Machine "' + m.gpu_name + '" is offline. Please start it first.');
        this.close();
        return;
      }

      try {
        const headers = {};
        if (CONFIG.authToken) {
          headers['Authorization'] = 'Bearer ' + CONFIG.authToken;
        }

        const res = await fetch(CONFIG.apiUrl + '/api/v1/instances/' + id, { headers });
        if (res.ok) {
          const data = await res.json();
          if (data.vscode_url) {
            window.location.href = data.vscode_url;
          }
        }
      } catch (e) {
        alert('Failed to switch machine: ' + e.message);
      }
      this.close();
    }

    addStyles() {
      const style = document.createElement('style');
      style.textContent = `
        .dumont-machine-switcher {
          position: fixed;
          top: 9px;
          right: 50px;
          z-index: 100000;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }
        .dumont-switcher-btn {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 5px 12px;
          background: linear-gradient(135deg, #2d2d2d 0%, #1a1a1a 100%);
          border: 1px solid rgba(255,255,255,0.15);
          border-radius: 6px;
          color: #e0e0e0;
          font-size: 12px;
          cursor: pointer;
          transition: all 0.2s ease;
          box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }
        .dumont-switcher-btn:hover {
          background: linear-gradient(135deg, #3d3d3d 0%, #2a2a2a 100%);
          border-color: rgba(255,255,255,0.25);
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        }
        .dumont-switcher-icon {
          color: #3fb950;
        }
        .dumont-switcher-label {
          font-weight: 600;
          max-width: 120px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .dumont-switcher-status {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #7d8590;
        }
        .dumont-switcher-status.online {
          background: #3fb950;
          box-shadow: 0 0 8px rgba(63,185,80,0.6);
          animation: dumont-pulse 2s infinite;
        }
        @keyframes dumont-pulse {
          0%, 100% { opacity: 1; box-shadow: 0 0 8px rgba(63,185,80,0.6); }
          50% { opacity: 0.7; box-shadow: 0 0 12px rgba(63,185,80,0.8); }
        }
        .dumont-switcher-arrow {
          opacity: 0.6;
          transition: transform 0.2s;
        }
        .dumont-dropdown {
          position: absolute;
          top: calc(100% + 8px);
          right: 0;
          width: 300px;
          background: #1e1e1e;
          border: 1px solid rgba(255,255,255,0.12);
          border-radius: 12px;
          box-shadow: 0 12px 40px rgba(0,0,0,0.5);
          overflow: hidden;
          animation: dumont-slideDown 0.2s ease;
        }
        @keyframes dumont-slideDown {
          from { opacity: 0; transform: translateY(-10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .dumont-dropdown-header {
          padding: 14px 16px;
          font-size: 14px;
          font-weight: 600;
          color: #fff;
          border-bottom: 1px solid rgba(255,255,255,0.1);
          background: linear-gradient(135deg, #252525 0%, #1a1a1a 100%);
        }
        .dumont-dropdown-empty {
          padding: 32px 16px;
          text-align: center;
          color: #7d8590;
        }
        .dumont-dropdown-section {
          padding: 8px 0;
        }
        .dumont-dropdown-section-title {
          padding: 8px 16px 6px;
          font-size: 11px;
          font-weight: 700;
          color: #7d8590;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        .dumont-dropdown-item {
          display: flex;
          align-items: center;
          gap: 12px;
          width: 100%;
          padding: 12px 16px;
          background: none;
          border: none;
          cursor: pointer;
          text-align: left;
          color: #e0e0e0;
          transition: background 0.15s;
        }
        .dumont-dropdown-item:hover {
          background: rgba(255,255,255,0.06);
        }
        .dumont-dropdown-item.selected {
          background: rgba(63,185,80,0.12);
        }
        .dumont-dropdown-item-info {
          flex: 1;
          min-width: 0;
        }
        .dumont-dropdown-item-name {
          display: block;
          font-size: 13px;
          font-weight: 500;
        }
        .dumont-dropdown-item-specs {
          display: block;
          font-size: 11px;
          color: #7d8590;
          margin-top: 3px;
        }
        .dumont-status-badge {
          padding: 3px 8px;
          border-radius: 4px;
          font-size: 10px;
          font-weight: 700;
          text-transform: uppercase;
        }
        .dumont-status-badge.online {
          background: rgba(63,185,80,0.18);
          color: #3fb950;
        }
        .dumont-status-badge.offline {
          background: rgba(125,133,144,0.18);
          color: #7d8590;
        }
        .dumont-check {
          color: #3fb950;
          font-weight: bold;
          font-size: 14px;
        }
        .dumont-dropdown-footer {
          display: flex;
          justify-content: space-between;
          padding: 12px 16px;
          border-top: 1px solid rgba(255,255,255,0.1);
          background: rgba(0,0,0,0.25);
        }
        .dumont-dropdown-link {
          font-size: 12px;
          font-weight: 600;
          color: #7d8590;
          text-decoration: none;
          transition: color 0.15s;
        }
        .dumont-dropdown-link:hover {
          color: #e0e0e0;
        }
        .dumont-dropdown-link.primary {
          color: #3fb950;
        }
        .dumont-dropdown-link.primary:hover {
          color: #4ade80;
        }
      `;
      document.head.appendChild(style);
    }
  }

  // Iniciar quando o documento estiver pronto
  const switcher = new MachineSwitcher();
  switcher.init();

  // Expor globalmente para debug
  window.DumontMachineSwitcher = switcher;
})();
