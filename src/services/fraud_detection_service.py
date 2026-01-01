"""
Serviço de detecção de fraude para o sistema de referências.

Responsável por:
- Bloqueio de self-referral
- Rate limiting (max 10 referrals por usuário por dia)
- Rastreamento de IP (detecta padrões suspeitos)
- Detecção de padrões de abuso (signups rápidos, mesmo IP, etc.)
- Logging de eventos de fraude
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass, field
import threading

from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from src.models.referral import Referral, ReferralCode, ReferralStatus


logger = logging.getLogger(__name__)


# Configurações de anti-fraude
MAX_REFERRALS_PER_USER_PER_DAY = 10  # Limite de indicações por dia
MAX_SIGNUPS_PER_IP_PER_HOUR = 5  # Limite de cadastros por IP por hora
MAX_SIGNUPS_PER_IP_PER_DAY = 10  # Limite de cadastros por IP por dia
RAPID_SIGNUP_THRESHOLD_SECONDS = 60  # Signups em menos de 60s são suspeitos
SUSPICIOUS_IP_SIMILARITY_THRESHOLD = 3  # Número de IPs similares para marcar como suspeito


@dataclass
class FraudCheckResult:
    """Resultado de uma verificação de fraude."""
    is_fraud: bool
    fraud_type: Optional[str] = None
    reason: Optional[str] = None
    severity: str = "low"  # low, medium, high
    should_block: bool = False
    details: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "is_fraud": self.is_fraud,
            "fraud_type": self.fraud_type,
            "reason": self.reason,
            "severity": self.severity,
            "should_block": self.should_block,
            "details": self.details
        }


class InMemoryRateLimiter:
    """
    Rate limiter em memória thread-safe.

    Usado como fallback quando Redis não está disponível.
    """

    def __init__(self):
        self._counts: Dict[str, List[datetime]] = defaultdict(list)
        self._lock = threading.Lock()

    def check_and_increment(
        self,
        key: str,
        max_count: int,
        window_seconds: int
    ) -> Tuple[bool, int]:
        """
        Verifica rate limit e incrementa contador.

        Args:
            key: Chave de identificação (user_id, ip, etc.)
            max_count: Número máximo de operações permitidas
            window_seconds: Janela de tempo em segundos

        Returns:
            Tuple (allowed: bool, current_count: int)
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=window_seconds)

        with self._lock:
            # Limpar entradas expiradas
            self._counts[key] = [
                ts for ts in self._counts[key]
                if ts > cutoff
            ]

            current_count = len(self._counts[key])

            if current_count >= max_count:
                return False, current_count

            # Adicionar nova entrada
            self._counts[key].append(now)
            return True, current_count + 1

    def get_count(self, key: str, window_seconds: int) -> int:
        """Retorna contagem atual sem incrementar."""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=window_seconds)

        with self._lock:
            return len([ts for ts in self._counts[key] if ts > cutoff])

    def reset(self, key: str) -> None:
        """Reseta contador para uma chave."""
        with self._lock:
            self._counts.pop(key, None)

    def cleanup_expired(self) -> int:
        """Remove todas as entradas expiradas de todas as chaves."""
        now = datetime.utcnow()
        # Usar janela de 24h para limpeza geral
        cutoff = now - timedelta(hours=24)
        removed = 0

        with self._lock:
            keys_to_remove = []
            for key, timestamps in self._counts.items():
                original_len = len(timestamps)
                self._counts[key] = [ts for ts in timestamps if ts > cutoff]
                removed += original_len - len(self._counts[key])

                if not self._counts[key]:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self._counts[key]

        return removed


