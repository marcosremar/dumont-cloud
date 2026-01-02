/**
 * Provisioning Step Component
 *
 * Step 4: Shows provisioning race progress and results.
 */

import React from 'react';
import { Check, X, Loader2, Cpu, Clock, Timer, Rocket } from 'lucide-react';
import { ProvisioningCandidate, FailoverStrategy } from '../../types';

// ============================================================================
// Types
// ============================================================================

export interface ProvisioningStepProps {
  candidates: ProvisioningCandidate[];
  winner: ProvisioningCandidate | null;
  currentRound: number;
  maxRounds: number;
  elapsedTime: string;
  eta: string;
  selectedFailover?: FailoverStrategy;
}

// ============================================================================
// Sub-components
// ============================================================================

interface CandidateCardProps {
  candidate: ProvisioningCandidate;
  index: number;
  isWinner: boolean;
  isCancelled: boolean;
}

const CandidateCard: React.FC<CandidateCardProps> = ({
  candidate,
  index,
  isWinner,
  isCancelled,
}) => {
  const status = candidate.status;

  return (
    <div
      data-testid={`provisioning-candidate-${index}`}
      className={`relative overflow-hidden rounded-lg border transition-all ${
        isWinner
          ? 'border-brand-500 bg-brand-500/10'
          : isCancelled
          ? 'border-white/5 bg-white/[0.02] opacity-50'
          : status === 'failed'
          ? 'border-red-500/30 bg-red-500/5'
          : 'border-white/10 bg-white/5'
      }`}
    >
      {/* Progress bar */}
      {status === 'connecting' && !isWinner && !isCancelled && (
        <div
          className="absolute bottom-0 left-0 h-0.5 bg-brand-500 transition-all duration-300 ease-out"
          style={{ width: `${candidate.progress ?? 0}%` }}
        />
      )}

      <div className="p-3 flex items-center gap-3">
        {/* Position/Status Icon */}
        <div
          className={`flex-shrink-0 w-8 h-8 rounded-md flex items-center justify-center font-bold text-sm ${
            isWinner
              ? 'bg-brand-500/20 text-brand-400'
              : isCancelled
              ? 'bg-white/5 text-gray-600'
              : status === 'failed'
              ? 'bg-red-500/10 text-red-400'
              : 'bg-white/5 text-gray-400'
          }`}
        >
          {isWinner ? (
            <Check className="w-4 h-4" />
          ) : isCancelled ? (
            <X className="w-4 h-4" />
          ) : status === 'failed' ? (
            <X className="w-4 h-4" />
          ) : (
            <span>{index + 1}</span>
          )}
        </div>

        {/* Machine Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <Cpu className={`w-3.5 h-3.5 ${isWinner ? 'text-brand-400' : 'text-gray-500'}`} />
            <span
              className={`text-sm font-medium truncate ${
                isWinner ? 'text-gray-100' : 'text-gray-300'
              }`}
            >
              {candidate.gpu_name}
            </span>
            {candidate.num_gpus > 1 && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-gray-400">
                x{candidate.num_gpus}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 mt-0.5 text-[10px] text-gray-500">
            <span>{candidate.gpu_ram?.toFixed(0)}GB</span>
            <span>•</span>
            <span>{candidate.geolocation ?? candidate.location ?? 'Unknown'}</span>
            <span>•</span>
            <span className="text-brand-400 font-medium">
              ${candidate.dph_total?.toFixed(2)}/h
            </span>
          </div>
        </div>

        {/* Status Badge */}
        <div className="flex-shrink-0">
          {isWinner ? (
            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-brand-500/20 text-brand-400 text-[10px] font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-brand-400" />
              Conectado
            </span>
          ) : isCancelled ? (
            <span className="text-[10px] text-gray-600">Cancelado</span>
          ) : status === 'failed' ? (
            <div className="flex flex-col items-end">
              <span className="text-[10px] text-red-400">Falhou</span>
              {candidate.errorMessage && (
                <span className="text-[9px] text-red-400/70">{candidate.errorMessage}</span>
              )}
            </div>
          ) : (
            <span className="inline-flex items-center gap-1.5 text-[10px] text-gray-400">
              <Loader2 className="w-3 h-3 animate-spin" />
              {candidate.statusMessage ?? 'Conectando...'}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// Main Component
// ============================================================================

export const ProvisioningStep: React.FC<ProvisioningStepProps> = ({
  candidates,
  winner,
  currentRound,
  maxRounds,
  elapsedTime,
  eta,
  selectedFailover,
}) => {
  return (
    <div className="space-y-5 animate-fadeIn">
      {/* Header */}
      <div className="text-center">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-brand-500/10 border border-brand-500/30 mb-4">
          {winner ? (
            <Check className="w-7 h-7 text-brand-400" />
          ) : (
            <Loader2 className="w-7 h-7 text-brand-400 animate-spin" />
          )}
        </div>
        <h3 className="text-lg font-semibold text-gray-100 mb-1">
          {winner ? 'Máquina Conectada!' : 'Provisionando Máquinas...'}
        </h3>
        <p className="text-xs text-gray-400">
          {winner
            ? 'Sua máquina está pronta para uso'
            : `Testando ${candidates.length} máquinas simultaneamente. A primeira a responder será selecionada.`}
        </p>

        {/* Round indicator and Timer */}
        {!winner && candidates.length > 0 && (
          <div className="flex items-center justify-center gap-3 mt-3 text-xs flex-wrap">
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-purple-500/10 border border-purple-500/30">
              <Rocket className="w-3.5 h-3.5 text-purple-400" />
              <span data-testid="wizard-round-indicator" className="text-purple-400 font-medium">
                Round {currentRound}/{maxRounds}
              </span>
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/5 border border-white/10">
              <Clock className="w-3.5 h-3.5 text-gray-400" />
              <span data-testid="wizard-timer" className="text-gray-300 font-mono">
                {elapsedTime}
              </span>
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-brand-500/10 border border-brand-500/30">
              <Timer className="w-3.5 h-3.5 text-brand-400" />
              <span className="text-brand-400">{eta}</span>
            </div>
          </div>
        )}
      </div>

      {/* Race Track */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2">
        {candidates.map((candidate, index) => (
          <CandidateCard
            key={candidate.id}
            candidate={candidate}
            index={index}
            isWinner={winner?.id === candidate.id}
            isCancelled={winner !== null && winner.id !== candidate.id}
          />
        ))}
      </div>

      {/* Winner Summary */}
      {winner && (
        <div className="p-4 rounded-lg bg-brand-500/5 border border-brand-500/20">
          <h4 className="text-xs font-medium text-brand-400 mb-3">Resumo da Instância</h4>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="flex justify-between">
              <span className="text-gray-500">GPU</span>
              <span className="text-gray-200">{winner.gpu_name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">VRAM</span>
              <span className="text-gray-200">{winner.gpu_ram?.toFixed(0)}GB</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Localização</span>
              <span className="text-gray-200">{winner.geolocation ?? winner.location}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Custo</span>
              <span className="text-brand-400 font-medium">${winner.dph_total?.toFixed(2)}/h</span>
            </div>
            {selectedFailover && (
              <>
                <div className="flex justify-between">
                  <span className="text-gray-500">Failover</span>
                  <span className="text-gray-200">{selectedFailover.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Custo extra</span>
                  <span className="text-gray-200">{selectedFailover.costHour ?? '-'}</span>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ProvisioningStep;
