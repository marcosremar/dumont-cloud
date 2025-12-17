import * as vscode from 'vscode';
import { Machine } from './machineService';

export class StatusBarManager {
    public statusBarItem: vscode.StatusBarItem;
    private currentMachine: Machine | null = null;

    constructor() {
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            100
        );
        this.statusBarItem.command = 'dumont.switchMachine';
        this.statusBarItem.tooltip = 'Click to switch machine';
        this.showNotConfigured();
        this.statusBarItem.show();
    }

    updateCurrentMachine(machine: Machine) {
        this.currentMachine = machine;
        const gpuName = this.formatGpuName(machine);
        const statusIcon = machine.actual_status === 'running' ? '$(vm-running)' : '$(vm-outline)';
        const statusColor = machine.actual_status === 'running' ? 'statusBarItem.prominentBackground' : undefined;

        this.statusBarItem.text = `${statusIcon} ${gpuName}`;
        this.statusBarItem.tooltip = this.buildTooltip(machine);
        this.statusBarItem.backgroundColor = machine.actual_status === 'running'
            ? new vscode.ThemeColor('statusBarItem.prominentBackground')
            : undefined;
    }

    getCurrentMachine(): Machine | null {
        return this.currentMachine;
    }

    showLoading(message: string = 'Loading...') {
        this.statusBarItem.text = `$(sync~spin) ${message}`;
        this.statusBarItem.tooltip = 'Loading machines...';
    }

    showNotConfigured() {
        this.statusBarItem.text = '$(vm) Dumont: Configure';
        this.statusBarItem.tooltip = 'Click to configure Dumont Cloud';
    }

    showError() {
        this.statusBarItem.text = '$(vm) Dumont: Error';
        this.statusBarItem.tooltip = 'Failed to connect. Click to retry.';
    }

    showNoMachines() {
        this.statusBarItem.text = '$(vm) No machines';
        this.statusBarItem.tooltip = 'No machines found. Click to create one.';
    }

    private formatGpuName(machine: Machine): string {
        const gpu = machine.gpu_name || 'CPU';
        const numGpus = machine.num_gpus || 1;
        return numGpus > 1 ? `${numGpus}x ${gpu}` : gpu;
    }

    private buildTooltip(machine: Machine): vscode.MarkdownString {
        const md = new vscode.MarkdownString();
        md.isTrusted = true;

        const status = machine.actual_status === 'running' ? 'Online' : machine.actual_status;
        const statusEmoji = machine.actual_status === 'running' ? '🟢' : '🔴';
        const vram = Math.round((machine.gpu_ram || 24000) / 1024);
        const ram = machine.cpu_ram > 1000 ? Math.round(machine.cpu_ram / 1024) : Math.round(machine.cpu_ram);
        const price = machine.dph_total?.toFixed(2) || '0.00';

        md.appendMarkdown(`### ${this.formatGpuName(machine)}\n\n`);
        md.appendMarkdown(`${statusEmoji} **Status:** ${status}\n\n`);
        md.appendMarkdown(`**VRAM:** ${vram}GB | **RAM:** ${ram}GB | **CPU:** ${machine.cpu_cores} cores\n\n`);
        md.appendMarkdown(`**Price:** $${price}/hour\n\n`);

        if (machine.actual_status === 'running') {
            if (machine.gpu_util !== undefined) {
                md.appendMarkdown(`**GPU Usage:** ${machine.gpu_util}%\n\n`);
            }
            if (machine.gpu_temp !== undefined) {
                md.appendMarkdown(`**GPU Temp:** ${machine.gpu_temp}°C\n\n`);
            }
            if (machine.public_ipaddr) {
                md.appendMarkdown(`**IP:** ${machine.public_ipaddr}\n\n`);
            }
        }

        md.appendMarkdown(`---\n\n`);
        md.appendMarkdown(`*Click to switch machine*`);

        return md;
    }
}
