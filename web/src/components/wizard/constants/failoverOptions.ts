/**
 * Failover Strategy Options
 * Real failover strategies with costs and specifications
 */

import {
  Database,
  Zap,
  Server,
  Network,
  AlertCircle,
} from 'lucide-react';
import type { FailoverOption } from '../types/wizard.types';

export const FAILOVER_OPTIONS: FailoverOption[] = [
  {
    id: 'snapshot_only',
    name: 'Snapshot Only',
    provider: 'GCP + B2',
    icon: Database,
    description: 'Apenas snapshots automáticos. CPU GCP para restore quando necessário.',
    recoveryTime: '2-5 min',
    dataLoss: 'Até 60 min',
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
    recommended: false,
    available: true,
  },
  {
    id: 'tensordock',
    name: 'TensorDock Failover',
    provider: 'TensorDock + B2',
    icon: Network,
    description: 'Failover para GPU TensorDock. Preços competitivos com recuperação rápida.',
    recoveryTime: '1-3 min',
    dataLoss: 'Mínima',
    costHour: '+$0.02/h',
    costMonth: '~$15/mês',
    costDetail: 'GPU TensorDock standby $0.02/h + B2 ~$0.50/mês',
    howItWorks: 'GPU secundária fica em standby no TensorDock. Snapshots automáticos a cada 60min para B2. Em caso de falha, failover para TensorDock.',
    features: [
      'GPU standby TensorDock',
      'Preços competitivos',
      'Snapshots B2 automáticos',
      'Recuperação rápida',
    ],
    requirements: 'API Key TensorDock configurada',
    recommended: false,
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
    recommended: false,
    available: true,
    danger: true,
  },
];

/**
 * Get failover option by ID
 */
export function getFailoverOption(id: string): FailoverOption | undefined {
  return FAILOVER_OPTIONS.find((option) => option.id === id);
}

/**
 * Get recommended failover option
 */
export function getRecommendedFailover(): FailoverOption {
  return FAILOVER_OPTIONS.find((option) => option.recommended) || FAILOVER_OPTIONS[0];
}

export default FAILOVER_OPTIONS;
