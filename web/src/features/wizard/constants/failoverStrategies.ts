/**
 * Failover Strategies Constants
 * Defines available failover/recovery strategies with costs
 */

import { Database, Zap, Server, Cloud, AlertCircle } from 'lucide-react';
import { FailoverStrategy, FailoverStrategyId } from '../types';

export const FAILOVER_STRATEGIES: readonly FailoverStrategy[] = [
  {
    id: 'snapshot_only',
    name: 'Snapshot Only',
    provider: 'GCP + B2',
    icon: Database,
    description: 'Apenas snapshots automáticos. CPU GCP para restore quando necessário.',
    recoveryTime: '2-5 min',
    dataLoss: 'Até 60 min',
    costHour: '$0',
    costMonth: '~$0.50/mês',
    costDetail: 'Só storage B2 (~$0.50/mês)',
    howItWorks: 'Snapshots LZ4 automáticos a cada 60min para Backblaze B2. Quando falhar, CPU GCP restaura dados e nova GPU é provisionada.',
    features: [
      'Snapshots automáticos (60min)',
      'Storage B2 barato',
      'Sem máquina idle',
      'Recover on-demand',
    ],
    requirements: 'Nenhum extra',
    recommended: true,
    available: true,
  },
  {
    id: 'vast_warmpool',
    name: 'VAST.ai Warm Pool',
    provider: 'VAST.ai + GCP + B2',
    icon: Zap,
    description: 'Failover completo com GPU warm, CPU standby e snapshots automáticos.',
    recoveryTime: '30-90 seg',
    dataLoss: 'Zero',
    costHour: '+$0.03/h',
    costMonth: '~$22/mês',
    costDetail: 'CPU GCP $0.01/h + Volume VAST $0.02/h + B2 ~$0.50/mês',
    howItWorks: 'GPU #2 fica parada no mesmo host (volume compartilhado). CPU no GCP (e2-medium spot $0.01/h) faz rsync contínuo. Snapshots LZ4 vão para Backblaze B2 a cada 60min.',
    features: [
      'GPU warm pool no mesmo host',
      'CPU standby GCP (+$0.01/h)',
      'Volume persistente VAST (+$0.02/h)',
      'Snapshots B2 (~$0.50/mês)',
    ],
    requirements: 'Host VAST.ai com 2+ GPUs',
    available: true,
  },
  {
    id: 'cpu_standby_only',
    name: 'CPU Standby Only',
    provider: 'GCP + B2',
    icon: Server,
    description: 'CPU GCP mantém dados sincronizados. Sem GPU warm.',
    recoveryTime: '1-3 min',
    dataLoss: 'Mínima',
    costHour: '+$0.01/h',
    costMonth: '~$8/mês',
    costDetail: 'CPU GCP $0.01/h + B2 ~$0.50/mês',
    howItWorks: 'Snapshots LZ4 automáticos a cada 60min para Backblaze B2. CPU GCP (e2-medium spot $0.01/h) sempre ligada. Quando falhar, nova GPU é provisionada e dados restaurados.',
    features: [
      'Snapshots automáticos (60min)',
      'CPU standby GCP (+$0.01/h)',
      'Storage B2 (~$0.50/mês)',
      'Sem GPU idle',
    ],
    requirements: 'Nenhum extra',
    available: true,
  },
  {
    id: 'tensordock',
    name: 'Tensor Dock Serverless',
    provider: 'Tensor Dock + B2',
    icon: Cloud,
    description: 'Abordagem serverless-like. Paga só quando usa.',
    recoveryTime: '~2 min',
    dataLoss: 'Último snapshot',
    costHour: '+$0.001/h',
    costMonth: '~$1/mês',
    costDetail: 'Só storage B2 (~$0.50/mês) + custo GPU sob demanda',
    howItWorks: 'Snapshots automáticos para B2. Sem máquina idle. Quando precisar, GPU é provisionada sob demanda no Tensor Dock e dados restaurados.',
    features: [
      'Sem máquina idle ($0/h parado)',
      'Snapshots B2 (~$0.50/mês)',
      'GPU sob demanda',
      'Boot otimizado',
    ],
    requirements: 'Conta Tensor Dock',
    available: true,
  },
  {
    id: 'no_failover',
    name: 'Sem Failover',
    provider: 'Apenas GPU',
    icon: AlertCircle,
    description: 'Sem proteção contra falhas. Se a máquina cair, você perde todos os dados.',
    recoveryTime: 'Manual',
    dataLoss: 'Total',
    costHour: '$0',
    costMonth: '$0',
    costDetail: 'Sem custo extra, mas sem proteção',
    howItWorks: 'Apenas a GPU principal. Sem snapshots, sem backup, sem recuperação automática. Se houver falha de hardware ou interrupção, todos os dados serão perdidos.',
    features: [
      'Sem custo adicional',
      'Sem snapshots',
      'Sem recuperação',
      'Dados perdidos em falha',
    ],
    requirements: 'Nenhum',
    danger: true,
    available: true,
  },
] as const;

/**
 * Get strategy by ID
 */
export function getStrategyById(id: FailoverStrategyId): FailoverStrategy | undefined {
  return FAILOVER_STRATEGIES.find(s => s.id === id);
}

/**
 * Get default (recommended) strategy
 */
export function getDefaultStrategy(): FailoverStrategy {
  return FAILOVER_STRATEGIES.find(s => s.recommended) ?? FAILOVER_STRATEGIES[0];
}

/**
 * Get available strategies only
 */
export function getAvailableStrategies(): FailoverStrategy[] {
  return FAILOVER_STRATEGIES.filter(s => s.available && !s.comingSoon);
}

/**
 * Strategy IDs for validation
 */
export const STRATEGY_IDS: readonly FailoverStrategyId[] = [
  'snapshot_only',
  'vast_warmpool',
  'cpu_standby_only',
  'tensordock',
  'no_failover',
] as const;
