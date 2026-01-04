/**
 * Constants Index
 * Re-export all constants
 */

export * from './gpuData';
export * from './failoverOptions';
export * from './steps';
export * from './regionMapping';

// Tooltips for technical terms
export const TERM_TOOLTIPS: Record<string, string> = {
  warm_pool: 'GPU reservada e pronta para uso imediato',
  cpu_standby: 'CPU pequena que mantém dados sincronizados',
  snapshot: 'Backup compactado dos seus dados',
  serverless: 'Paga apenas quando a GPU está em uso',
  failover: 'Recuperação automática em caso de falha',
  rsync: 'Sincronização contínua de arquivos',
  lz4: 'Compressão rápida de dados',
};
