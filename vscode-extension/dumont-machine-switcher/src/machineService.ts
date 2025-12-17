import * as vscode from 'vscode';

export interface Machine {
    id: number;
    gpu_name: string;
    num_gpus: number;
    gpu_ram: number;
    cpu_cores: number;
    cpu_ram: number;
    disk_space: number;
    dph_total: number;
    actual_status: string;
    public_ipaddr: string;
    ssh_host: string;
    ssh_port: number;
    ports: { [key: string]: Array<{ HostPort: string }> };
    gpu_util?: number;
    gpu_temp?: number;
    label?: string;
}

export class MachineService {
    private apiUrl: string = '';
    private authToken: string = '';
    private machines: Machine[] = [];
    private context: vscode.ExtensionContext;

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
    }

    configure(apiUrl: string, authToken: string) {
        this.apiUrl = apiUrl.replace(/\/$/, ''); // Remove trailing slash
        this.authToken = authToken;
    }

    isConfigured(): boolean {
        return !!(this.apiUrl && this.authToken);
    }

    async fetchMachines(): Promise<Machine[]> {
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

        const data = await response.json() as { instances: Machine[] };
        this.machines = data.instances || [];
        return this.machines;
    }

    getMachines(): Machine[] {
        return this.machines;
    }

    getRunningMachines(): Machine[] {
        return this.machines.filter(m => m.actual_status === 'running');
    }

    getStoppedMachines(): Machine[] {
        return this.machines.filter(m => m.actual_status !== 'running');
    }

    async startMachine(machineId: number): Promise<void> {
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

    async stopMachine(machineId: number): Promise<void> {
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
