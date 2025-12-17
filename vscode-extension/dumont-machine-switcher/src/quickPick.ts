import * as vscode from 'vscode';
import { Machine } from './machineService';

interface MachineQuickPickItem extends vscode.QuickPickItem {
    machine?: Machine;
    action?: 'new' | 'manage';
}

export class MachineQuickPick {
    private machines: Machine[];
    private currentMachine: Machine | null;

    constructor(machines: Machine[], currentMachine: Machine | null) {
        this.machines = machines;
        this.currentMachine = currentMachine;
    }

    async show(): Promise<Machine | { id: string } | undefined> {
        const quickPick = vscode.window.createQuickPick<MachineQuickPickItem>();
        quickPick.title = 'Select Machine';
        quickPick.placeholder = 'Choose a GPU machine to connect to...';
        quickPick.matchOnDescription = true;
        quickPick.matchOnDetail = true;

        // Build items
        const items: MachineQuickPickItem[] = [];

        // Running machines section
        const runningMachines = this.machines.filter(m => m.actual_status === 'running');
        if (runningMachines.length > 0) {
            items.push({
                label: 'Online Machines',
                kind: vscode.QuickPickItemKind.Separator
            });

            for (const machine of runningMachines) {
                items.push(this.createMachineItem(machine));
            }
        }

        // Stopped machines section
        const stoppedMachines = this.machines.filter(m => m.actual_status !== 'running');
        if (stoppedMachines.length > 0) {
            items.push({
                label: 'Offline Machines',
                kind: vscode.QuickPickItemKind.Separator
            });

            for (const machine of stoppedMachines) {
                items.push(this.createMachineItem(machine));
            }
        }

        // Actions section
        items.push({
            label: 'Actions',
            kind: vscode.QuickPickItemKind.Separator
        });

        items.push({
            label: '$(add) Create New Machine',
            description: 'Open Dumont Cloud dashboard',
            action: 'new'
        });

        items.push({
            label: '$(server) Manage Machines',
            description: 'Open machines page',
            action: 'manage'
        });

        quickPick.items = items;

        return new Promise<Machine | { id: string } | undefined>((resolve) => {
            quickPick.onDidAccept(() => {
                const selected = quickPick.selectedItems[0];
                quickPick.hide();

                if (selected?.machine) {
                    resolve(selected.machine);
                } else if (selected?.action) {
                    resolve({ id: selected.action });
                } else {
                    resolve(undefined);
                }
            });

            quickPick.onDidHide(() => {
                quickPick.dispose();
                resolve(undefined);
            });

            quickPick.show();
        });
    }

    private createMachineItem(machine: Machine): MachineQuickPickItem {
        const isCurrent = this.currentMachine?.id === machine.id;
        const statusIcon = machine.actual_status === 'running' ? '$(vm-running)' : '$(vm-outline)';
        const gpuName = this.formatGpuName(machine);
        const vram = Math.round((machine.gpu_ram || 24000) / 1024);
        const price = machine.dph_total?.toFixed(2) || '0.00';

        let description = `${vram}GB VRAM`;
        if (machine.actual_status === 'running') {
            description += ` | $${price}/h`;
            if (machine.gpu_util !== undefined) {
                description += ` | GPU: ${machine.gpu_util}%`;
            }
        } else {
            description += ` | ${machine.actual_status}`;
        }

        return {
            label: `${statusIcon} ${gpuName}`,
            description: description,
            detail: machine.public_ipaddr ? `IP: ${machine.public_ipaddr}` : undefined,
            picked: isCurrent,
            machine: machine
        };
    }

    private formatGpuName(machine: Machine): string {
        const gpu = machine.gpu_name || 'CPU';
        const numGpus = machine.num_gpus || 1;
        return numGpus > 1 ? `${numGpus}x ${gpu}` : gpu;
    }
}
