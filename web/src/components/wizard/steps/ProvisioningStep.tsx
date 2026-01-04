/**
 * ProvisioningStep Component
 * Step 4: Provisioning race visualization
 */

import React from 'react';
import {
  Loader2,
  Check,
  X,
  Cpu,
  Clock,
  Timer,
  Rocket,
  AlertCircle,
} from 'lucide-react';
import { formatTime, getETA } from '../utils/timeFormatters';
import { getFailoverOption } from '../constants/failoverOptions';
import type {
  ProvisioningCandidate,
  ProvisioningWinner,
  FailoverStrategy,
} from '../types/wizard.types';

interface ProvisioningStepProps {
  candidates: ProvisioningCandidate[];
  winner: ProvisioningWinner | null;
  currentRound: number;
  maxRounds: number;
  elapsedTime: number;
  raceError: string | null;
  isFailed: boolean;
  failoverStrategy: FailoverStrategy;
}

export function ProvisioningStep({
  candidates,
  winner,
  currentRound,
  maxRounds,
  elapsedTime,
  raceError,
  isFailed,
  failoverStrategy,
}: ProvisioningStepProps) {
  const selectedFailover = getFailoverOption(failoverStrategy);
  const eta = getETA(elapsedTime, candidates, !!winner);

  return (
    <div className="space-y-5 animate-fadeIn">
      {/* Header */}
      <div className="text-center">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-brand-500/10 border border-brand-500/30 mb-4">
          {winner ? (
            <Check className="w-7 h-7 text-brand-400" />
          ) : isFailed ? (
            <AlertCircle className="w-7 h-7 text-red-400" />
          ) : (
            <Loader2 className="w-7 h-7 text-brand-400 animate-spin" />
          )}
        </div>
        <h3 className="text-lg font-semibold text-gray-100 mb-1">
          {winner
            ? 'Máquina Conectada!'
            : isFailed
            ? 'Falha no Provisionamento'
            : 'Provisionando Máquinas...'}
        </h3>
        <p className="text-xs text-gray-400">
          {winner
            ? 'Sua máquina está pronta para uso'
            : isFailed
            ? raceError || 'Não foi possível conectar às máquinas'
            : `Testando ${candidates.length} máquinas simultaneamente. A primeira a responder será selecionada.`}
        </p>

        {/* Round indicator and Timer */}
        {!winner && !isFailed && candidates.length > 0 && (
          <div className="flex items-center justify-center gap-3 mt-3 text-xs flex-wrap">
            {/* Round indicator */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-purple-500/10 border border-purple-500/30">
              <Rocket className="w-3.5 h-3.5 text-purple-400" />
              <span
                data-testid="wizard-round-indicator"
                className="text-purple-400 font-medium"
              >
                Round {currentRound}/{maxRounds}
              </span>
            </div>
            {/* Timer */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/5 border border-white/10">
              <Clock className="w-3.5 h-3.5 text-gray-400" />
              <span
                data-testid="wizard-timer"
                className="text-gray-300 font-mono"
              >
                {formatTime(elapsedTime)}
              </span>
            </div>
            {/* ETA */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-brand-500/10 border border-brand-500/30">
              <Timer className="w-3.5 h-3.5 text-brand-400" />
              <span className="text-brand-400">{eta}</span>
            </div>
          </div>
        )}
      </div>

      {/* Race Track - Grid layout for compact display */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2">
        {candidates.map((candidate, index) => {
          const isWinner = winner?.id === candidate.id;
          const isCancelled = winner && !isWinner;
          const status = candidate.status;

          return (
            <div
              key={candidate.id}
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
              {/* Progress bar for connecting state */}
              {status === 'connecting' && !winner && (
                <div
                  className="absolute bottom-0 left-0 h-0.5 bg-brand-500 transition-all duration-300 ease-out"
                  style={{ width: `${candidate.progress || 0}%` }}
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
                    <Cpu
                      className={`w-3.5 h-3.5 ${
                        isWinner ? 'text-brand-400' : 'text-gray-500'
                      }`}
                    />
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
                    <span>
                      {candidate.geolocation || candidate.location || 'Unknown'}
                    </span>
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
                        <span className="text-[9px] text-red-400/70">
                          {candidate.errorMessage}
                        </span>
                      )}
                    </div>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 text-[10px] text-gray-400">
                      <Loader2 className="w-3 h-3 animate-spin" />
                      Conectando...
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Winner Details */}
      {winner && (
        <div className="p-4 rounded-lg bg-brand-500/5 border border-brand-500/20">
          <h4 className="text-sm font-medium text-gray-200 mb-3">
            Detalhes da Máquina
          </h4>
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
              <span className="text-gray-200">
                {winner.geolocation || winner.location}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Custo</span>
              <span className="text-brand-400 font-medium">
                ${winner.dph_total?.toFixed(2)}/h
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Failover</span>
              <span className="text-gray-200">
                {selectedFailover?.name || '-'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Custo extra</span>
              <span className="text-gray-200">
                {selectedFailover?.costHour || '-'}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ProvisioningStep;