class FraudDetectionService:
    """
    Serviço de detecção de fraude para referências.

    Implementa múltiplas verificações anti-fraude:
    - Self-referral blocking
    - Rate limiting por usuário
    - Rate limiting por IP
    - Detecção de padrões suspeitos
    """

    # Rate limiter singleton compartilhado
    _rate_limiter = InMemoryRateLimiter()

    def __init__(self, db: Session):
        self.db = db

    @classmethod
    def get_rate_limiter(cls) -> InMemoryRateLimiter:
        """Retorna o rate limiter compartilhado."""
        return cls._rate_limiter

    def check_self_referral(
        self,
        referrer_user_id: str,
        referred_user_id: str
    ) -> FraudCheckResult:
        """
        Verifica se é uma tentativa de self-referral.

        Args:
            referrer_user_id: ID do usuário que indicou
            referred_user_id: ID do usuário indicado

        Returns:
            FraudCheckResult com resultado da verificação
        """
        if referrer_user_id == referred_user_id:
            logger.warning(
                f"Self-referral detectado: user_id={referred_user_id}"
            )
            return FraudCheckResult(
                is_fraud=True,
                fraud_type="self_referral",
                reason="User cannot refer themselves",
                severity="high",
                should_block=True,
                details={
                    "user_id": referred_user_id
                }
            )

        return FraudCheckResult(is_fraud=False)

    def check_referral_rate_limit(
        self,
        referrer_user_id: str
    ) -> FraudCheckResult:
        """
        Verifica rate limit de referências por usuário por dia.

        Args:
            referrer_user_id: ID do usuário que está indicando

        Returns:
            FraudCheckResult com resultado da verificação
        """
        key = f"referral_daily:{referrer_user_id}"
        window_seconds = 24 * 60 * 60  # 24 horas

        allowed, count = self._rate_limiter.check_and_increment(
            key,
            MAX_REFERRALS_PER_USER_PER_DAY,
            window_seconds
        )

        if not allowed:
            logger.warning(
                f"Rate limit de referências excedido: user_id={referrer_user_id}, count={count}"
            )
            return FraudCheckResult(
                is_fraud=True,
                fraud_type="rate_limit_exceeded",
                reason=f"Maximum {MAX_REFERRALS_PER_USER_PER_DAY} referrals per day exceeded",
                severity="medium",
                should_block=True,
                details={
                    "user_id": referrer_user_id,
                    "current_count": count,
                    "max_allowed": MAX_REFERRALS_PER_USER_PER_DAY,
                    "window": "24h"
                }
            )

        return FraudCheckResult(
            is_fraud=False,
            details={
                "current_count": count,
                "max_allowed": MAX_REFERRALS_PER_USER_PER_DAY
            }
        )

    def check_ip_rate_limit(
        self,
        ip_address: str
    ) -> FraudCheckResult:
        """
        Verifica rate limit de signups por IP.

        Args:
            ip_address: Endereço IP do usuário

        Returns:
            FraudCheckResult com resultado da verificação
        """
        if not ip_address:
            return FraudCheckResult(is_fraud=False)

        # Verificar limite por hora
        hourly_key = f"ip_hourly:{ip_address}"
        hourly_allowed, hourly_count = self._rate_limiter.check_and_increment(
            hourly_key,
            MAX_SIGNUPS_PER_IP_PER_HOUR,
            60 * 60  # 1 hora
        )

        if not hourly_allowed:
            logger.warning(
                f"Rate limit de IP por hora excedido: ip={ip_address}, count={hourly_count}"
            )
            return FraudCheckResult(
                is_fraud=True,
                fraud_type="ip_rate_limit_hourly",
                reason=f"Maximum {MAX_SIGNUPS_PER_IP_PER_HOUR} signups per hour from same IP",
                severity="high",
                should_block=True,
                details={
                    "ip_address": ip_address,
                    "current_count": hourly_count,
                    "max_allowed": MAX_SIGNUPS_PER_IP_PER_HOUR,
                    "window": "1h"
                }
            )

        # Verificar limite diário
        daily_key = f"ip_daily:{ip_address}"
        daily_allowed, daily_count = self._rate_limiter.check_and_increment(
            daily_key,
            MAX_SIGNUPS_PER_IP_PER_DAY,
            24 * 60 * 60  # 24 horas
        )

        if not daily_allowed:
            logger.warning(
                f"Rate limit de IP diário excedido: ip={ip_address}, count={daily_count}"
            )
            return FraudCheckResult(
                is_fraud=True,
                fraud_type="ip_rate_limit_daily",
                reason=f"Maximum {MAX_SIGNUPS_PER_IP_PER_DAY} signups per day from same IP",
                severity="medium",
                should_block=True,
                details={
                    "ip_address": ip_address,
                    "current_count": daily_count,
                    "max_allowed": MAX_SIGNUPS_PER_IP_PER_DAY,
                    "window": "24h"
                }
            )

        return FraudCheckResult(
            is_fraud=False,
            details={
                "hourly_count": hourly_count,
                "daily_count": daily_count
            }
        )

    def check_same_ip_referral(
        self,
        referrer_user_id: str,
        referred_ip: str
    ) -> FraudCheckResult:
        """
        Verifica se referrer e referred usam o mesmo IP.

        Isso pode indicar que a mesma pessoa está criando múltiplas contas.

        Args:
            referrer_user_id: ID do usuário que indicou
            referred_ip: IP do usuário indicado

        Returns:
            FraudCheckResult com resultado da verificação
        """
        if not referred_ip:
            return FraudCheckResult(is_fraud=False)

        # Buscar IP do referrer nas referências anteriores
        referrer_ips = self.db.query(Referral.referrer_ip).filter(
            Referral.referrer_id == referrer_user_id,
            Referral.referrer_ip.isnot(None)
        ).distinct().all()

        referrer_ip_set = {ip[0] for ip in referrer_ips}

        if referred_ip in referrer_ip_set:
            logger.warning(
                f"Mesmo IP para referrer e referred: ip={referred_ip}, "
                f"referrer_id={referrer_user_id}"
            )
            return FraudCheckResult(
                is_fraud=True,
                fraud_type="same_ip_referral",
                reason="Referrer and referred user share the same IP address",
                severity="high",
                should_block=False,  # Não bloqueia mas marca como suspeito
                details={
                    "ip_address": referred_ip,
                    "referrer_user_id": referrer_user_id
                }
            )

        return FraudCheckResult(is_fraud=False)

    def check_rapid_signups(
        self,
        referral_code_id: int,
        window_seconds: int = RAPID_SIGNUP_THRESHOLD_SECONDS
    ) -> FraudCheckResult:
        """
        Verifica se houve signups muito rápidos para o mesmo código.

        Signups em menos de 60 segundos do anterior são suspeitos.

        Args:
            referral_code_id: ID do código de referência
            window_seconds: Janela de tempo para detectar signups rápidos

        Returns:
            FraudCheckResult com resultado da verificação
        """
        cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)

        recent_signups = self.db.query(func.count(Referral.id)).filter(
            Referral.referral_code_id == referral_code_id,
            Referral.created_at >= cutoff
        ).scalar() or 0

        if recent_signups > 0:
            logger.warning(
                f"Signup rápido detectado: code_id={referral_code_id}, "
                f"recent_count={recent_signups} em {window_seconds}s"
            )
            return FraudCheckResult(
                is_fraud=True,
                fraud_type="rapid_signup",
                reason=f"Multiple signups within {window_seconds} seconds",
                severity="medium",
                should_block=False,  # Não bloqueia mas marca como suspeito
                details={
                    "referral_code_id": referral_code_id,
                    "recent_signups": recent_signups,
                    "window_seconds": window_seconds
                }
            )

        return FraudCheckResult(is_fraud=False)

    def check_ip_pattern(
        self,
        ip_address: str,
        referral_code_id: int
    ) -> FraudCheckResult:
        """
        Verifica padrões suspeitos de IP para um código de referência.

        Detecta quando múltiplas referências vêm do mesmo /24 subnet.

        Args:
            ip_address: Endereço IP do usuário
            referral_code_id: ID do código de referência

        Returns:
            FraudCheckResult com resultado da verificação
        """
        if not ip_address:
            return FraudCheckResult(is_fraud=False)

        # Extrair subnet /24 (primeiros 3 octetos)
        ip_parts = ip_address.split('.')
        if len(ip_parts) != 4:
            # IPv6 ou formato inválido - skip
            return FraudCheckResult(is_fraud=False)

        subnet_prefix = '.'.join(ip_parts[:3])

        # Contar referências do mesmo subnet nas últimas 24h
        cutoff = datetime.utcnow() - timedelta(hours=24)

        same_subnet_count = self.db.query(func.count(Referral.id)).filter(
            Referral.referral_code_id == referral_code_id,
            Referral.referred_ip.like(f"{subnet_prefix}.%"),
            Referral.created_at >= cutoff
        ).scalar() or 0

        if same_subnet_count >= SUSPICIOUS_IP_SIMILARITY_THRESHOLD:
            logger.warning(
                f"Padrão de IP suspeito: subnet={subnet_prefix}.*, "
                f"code_id={referral_code_id}, count={same_subnet_count}"
            )
            return FraudCheckResult(
                is_fraud=True,
                fraud_type="ip_pattern",
                reason=f"Multiple referrals from similar IP addresses ({same_subnet_count} from same /24 subnet)",
                severity="medium",
                should_block=False,
                details={
                    "subnet": f"{subnet_prefix}.0/24",
                    "referral_code_id": referral_code_id,
                    "same_subnet_count": same_subnet_count,
                    "threshold": SUSPICIOUS_IP_SIMILARITY_THRESHOLD
                }
            )

        return FraudCheckResult(is_fraud=False)

    def check_already_referred(
        self,
        user_id: str
    ) -> FraudCheckResult:
        """
        Verifica se usuário já foi indicado anteriormente.

        Um usuário só pode ser indicado uma vez.

        Args:
            user_id: ID do usuário

        Returns:
            FraudCheckResult com resultado da verificação
        """
        existing = self.db.query(Referral).filter(
            Referral.referred_id == user_id
        ).first()

        if existing:
            logger.warning(
                f"Tentativa de re-referral: user_id={user_id}, "
                f"existing_referral_id={existing.id}"
            )
            return FraudCheckResult(
                is_fraud=True,
                fraud_type="already_referred",
                reason="User has already been referred",
                severity="high",
                should_block=True,
                details={
                    "user_id": user_id,
                    "existing_referral_id": existing.id,
                    "existing_referrer_id": existing.referrer_id
                }
            )

        return FraudCheckResult(is_fraud=False)

    def perform_full_fraud_check(
        self,
        referrer_user_id: str,
        referred_user_id: str,
        referred_ip: Optional[str] = None,
        referral_code_id: Optional[int] = None
    ) -> Tuple[bool, List[FraudCheckResult]]:
        """
        Executa verificação completa de fraude.

        Realiza todas as verificações anti-fraude disponíveis e retorna
        o resultado consolidado.

        Args:
            referrer_user_id: ID do usuário que indicou
            referred_user_id: ID do usuário indicado
            referred_ip: IP do usuário indicado (opcional)
            referral_code_id: ID do código de referência (opcional)

        Returns:
            Tuple (should_block: bool, results: List[FraudCheckResult])
        """
        results = []
        should_block = False

        # 1. Self-referral check
        result = self.check_self_referral(referrer_user_id, referred_user_id)
        if result.is_fraud:
            results.append(result)
            if result.should_block:
                should_block = True

        # 2. Already referred check
        result = self.check_already_referred(referred_user_id)
        if result.is_fraud:
            results.append(result)
            if result.should_block:
                should_block = True

        # 3. Referral rate limit
        result = self.check_referral_rate_limit(referrer_user_id)
        if result.is_fraud:
            results.append(result)
            if result.should_block:
                should_block = True

        # 4. IP rate limit
        if referred_ip:
            result = self.check_ip_rate_limit(referred_ip)
            if result.is_fraud:
                results.append(result)
                if result.should_block:
                    should_block = True

        # 5. Same IP check
        if referred_ip:
            result = self.check_same_ip_referral(referrer_user_id, referred_ip)
            if result.is_fraud:
                results.append(result)
                # Não bloqueia, apenas marca como suspeito

        # 6. Rapid signup check
        if referral_code_id:
            result = self.check_rapid_signups(referral_code_id)
            if result.is_fraud:
                results.append(result)

        # 7. IP pattern check
        if referred_ip and referral_code_id:
            result = self.check_ip_pattern(referred_ip, referral_code_id)
            if result.is_fraud:
                results.append(result)

        # Log resultado consolidado
        if results:
            fraud_types = [r.fraud_type for r in results]
            logger.info(
                f"Fraud check concluído: referred={referred_user_id}, "
                f"fraud_count={len(results)}, types={fraud_types}, "
                f"should_block={should_block}"
            )

        return should_block, results

    def mark_referral_suspicious(
        self,
        referral: Referral,
        fraud_results: List[FraudCheckResult]
    ) -> Referral:
        """
        Marca uma referência como suspeita.

        Args:
            referral: Objeto Referral a ser marcado
            fraud_results: Lista de resultados de fraude

        Returns:
            Referral atualizado
        """
        referral.is_suspicious = True

        # Compilar razões de fraude
        fraud_reasons = [
            f"{r.fraud_type}: {r.reason}"
            for r in fraud_results
        ]
        referral.fraud_reason = "; ".join(fraud_reasons)[:500]  # Limitar tamanho

        self.db.commit()
        self.db.refresh(referral)

        logger.info(
            f"Referral marcado como suspeito: id={referral.id}, "
            f"reasons={referral.fraud_reason}"
        )

        return referral

    def block_referral(
        self,
        referral: Referral,
        fraud_results: List[FraudCheckResult]
    ) -> Referral:
        """
        Bloqueia uma referência por fraude.

        Args:
            referral: Objeto Referral a ser bloqueado
            fraud_results: Lista de resultados de fraude

        Returns:
            Referral atualizado
        """
        referral.status = ReferralStatus.FRAUD.value
        referral.is_suspicious = True

        fraud_reasons = [
            f"{r.fraud_type}: {r.reason}"
            for r in fraud_results
        ]
        referral.fraud_reason = "; ".join(fraud_reasons)[:500]

        self.db.commit()
        self.db.refresh(referral)

        logger.warning(
            f"Referral bloqueado por fraude: id={referral.id}, "
            f"status=FRAUD, reasons={referral.fraud_reason}"
        )

        return referral

    def get_suspicious_referrals(
        self,
        limit: int = 100,
        include_blocked: bool = False
    ) -> List[Referral]:
        """
        Lista referências suspeitas para revisão.

        Args:
            limit: Limite de resultados
            include_blocked: Incluir referências já bloqueadas

        Returns:
            Lista de Referral suspeitas
        """
        query = self.db.query(Referral).filter(
            Referral.is_suspicious == True
        )

        if not include_blocked:
            query = query.filter(Referral.status != ReferralStatus.FRAUD.value)

        return query.order_by(Referral.created_at.desc()).limit(limit).all()

    def get_fraud_stats(self) -> Dict:
        """
        Retorna estatísticas de fraude.

        Returns:
            Dict com estatísticas de fraude
        """
        # Total de referências
        total_referrals = self.db.query(func.count(Referral.id)).scalar() or 0

        # Referências suspeitas
        suspicious_count = self.db.query(func.count(Referral.id)).filter(
            Referral.is_suspicious == True
        ).scalar() or 0

        # Referências bloqueadas por fraude
        blocked_count = self.db.query(func.count(Referral.id)).filter(
            Referral.status == ReferralStatus.FRAUD.value
        ).scalar() or 0

        # Taxa de fraude
        fraud_rate = (blocked_count / total_referrals * 100) if total_referrals > 0 else 0
        suspicious_rate = (suspicious_count / total_referrals * 100) if total_referrals > 0 else 0

        return {
            "total_referrals": total_referrals,
            "suspicious_count": suspicious_count,
            "blocked_count": blocked_count,
            "fraud_rate_percent": round(fraud_rate, 2),
            "suspicious_rate_percent": round(suspicious_rate, 2),
            "rate_limiter_keys": len(self._rate_limiter._counts)
        }

    def clear_user_rate_limits(self, user_id: str) -> None:
        """
        Limpa rate limits para um usuário específico (admin).

        Args:
            user_id: ID do usuário
        """
        key = f"referral_daily:{user_id}"
        self._rate_limiter.reset(key)
        logger.info(f"Rate limits resetados para user_id={user_id}")

    def clear_ip_rate_limits(self, ip_address: str) -> None:
        """
        Limpa rate limits para um IP específico (admin).

        Args:
            ip_address: Endereço IP
        """
        hourly_key = f"ip_hourly:{ip_address}"
        daily_key = f"ip_daily:{ip_address}"

        self._rate_limiter.reset(hourly_key)
        self._rate_limiter.reset(daily_key)

        logger.info(f"Rate limits de IP resetados para ip={ip_address}")


# Funções de conveniência para uso sem instância de service
def check_referral_fraud(
    db: Session,
    referrer_user_id: str,
    referred_user_id: str,
    referred_ip: Optional[str] = None,
    referral_code_id: Optional[int] = None
) -> Tuple[bool, List[FraudCheckResult]]:
    """
    Função de conveniência para verificação de fraude.

    Args:
        db: Sessão do banco de dados
        referrer_user_id: ID do usuário que indicou
        referred_user_id: ID do usuário indicado
        referred_ip: IP do usuário indicado (opcional)
        referral_code_id: ID do código de referência (opcional)

    Returns:
        Tuple (should_block: bool, results: List[FraudCheckResult])
    """
    service = FraudDetectionService(db)
    return service.perform_full_fraud_check(
        referrer_user_id,
        referred_user_id,
        referred_ip,
        referral_code_id
    )
