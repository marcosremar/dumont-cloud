/**
 * Time Formatting Utilities
 */

/**
 * Format seconds as mm:ss
 */
export function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Format time ago (e.g., "30 min atrás", "1 dia atrás")
 */
export function getTimeAgo(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 60) return `${diffMins} min atrás`;
  if (diffHours < 24) return `${diffHours}h atrás`;
  if (diffDays === 1) return 'Ontem';
  if (diffDays < 7) return `${diffDays} dias atrás`;
  return `${Math.floor(diffDays / 7)} semana(s) atrás`;
}

/**
 * Estimate remaining time based on progress
 */
export function getETA(
  elapsedTime: number,
  candidates: Array<{ status: string; progress?: number }>,
  hasWinner: boolean
): string {
  if (hasWinner) return 'Concluído!';

  const activeCandidates = candidates.filter((c) => c.status !== 'failed');
  if (activeCandidates.length === 0) return 'Sem máquinas ativas';

  const maxProgress = Math.max(...activeCandidates.map((c) => c.progress || 0));
  if (maxProgress <= 10 || elapsedTime < 3) return 'Estimando...';

  const estimatedTotal = (elapsedTime / maxProgress) * 100;
  const remaining = Math.max(0, Math.ceil(estimatedTotal - elapsedTime));

  if (remaining < 60) return `~${remaining}s restantes`;
  return `~${Math.ceil(remaining / 60)}min restantes`;
}

/**
 * Format date for display
 */
export function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default {
  formatTime,
  getTimeAgo,
  getETA,
  formatDate,
};
