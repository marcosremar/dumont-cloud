"""
Serviço para gerenciar referências e códigos de referência.

Responsável por:
- Geração de códigos de referência únicos
- Validação de códigos
- Criação e busca de códigos de referência
- Aplicação de códigos durante cadastro
- Rastreamento de referências
- Integração com detecção de fraude
"""
import logging
import secrets
import string
from datetime import datetime
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.models.referral import (
    ReferralCode, Referral, CreditTransaction, AffiliateTracking,
    TransactionType, ReferralStatus
)
from src.services.fraud_detection_service import FraudDetectionService


logger = logging.getLogger(__name__)


# Configurações de créditos (não hardcoded, pode ser movido para config)
REFERRER_REWARD_AMOUNT = 25.0  # $25 para quem indicou
REFERRED_WELCOME_CREDIT = 10.0  # $10 para novo usuário
SPEND_THRESHOLD = 50.0  # Threshold de gasto para liberar reward

# Configuração do código de referência
CODE_LENGTH = 8  # Comprimento do código (entre 8 e 12)
CODE_ALPHABET = string.ascii_uppercase + string.digits  # A-Z, 0-9


class ReferralService:
    """Serviço para gerenciar referências e códigos de referência."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def generate_code(length: int = CODE_LENGTH) -> str:
        """
        Gera um código de referência único e seguro.

        Usa secrets.choice para geração criptograficamente segura.
        Códigos são alfanuméricos (A-Z, 0-9), 8-12 caracteres.

        Args:
            length: Comprimento do código (default: 8, min: 8, max: 12)

        Returns:
            str: Código de referência gerado
        """
        # Garantir comprimento entre 8 e 12
        length = max(8, min(12, length))

        # Gerar código usando secrets para segurança criptográfica
        code = ''.join(secrets.choice(CODE_ALPHABET) for _ in range(length))

        return code

    def _is_code_unique(self, code: str) -> bool:
        """Verifica se o código é único no banco de dados."""
        existing = self.db.query(ReferralCode).filter(
            ReferralCode.code == code
        ).first()
        return existing is None

    def _generate_unique_code(self, max_attempts: int = 10) -> str:
        """
        Gera um código único, verificando colisões no banco.

        Args:
            max_attempts: Número máximo de tentativas antes de falhar

        Returns:
            str: Código único

        Raises:
            RuntimeError: Se não conseguir gerar código único após tentativas
        """
        for _ in range(max_attempts):
            code = self.generate_code()
            if self._is_code_unique(code):
                return code

        # Se todas as tentativas falharem, usar código maior
        for _ in range(max_attempts):
            code = self.generate_code(length=12)
            if self._is_code_unique(code):
                return code

        raise RuntimeError("Unable to generate unique referral code after maximum attempts")

    def get_or_create_code(self, user_id: str) -> ReferralCode:
        """
        Obtém ou cria código de referência para um usuário.

        Cada usuário tem apenas um código de referência.

        Args:
            user_id: ID do usuário

        Returns:
            ReferralCode: Objeto do código de referência
        """
        # Buscar código existente
        existing = self.db.query(ReferralCode).filter(
            ReferralCode.user_id == user_id
        ).first()

        if existing:
            return existing

        # Gerar novo código único
        code = self._generate_unique_code()

        referral_code = ReferralCode(
            user_id=user_id,
            code=code,
            is_active=True,
            created_at=datetime.utcnow()
        )

        self.db.add(referral_code)
        self.db.commit()
        self.db.refresh(referral_code)

        return referral_code

    def get_code_by_user(self, user_id: str) -> Optional[ReferralCode]:
        """
        Busca código de referência por user_id.

        Args:
            user_id: ID do usuário

        Returns:
            ReferralCode ou None se não existir
        """
        return self.db.query(ReferralCode).filter(
            ReferralCode.user_id == user_id
        ).first()

    def get_code_by_code(self, code: str) -> Optional[ReferralCode]:
        """
        Busca código de referência pelo código.

        Args:
            code: Código de referência

        Returns:
            ReferralCode ou None se não existir
        """
        return self.db.query(ReferralCode).filter(
            ReferralCode.code == code.upper()  # Códigos são case-insensitive
        ).first()

    def validate_code(self, code: str, user_id: str) -> Dict:
        """
        Valida um código de referência.

        Verifica:
        - Se o código existe
        - Se está ativo e não expirado
        - Se não é o próprio código do usuário (self-referral)

        Args:
            code: Código de referência a validar
            user_id: ID do usuário que quer usar o código

        Returns:
            Dict com resultado da validação:
            {
                "valid": bool,
                "error": str ou None,
                "referral_code": ReferralCode ou None
            }
        """
        if not code:
            return {"valid": False, "error": "Referral code is required", "referral_code": None}

        # Buscar código
        referral_code = self.get_code_by_code(code.upper())

        if not referral_code:
            return {"valid": False, "error": "Invalid referral code", "referral_code": None}

        # Verificar se está ativo e não expirado
        if not referral_code.is_usable:
            if not referral_code.is_active:
                return {"valid": False, "error": "Referral code is inactive", "referral_code": None}
            if referral_code.is_expired:
                return {"valid": False, "error": "Referral code has expired", "referral_code": None}

        # Verificar self-referral
        if referral_code.user_id == user_id:
            return {"valid": False, "error": "Cannot use your own referral code", "referral_code": None}

        # Verificar se usuário já foi indicado
        existing_referral = self.db.query(Referral).filter(
            Referral.referred_id == user_id
        ).first()

        if existing_referral:
            return {"valid": False, "error": "User already has a referrer", "referral_code": None}

        return {"valid": True, "error": None, "referral_code": referral_code}

    def apply_code(
        self,
        referred_user_id: str,
        code: str,
        referred_ip: Optional[str] = None,
        skip_fraud_check: bool = False
    ) -> Dict:
        """
        Aplica um código de referência para um novo usuário.

        Cria o relacionamento de referência e registra $10 de welcome credit.
        O crédito só será ativado após verificação de email.
        Inclui verificações anti-fraude (rate limiting, IP tracking, etc.)

        Args:
            referred_user_id: ID do usuário que está se cadastrando
            code: Código de referência
            referred_ip: IP do usuário (para anti-fraude)
            skip_fraud_check: Pular verificações de fraude (uso interno apenas)

        Returns:
            Dict com resultado:
            {
                "success": bool,
                "error": str ou None,
                "referral": Referral ou None,
                "welcome_credit": float ou None,
                "is_suspicious": bool,
                "fraud_warnings": List[Dict] ou None
            }
        """
        # Validar código
        validation = self.validate_code(code, referred_user_id)
        if not validation["valid"]:
            return {
                "success": False,
                "error": validation["error"],
                "referral": None,
                "welcome_credit": None,
                "is_suspicious": False,
                "fraud_warnings": None
            }

        referral_code = validation["referral_code"]

        # Verificação anti-fraude
        fraud_warnings = []
        is_suspicious = False

        if not skip_fraud_check:
            fraud_service = FraudDetectionService(self.db)
            should_block, fraud_results = fraud_service.perform_full_fraud_check(
                referrer_user_id=referral_code.user_id,
                referred_user_id=referred_user_id,
                referred_ip=referred_ip,
                referral_code_id=referral_code.id
            )

            if should_block:
                # Bloquear referência por fraude
                blocking_reasons = [
                    r.reason for r in fraud_results if r.should_block
                ]
                logger.warning(
                    f"Referral bloqueado por fraude: referred={referred_user_id}, "
                    f"reasons={blocking_reasons}"
                )
                return {
                    "success": False,
                    "error": blocking_reasons[0] if blocking_reasons else "Suspicious activity detected",
                    "referral": None,
                    "welcome_credit": None,
                    "is_suspicious": True,
                    "fraud_warnings": [r.to_dict() for r in fraud_results]
                }

            # Verificar se há warnings não-bloqueantes
            if fraud_results:
                is_suspicious = True
                fraud_warnings = [r.to_dict() for r in fraud_results]

        # Criar referência
        referral = Referral(
            referrer_id=referral_code.user_id,
            referred_id=referred_user_id,
            referral_code_id=referral_code.id,
            status=ReferralStatus.PENDING.value,
            email_verified=False,
            referred_total_spend=0.0,
            spend_threshold=SPEND_THRESHOLD,
            referrer_reward_amount=REFERRER_REWARD_AMOUNT,
            referred_welcome_credit=REFERRED_WELCOME_CREDIT,
            reward_granted=False,
            welcome_credit_granted=False,
            referred_ip=referred_ip,
            is_suspicious=is_suspicious,
            fraud_reason="; ".join([w["reason"] for w in fraud_warnings]) if fraud_warnings else None,
            created_at=datetime.utcnow()
        )

        self.db.add(referral)

        # Atualizar estatísticas do código
        referral_code.total_signups += 1
        referral_code.last_used_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(referral)

        # Log de sucesso
        logger.info(
            f"Referral aplicado: referred={referred_user_id}, "
            f"referrer={referral_code.user_id}, code={code}, "
            f"is_suspicious={is_suspicious}"
        )

        return {
            "success": True,
            "error": None,
            "referral": referral,
            "welcome_credit": REFERRED_WELCOME_CREDIT,  # Crédito pendente de verificação
            "is_suspicious": is_suspicious,
            "fraud_warnings": fraud_warnings if fraud_warnings else None
        }

    def get_referral_by_referred(self, referred_user_id: str) -> Optional[Referral]:
        """
        Busca referência pelo ID do usuário indicado.

        Args:
            referred_user_id: ID do usuário indicado

        Returns:
            Referral ou None
        """
        return self.db.query(Referral).filter(
            Referral.referred_id == referred_user_id
        ).first()

    def get_referrals_by_referrer(
        self,
        referrer_user_id: str,
        status: Optional[str] = None
    ) -> List[Referral]:
        """
        Lista referências feitas por um usuário.

        Args:
            referrer_user_id: ID do usuário que indicou
            status: Filtrar por status (opcional)

        Returns:
            Lista de Referral
        """
        query = self.db.query(Referral).filter(
            Referral.referrer_id == referrer_user_id
        )

        if status:
            query = query.filter(Referral.status == status)

        return query.order_by(Referral.created_at.desc()).all()

    def get_referrer_stats(self, user_id: str) -> Dict:
        """
        Retorna estatísticas de referência para um usuário (como referrer).

        Args:
            user_id: ID do usuário

        Returns:
            Dict com estatísticas
        """
        referral_code = self.get_code_by_user(user_id)
        if not referral_code:
            return {
                "has_code": False,
                "code": None,
                "total_referrals": 0,
                "pending_referrals": 0,
                "completed_referrals": 0,
                "total_earnings": 0.0,
                "pending_earnings": 0.0
            }

        # Contagem de referências por status
        referrals_query = self.db.query(
            Referral.status,
            func.count(Referral.id).label("count")
        ).filter(
            Referral.referrer_id == user_id
        ).group_by(Referral.status).all()

        status_counts = {r.status: r.count for r in referrals_query}

        total = sum(status_counts.values())
        pending = status_counts.get(ReferralStatus.PENDING.value, 0) + \
                  status_counts.get(ReferralStatus.ACTIVE.value, 0)
        completed = status_counts.get(ReferralStatus.COMPLETED.value, 0)

        # Total de ganhos (já creditados)
        total_earnings = self.db.query(func.sum(CreditTransaction.amount)).filter(
            CreditTransaction.user_id == user_id,
            CreditTransaction.transaction_type == TransactionType.REFERRAL_BONUS.value,
            CreditTransaction.amount > 0
        ).scalar() or 0.0

        # Ganhos pendentes (referências ativas que ainda não atingiram threshold)
        pending_earnings = pending * REFERRER_REWARD_AMOUNT

        return {
            "has_code": True,
            "code": referral_code.code,
            "total_referrals": total,
            "pending_referrals": pending,
            "completed_referrals": completed,
            "total_earnings": round(total_earnings, 2),
            "pending_earnings": round(pending_earnings, 2),
            "conversion_rate": referral_code.conversion_rate
        }

    def record_click(self, code: str) -> bool:
        """
        Registra um clique em um código de referência.

        Args:
            code: Código de referência

        Returns:
            bool: True se registrado com sucesso
        """
        referral_code = self.get_code_by_code(code)
        if not referral_code or not referral_code.is_usable:
            return False

        referral_code.total_clicks += 1
        referral_code.last_used_at = datetime.utcnow()
        self.db.commit()

        return True
