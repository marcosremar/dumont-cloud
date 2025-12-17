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
exports.MachineQuickPick = void 0;
const vscode = __importStar(require("vscode"));
class MachineQuickPick {
    constructor(machines, currentMachine) {
        this.machines = machines;
        this.currentMachine = currentMachine;
    }
    async show() {
        const quickPick = vscode.window.createQuickPick();
        quickPick.title = 'Select Machine';
        quickPick.placeholder = 'Choose a GPU machine to connect to...';
        quickPick.matchOnDescription = true;
        quickPick.matchOnDetail = true;
        // Build items
        const items = [];
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
        return new Promise((resolve) => {
            quickPick.onDidAccept(() => {
                const selected = quickPick.selectedItems[0];
                quickPick.hide();
                if (selected?.machine) {
                    resolve(selected.machine);
                }
                else if (selected?.action) {
                    resolve({ id: selected.action });
                }
                else {
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
    createMachineItem(machine) {
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
        }
        else {
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
    formatGpuName(machine) {
        const gpu = machine.gpu_name || 'CPU';
        const numGpus = machine.num_gpus || 1;
        return numGpus > 1 ? `${numGpus}x ${gpu}` : gpu;
    }
}
exports.MachineQuickPick = MachineQuickPick;
//# sourceMappingURL=quickPick.js.map