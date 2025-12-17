"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.MachineService = void 0;
class MachineService {
    constructor(context) {
        this.apiUrl = '';
        this.authToken = '';
        this.machines = [];
        this.context = context;
    }
    configure(apiUrl, authToken) {
        this.apiUrl = apiUrl.replace(/\/$/, ''); // Remove trailing slash
        this.authToken = authToken;
    }
    isConfigured() {
        return !!(this.apiUrl && this.authToken);
    }
    async fetchMachines() {
        if (!this.isConfigured()) {
            throw new Error('Dumont API not configured');
        }
        const response = await fetch(`${this.apiUrl}/api/instances`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${this.authToken}`,
                'Content-Type': 'application/json'
            }
        });
        if (!response.ok) {
            throw new Error(`API error: ${response.status} ${response.statusText}`);
        }
        const data = await response.json();
        this.machines = data.instances || [];
        return this.machines;
    }
    getMachines() {
        return this.machines;
    }
    getRunningMachines() {
        return this.machines.filter(m => m.actual_status === 'running');
    }
    getStoppedMachines() {
        return this.machines.filter(m => m.actual_status !== 'running');
    }
    async startMachine(machineId) {
        if (!this.isConfigured()) {
            throw new Error('Dumont API not configured');
        }
        const response = await fetch(`${this.apiUrl}/api/instances/${machineId}/resume`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.authToken}`,
                'Content-Type': 'application/json'
            }
        });
        if (!response.ok) {
            throw new Error(`Failed to start machine: ${response.status} ${response.statusText}`);
        }
    }
    async stopMachine(machineId) {
        if (!this.isConfigured()) {
            throw new Error('Dumont API not configured');
        }
        const response = await fetch(`${this.apiUrl}/api/instances/${machineId}/pause`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.authToken}`,
                'Content-Type': 'application/json'
            }
        });
        if (!response.ok) {
            throw new Error(`Failed to stop machine: ${response.status} ${response.statusText}`);
        }
    }
}
exports.MachineService = MachineService;
//# sourceMappingURL=machineService.js.map