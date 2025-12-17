import * as vscode from 'vscode';
import { MachineService, Machine } from './machineService';

export class MachinesViewProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'dumont.machinesList';
    private _view?: vscode.WebviewView;
    private machineService: MachineService;

    constructor(
        private readonly _extensionUri: vscode.Uri,
        machineService: MachineService
    ) {
        this.machineService = machineService;
    }

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken
    ) {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri]
        };

        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);

        // Handle messages from the webview
        webviewView.webview.onDidReceiveMessage(async (data) => {
            switch (data.type) {
                case 'selectMachine':
                    await this.selectMachine(data.machineId);
                    break;
                case 'startMachine':
                    await this.startMachine(data.machineId);
                    break;
                case 'refresh':
                    await this.refresh();
                    break;
                case 'openDashboard':
                    this.openDashboard();
                    break;
            }
        });

        // Initial load
        this.refresh();
    }

    public async refresh() {
        if (!this._view) return;

        try {
            await this.machineService.fetchMachines();
            const machines = this.machineService.getMachines();
            this._view.webview.postMessage({ type: 'updateMachines', machines });
        } catch (error) {
            this._view.webview.postMessage({ type: 'error', message: String(error) });
        }
    }

    private async selectMachine(machineId: number) {
        const machines = this.machineService.getMachines();
        const machine = machines.find(m => m.id === machineId);

        if (!machine) return;

        if (machine.actual_status !== 'running') {
            const action = await vscode.window.showWarningMessage(
                `Machine "${machine.gpu_name}" is offline. Start it?`,
                'Start',
                'Cancel'
            );
            if (action === 'Start') {
                await this.startMachine(machineId);
            }
            return;
        }

        // Open VS Code on the machine
        const ports = machine.ports || {};
        const port8080 = ports['8080/tcp'];

        if (port8080 && port8080[0] && machine.public_ipaddr) {
            const hostPort = port8080[0].HostPort;
            const url = `http://${machine.public_ipaddr}:${hostPort}/`;
            vscode.env.openExternal(vscode.Uri.parse(url));
        }

        vscode.window.showInformationMessage(`Connected to ${machine.gpu_name}`);
    }

    private async startMachine(machineId: number) {
        try {
            await this.machineService.startMachine(machineId);
            vscode.window.showInformationMessage('Machine is starting...');

            // Refresh after a delay
            setTimeout(() => this.refresh(), 5000);
        } catch (error) {
            vscode.window.showErrorMessage(`Failed to start machine: ${error}`);
        }
    }

    private openDashboard() {
        const config = vscode.workspace.getConfiguration('dumont');
        const apiUrl = config.get<string>('apiUrl') || '';
        if (apiUrl) {
            const dashboardUrl = apiUrl.replace('/api', '').replace(':5000', ':5173');
            vscode.env.openExternal(vscode.Uri.parse(dashboardUrl));
        }
    }

    private _getHtmlForWebview(webview: vscode.Webview): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dumont Machines</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: var(--vscode-font-family);
            font-size: var(--vscode-font-size);
            color: var(--vscode-foreground);
            background: var(--vscode-sideBar-background);
            padding: 8px;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--vscode-panel-border);
        }
        .header h3 {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--vscode-sideBarSectionHeader-foreground);
        }
        .header-actions {
            display: flex;
            gap: 4px;
        }
        .icon-btn {
            background: none;
            border: none;
            color: var(--vscode-foreground);
            cursor: pointer;
            padding: 4px;
            border-radius: 4px;
            opacity: 0.7;
        }
        .icon-btn:hover {
            opacity: 1;
            background: var(--vscode-toolbar-hoverBackground);
        }
        .section {
            margin-bottom: 16px;
        }
        .section-title {
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--vscode-descriptionForeground);
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .section-title .dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
        }
        .section-title .dot.online {
            background: #4ade80;
            box-shadow: 0 0 6px #4ade80;
        }
        .section-title .dot.offline {
            background: #6b7280;
        }
        .machine-card {
            background: var(--vscode-editor-background);
            border: 1px solid var(--vscode-panel-border);
            border-radius: 6px;
            padding: 10px;
            margin-bottom: 8px;
            cursor: pointer;
            transition: all 0.15s ease;
        }
        .machine-card:hover {
            border-color: var(--vscode-focusBorder);
            background: var(--vscode-list-hoverBackground);
        }
        .machine-card.selected {
            border-color: #4ade80;
            background: rgba(74, 222, 128, 0.1);
        }
        .machine-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }
        .machine-name {
            font-weight: 600;
            font-size: 13px;
            color: var(--vscode-foreground);
        }
        .machine-status {
            font-size: 9px;
            font-weight: 600;
            text-transform: uppercase;
            padding: 2px 6px;
            border-radius: 3px;
        }
        .machine-status.online {
            background: rgba(74, 222, 128, 0.2);
            color: #4ade80;
        }
        .machine-status.offline {
            background: rgba(107, 114, 128, 0.2);
            color: #9ca3af;
        }
        .machine-specs {
            font-size: 11px;
            color: var(--vscode-descriptionForeground);
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        .machine-specs span {
            background: var(--vscode-badge-background);
            padding: 2px 6px;
            border-radius: 3px;
        }
        .machine-price {
            margin-top: 6px;
            font-size: 12px;
            color: #fbbf24;
            font-weight: 500;
        }
        .empty-state {
            text-align: center;
            padding: 24px 12px;
            color: var(--vscode-descriptionForeground);
        }
        .empty-state svg {
            width: 48px;
            height: 48px;
            margin-bottom: 12px;
            opacity: 0.5;
        }
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            padding: 6px 12px;
            font-size: 12px;
            font-weight: 500;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.15s ease;
        }
        .btn-primary {
            background: #4ade80;
            color: #000;
        }
        .btn-primary:hover {
            background: #22c55e;
        }
        .btn-secondary {
            background: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
        }
        .btn-secondary:hover {
            background: var(--vscode-button-secondaryHoverBackground);
        }
        .footer {
            margin-top: 16px;
            padding-top: 12px;
            border-top: 1px solid var(--vscode-panel-border);
            display: flex;
            gap: 8px;
        }
        .footer .btn {
            flex: 1;
        }
        .loading {
            text-align: center;
            padding: 24px;
            color: var(--vscode-descriptionForeground);
        }
        .error {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: #ef4444;
            padding: 12px;
            border-radius: 6px;
            font-size: 12px;
            margin-bottom: 12px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h3>GPU Machines</h3>
        <div class="header-actions">
            <button class="icon-btn" onclick="refresh()" title="Refresh">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                    <path d="M13.451 5.609l-.579-.939-1.068.812-.076.094c-.335.415-.927 1.341-1.124 2.876l-.021.165.033.163.071.345c.024.097.039.136.054.177.011.03.023.059.048.158l.02.057.024.052a2.958 2.958 0 0 0 3.442 1.499l.166-.06-.018-1.254-.143.035a1.87 1.87 0 0 1-1.417-.258 1.859 1.859 0 0 1-.387-.395l-.015-.022.013-.034a5.113 5.113 0 0 1 .642-1.484l.063-.1 1.058-.847.582.935.96-.66-.3-1.545zM8 3a4.983 4.983 0 0 1 4.293 2.455l.676-.537A5.985 5.985 0 0 0 8 2a6 6 0 1 0 6 6h-1a5 5 0 1 1-5-5z"/>
                </svg>
            </button>
        </div>
    </div>

    <div id="error-container"></div>
    <div id="content">
        <div class="loading">Loading machines...</div>
    </div>

    <div class="footer">
        <button class="btn btn-primary" onclick="openDashboard()">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                <path d="M14 1H2a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1zM2 0a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2H2z"/>
                <path d="M8 4a.5.5 0 0 1 .5.5v3h3a.5.5 0 0 1 0 1h-3v3a.5.5 0 0 1-1 0v-3h-3a.5.5 0 0 1 0-1h3v-3A.5.5 0 0 1 8 4z"/>
            </svg>
            New Machine
        </button>
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        let machines = [];

        function refresh() {
            vscode.postMessage({ type: 'refresh' });
        }

        function selectMachine(machineId) {
            vscode.postMessage({ type: 'selectMachine', machineId });
        }

        function startMachine(machineId) {
            vscode.postMessage({ type: 'startMachine', machineId });
        }

        function openDashboard() {
            vscode.postMessage({ type: 'openDashboard' });
        }

        function renderMachines() {
            const content = document.getElementById('content');

            if (machines.length === 0) {
                content.innerHTML = \`
                    <div class="empty-state">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M5 12h14M12 5v14"/>
                        </svg>
                        <p>No machines found</p>
                        <p style="font-size: 11px; margin-top: 8px;">Create a new GPU machine to get started</p>
                    </div>
                \`;
                return;
            }

            const online = machines.filter(m => m.actual_status === 'running');
            const offline = machines.filter(m => m.actual_status !== 'running');

            let html = '';

            if (online.length > 0) {
                html += \`
                    <div class="section">
                        <div class="section-title">
                            <span class="dot online"></span>
                            Online (\${online.length})
                        </div>
                        \${online.map(m => renderMachineCard(m)).join('')}
                    </div>
                \`;
            }

            if (offline.length > 0) {
                html += \`
                    <div class="section">
                        <div class="section-title">
                            <span class="dot offline"></span>
                            Offline (\${offline.length})
                        </div>
                        \${offline.map(m => renderMachineCard(m)).join('')}
                    </div>
                \`;
            }

            content.innerHTML = html;
        }

        function renderMachineCard(machine) {
            const isOnline = machine.actual_status === 'running';
            const vram = Math.round((machine.gpu_ram || 24000) / 1024);
            const price = machine.dph_total?.toFixed(2) || '0.00';
            const gpuName = machine.num_gpus > 1
                ? \`\${machine.num_gpus}x \${machine.gpu_name}\`
                : machine.gpu_name;

            return \`
                <div class="machine-card" onclick="selectMachine(\${machine.id})">
                    <div class="machine-header">
                        <span class="machine-name">\${gpuName}</span>
                        <span class="machine-status \${isOnline ? 'online' : 'offline'}">
                            \${isOnline ? 'Online' : machine.actual_status}
                        </span>
                    </div>
                    <div class="machine-specs">
                        <span>\${vram}GB VRAM</span>
                        <span>\${machine.cpu_cores || 4} CPU</span>
                    </div>
                    <div class="machine-price">$\${price}/hour</div>
                </div>
            \`;
        }

        window.addEventListener('message', event => {
            const message = event.data;
            switch (message.type) {
                case 'updateMachines':
                    machines = message.machines || [];
                    document.getElementById('error-container').innerHTML = '';
                    renderMachines();
                    break;
                case 'error':
                    document.getElementById('error-container').innerHTML = \`
                        <div class="error">\${message.message}</div>
                    \`;
                    break;
            }
        });

        // Initial refresh
        refresh();
    </script>
</body>
</html>`;
    }
}
