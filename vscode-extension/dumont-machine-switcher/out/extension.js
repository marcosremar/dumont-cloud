"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const machineService_1 = require("./machineService");
const statusBar_1 = require("./statusBar");
const quickPick_1 = require("./quickPick");
const machinesViewProvider_1 = require("./machinesViewProvider");
let machineService;
let statusBarManager;
let machinesViewProvider;
let refreshInterval;
function activate(context) {
    console.log('Dumont Machine Switcher is now active');
    // Initialize services
    machineService = new machineService_1.MachineService(context);
    statusBarManager = new statusBar_1.StatusBarManager();
    // Register webview provider for sidebar
    machinesViewProvider = new machinesViewProvider_1.MachinesViewProvider(context.extensionUri, machineService);
    context.subscriptions.push(vscode.window.registerWebviewViewProvider(machinesViewProvider_1.MachinesViewProvider.viewType, machinesViewProvider));
    // Register commands
    const switchCommand = vscode.commands.registerCommand('dumont.switchMachine', async () => {
        await showMachinePicker();
    });
    const refreshCommand = vscode.commands.registerCommand('dumont.refreshMachines', async () => {
        await refreshMachines();
        machinesViewProvider.refresh();
    });
    const openPanelCommand = vscode.commands.registerCommand('dumont.openPanel', async () => {
        // Focus the sidebar view
        vscode.commands.executeCommand('dumont.machinesList.focus');
    });
    context.subscriptions.push(switchCommand, refreshCommand, openPanelCommand);
    context.subscriptions.push(statusBarManager.statusBarItem);
    // Initial load
    initializeExtension();
    // Auto-refresh every 30 seconds
    refreshInterval = setInterval(() => {
        refreshMachines(true);
        machinesViewProvider.refresh();
    }, 30000);
}
async function initializeExtension() {
    // Try to get config from environment or settings
    const config = vscode.workspace.getConfiguration('dumont');
    let apiUrl = config.get('apiUrl') || process.env.DUMONT_API_URL || '';
    let authToken = config.get('authToken') || process.env.DUMONT_AUTH_TOKEN || '';
    const currentMachineId = config.get('currentMachineId') || process.env.DUMONT_MACHINE_ID || '';
    // Try to read from config file if not set
    if (!apiUrl || !authToken) {
        const configFromFile = await readDumontConfig();
        if (configFromFile) {
            apiUrl = apiUrl || configFromFile.apiUrl;
            authToken = authToken || configFromFile.authToken;
        }
    }
    if (apiUrl && authToken) {
        machineService.configure(apiUrl, authToken);
        await refreshMachines();
        // Set current machine if known
        if (currentMachineId) {
            const machines = machineService.getMachines();
            const current = machines.find(m => m.id.toString() === currentMachineId);
            if (current) {
                statusBarManager.updateCurrentMachine(current);
            }
        }
    }
    else {
        statusBarManager.showNotConfigured();
    }
}
async function readDumontConfig() {
    try {
        const fs = require('fs');
        const path = require('path');
        const configPath = path.join(process.env.HOME || '/root', '.dumont', 'config.json');
        if (fs.existsSync(configPath)) {
            const content = fs.readFileSync(configPath, 'utf-8');
            const config = JSON.parse(content);
            return {
                apiUrl: config.api_url || config.apiUrl || '',
                authToken: config.auth_token || config.authToken || ''
            };
        }
    }
    catch (e) {
        console.error('Failed to read Dumont config:', e);
    }
    return null;
}
async function refreshMachines(silent = false) {
    try {
        if (!silent) {
            statusBarManager.showLoading();
        }
        await machineService.fetchMachines();
        const machines = machineService.getMachines();
        // Update status bar with current machine or first running
        const current = statusBarManager.getCurrentMachine();
        if (current) {
            const updated = machines.find(m => m.id === current.id);
            if (updated) {
                statusBarManager.updateCurrentMachine(updated);
            }
        }
        else {
            const running = machines.find(m => m.actual_status === 'running');
            if (running) {
                statusBarManager.updateCurrentMachine(running);
            }
            else if (machines.length > 0) {
                statusBarManager.updateCurrentMachine(machines[0]);
            }
        }
    }
    catch (error) {
        if (!silent) {
            // Don't show error popup, just update status bar
            console.error('Failed to fetch machines:', error);
        }
        statusBarManager.showError();
    }
}
async function showMachinePicker() {
    const machines = machineService.getMachines();
    if (machines.length === 0) {
        const action = await vscode.window.showWarningMessage('No machines found. Would you like to refresh?', 'Refresh', 'Configure');
        if (action === 'Refresh') {
            await refreshMachines();
            machinesViewProvider.refresh();
            if (machineService.getMachines().length > 0) {
                await showMachinePicker();
            }
        }
        else if (action === 'Configure') {
            vscode.commands.executeCommand('workbench.action.openSettings', 'dumont');
        }
        return;
    }
    const quickPick = new quickPick_1.MachineQuickPick(machines, statusBarManager.getCurrentMachine());
    const selected = await quickPick.show();
    if (selected) {
        if (selected.id === 'new') {
            // Open Dumont Cloud dashboard to create new machine
            const config = vscode.workspace.getConfiguration('dumont');
            const apiUrl = config.get('apiUrl') || '';
            if (apiUrl) {
                const dashboardUrl = apiUrl.replace('/api', '').replace(':5000', ':5173');
                vscode.env.openExternal(vscode.Uri.parse(dashboardUrl));
            }
        }
        else if (selected.id === 'manage') {
            // Open machines page
            const config = vscode.workspace.getConfiguration('dumont');
            const apiUrl = config.get('apiUrl') || '';
            if (apiUrl) {
                const machinesUrl = apiUrl.replace('/api', '').replace(':5000', ':5173') + '/machines';
                vscode.env.openExternal(vscode.Uri.parse(machinesUrl));
            }
        }
        else {
            // Switch to selected machine
            await switchToMachine(selected);
        }
    }
}
async function switchToMachine(machine) {
    if (machine.actual_status !== 'running') {
        const action = await vscode.window.showWarningMessage(`Machine "${machine.gpu_name}" is ${machine.actual_status}. Would you like to start it?`, 'Start Machine', 'Cancel');
        if (action === 'Start Machine') {
            try {
                statusBarManager.showLoading('Starting...');
                await machineService.startMachine(machine.id);
                vscode.window.showInformationMessage(`Starting ${machine.gpu_name}... This may take a moment.`);
                // Poll for machine to be running
                let attempts = 0;
                const maxAttempts = 30;
                const pollInterval = setInterval(async () => {
                    attempts++;
                    await machineService.fetchMachines();
                    const updated = machineService.getMachines().find(m => m.id === machine.id);
                    if (updated?.actual_status === 'running') {
                        clearInterval(pollInterval);
                        await connectToMachine(updated);
                    }
                    else if (attempts >= maxAttempts) {
                        clearInterval(pollInterval);
                        vscode.window.showErrorMessage('Machine failed to start in time. Please try again.');
                        statusBarManager.showError();
                    }
                }, 5000);
            }
            catch (error) {
                vscode.window.showErrorMessage(`Failed to start machine: ${error}`);
                statusBarManager.showError();
            }
        }
        return;
    }
    await connectToMachine(machine);
}
async function connectToMachine(machine) {
    statusBarManager.updateCurrentMachine(machine);
    // Save current machine ID
    const config = vscode.workspace.getConfiguration('dumont');
    await config.update('currentMachineId', machine.id.toString(), vscode.ConfigurationTarget.Global);
    // Get VS Code Online URL for the machine
    const ports = machine.ports || {};
    const port8080 = ports['8080/tcp'];
    if (port8080 && port8080[0] && machine.public_ipaddr) {
        const hostPort = port8080[0].HostPort;
        const url = `http://${machine.public_ipaddr}:${hostPort}/`;
        const action = await vscode.window.showInformationMessage(`Connected to ${machine.gpu_name}. Open in browser?`, 'Open VS Code', 'Copy URL');
        if (action === 'Open VS Code') {
            vscode.env.openExternal(vscode.Uri.parse(url));
        }
        else if (action === 'Copy URL') {
            vscode.env.clipboard.writeText(url);
            vscode.window.showInformationMessage('URL copied to clipboard');
        }
    }
    else {
        vscode.window.showInformationMessage(`Switched to ${machine.gpu_name}`);
    }
}
function deactivate() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
}
//# sourceMappingURL=extension.js.map