"""
Serviço para gerenciar transações de crédito e ledger.

Responsável por:
- Adicionar e gerenciar créditos de usuários
- Manter o ledger imutável de transações
- Calcular saldos
- Processar welcome credits e referrer rewards
- Lidar com retrações de crédito (fraude/reembolso)
- Enforçar verificação de email antes de ativar créditos
"""
import logging
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.models.referral import (
    CreditTransaction, Referral, ReferralCode,
    TransactionType, ReferralStatus
)


logger = logging.getLogger(__name__)


# Configurações de créditos (não hardcoded, pode ser movido para config)
REFERRER_REWARD_AMOUNT = 25.0  # $25 para quem indicou
REFERRED_WELCOME_CREDIT = 10.0  # $10 para novo usuário
SPEND_THRESHOLD = 50.0  # Threshold de gasto para liberar reward


class EmailNotVerifiedError(Exception):
    """
    Exceção lançada quando uma operação requer email verificado.

    Esta exceção é usada para bloquear operações de crédito
    para usuários que ainda não verificaram seu email.
    """
    pass


class CreditService:
    """Serviço para gerenciar transações de crédito e ledger."""

    def __init__(self, db: Session):
        self.db = db

    def get_referral_by_referred(self, user_id: str) -> Optional[Referral]:
        """
        Busca a referência pelo ID do usuário indicado.

        Args:
            user_id: ID do usuário

        Returns:
            Referral ou None se não for um usuário indicado
        """
        return self.db.query(Referral).filter(
            Referral.referred_id == user_id
        ).first()

    def is_email_verified(self, user_id: str) -> Tuple[bool, Optional[str]]:
        """
        Verifica se o email de um usuário está verificado.

        Para usuários indicados, verifica o campo email_verified na referência.
        Para usuários não-indicados, considera o email como verificado.

        Args:
            user_id: ID do usuário

        Returns:
            Tuple[bool, Optional[str]]: (is_verified, error_message)
            - is_verified: True se email está verificado
            - error_message: Mensagem de erro se não verificado, None caso contrário
        """
        referral = self.get_referral_by_referred(user_id)

        # Se não é usuário indicado, considera verificado
        if not referral:
            return True, None

        # Se é usuário indicado, verifica o campo email_verified
        if not referral.email_verified:
            return False, "Email verification required before using credits"

        return True, None

    def require_email_verification(self, user_id: str) -> None:
        """
        Verifica se o email do usuário está verificado e levanta exceção se não.

        Args:
            user_id: ID do usuário

        Raises:
            EmailNotVerifiedError: Se email não está verificado
        """
        is_verified, error_message = self.is_email_verified(user_id)
        if not is_verified:
            raise EmailNotVerifiedError(error_message)

    def get_balance(self, user_id: str) -> float:
        """
        Retorna o saldo de créditos de um usuário.

        Calcula o saldo a partir da última transação registrada.
        Se não houver transações, retorna 0.

        Args:
            user_id: ID do usuário

        Returns:
            float: Saldo atual de créditos
        """
        # Buscar última transação para obter saldo atual
        last_transaction = self.db.query(CreditTransaction).filter(
            CreditTransaction.user_id == user_id
        ).order_by(CreditTransaction.created_at.desc()).first()

        if not last_transaction:
            return 0.0

        return last_transaction.balance_after

    def get_transaction_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        transaction_type: Optional[str] = None
    ) -> List[CreditTransaction]:
        """
        Retorna histórico de transações de crédito de um usuário.

        Args:
            user_id: ID do usuário
            limit: Número máximo de transações a retornar
            offset: Offset para paginação
            transaction_type: Filtrar por tipo de transação (opcional)

        Returns:
            Lista de CreditTransaction
        """
        query = self.db.query(CreditTransaction).filter(
            CreditTransaction.user_id == user_id
        )

        if transaction_type:
            query = query.filter(CreditTransaction.transaction_type == transaction_type)

        return query.order_by(
            CreditTransaction.created_at.desc()
        ).offset(offset).limit(limit).all()

    def get_transaction_count(
        self,
        user_id: str,
        transaction_type: Optional[str] = None
    ) -> int:
        """
        Retorna contagem de transações de um usuário.

        Args:
            user_id: ID do usuário
            transaction_type: Filtrar por tipo de transação (opcional)

        Returns:
            int: Número de transações
        """
        query = self.db.query(func.count(CreditTransaction.id)).filter(
            CreditTransaction.user_id == user_id
        )

        if transaction_type:
            query = query.filter(CreditTransaction.transaction_type == transaction_type)

        return query.scalar() or 0

    def add_credit(
        self,
        user_id: str,
        amount: float,
        transaction_type: str,
        description: Optional[str] = None,
        referral_id: Optional[int] = None,
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None,
        created_by: str = "system",
        ip_address: Optional[str] = None
    ) -> CreditTransaction:
        """
        Adiciona crédito ao saldo de um usuário.

        Esta é uma operação append-only no ledger.
        O saldo é calculado automaticamente baseado no saldo anterior.

        Args:
            user_id: ID do usuário
            amount: Valor do crédito (deve ser positivo para adicionar)
            transaction_type: Tipo da transação (TransactionType)
            description: Descrição da transação
            referral_id: ID da referência associada (opcional)
            reference_id: ID de referência externa (opcional)
            reference_type: Tipo de referência externa (opcional)
            created_by: Quem criou a transação (user_id ou "system")
            ip_address: IP do usuário (opcional)

        Returns:
            CreditTransaction: Transação criada

        Raises:
            ValueError: Se o amount for 0
        """
        if amount == 0:
            raise ValueError("Transaction amount cannot be zero")

        # Obter saldo atual
        current_balance = self.get_balance(user_id)

        # Calcular novo saldo
        new_balance = round(current_balance + amount, 2)

        # Criar transação
        transaction = CreditTransaction(
            user_id=user_id,
            transaction_type=transaction_type,
            amount=round(amount, 2),
            balance_before=round(current_balance, 2),
            balance_after=new_balance,
            referral_id=referral_id,
            reference_id=reference_id,
            reference_type=reference_type,
            description=description,
            created_by=created_by,
            ip_address=ip_address,
            created_at=datetime.utcnow()
        )

        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)

        return transaction

    def grant_welcome_credit(
        self,
        referral: Referral,
        ip_address: Optional[str] = None
    ) -> Optional[CreditTransaction]:
        """
        Concede crédito de boas-vindas ($10) para um novo usuário indicado.

        O crédito só é concedido se:
        - O usuário tem uma referência válida
        - O email foi verificado
        - O welcome credit ainda não foi concedido

        Args:
            referral: Objeto Referral do usuário indicado
            ip_address: IP do usuário (opcional)

        Returns:
            CreditTransaction ou None se não concedido
        """
        # Verificar se já foi concedido
        if referral.welcome_credit_granted:
            return None

        # Verificar se email foi verificado
        if not referral.email_verified:
            return None

        # Verificar se não é fraude
        if referral.is_suspicious or referral.status == ReferralStatus.FRAUD.value:
            return None

        # Conceder crédito
        transaction = self.add_credit(
            user_id=referral.referred_id,
            amount=referral.referred_welcome_credit,
            transaction_type=TransactionType.WELCOME_CREDIT.value,
            description=f"Welcome credit for signing up with referral code",
            referral_id=referral.id,
            created_by="system",
            ip_address=ip_address
        )

        # Marcar como concedido
        referral.welcome_credit_granted = True
        referral.welcome_credit_granted_at = datetime.utcnow()

        # Atualizar status da referência
        if referral.status == ReferralStatus.PENDING.value:
            referral.status = ReferralStatus.ACTIVE.value

        self.db.commit()

        return transaction

    def grant_referrer_reward(
        self,
        referral: Referral,
        ip_address: Optional[str] = None
    ) -> Optional[CreditTransaction]:
        """
        Concede reward ($25) para quem indicou quando threshold é atingido.

        O reward só é concedido se:
        - O threshold de gasto foi atingido ($50)
        - O reward ainda não foi concedido
        - A referência não é fraudulenta

        Args:
            referral: Objeto Referral
            ip_address: IP (opcional)

        Returns:
            CreditTransaction ou None se não concedido
        """
        # Verificar se já foi concedido
        if referral.reward_granted:
            return None

        # Verificar threshold
        if referral.referred_total_spend < referral.spend_threshold:
            return None

        # Verificar fraude
        if referral.is_suspicious or referral.status == ReferralStatus.FRAUD.value:
            return None

        # Conceder reward ao referrer
        transaction = self.add_credit(
            user_id=referral.referrer_id,
            amount=referral.referrer_reward_amount,
            transaction_type=TransactionType.REFERRAL_BONUS.value,
            description=f"Referral reward for user reaching ${referral.spend_threshold} spend threshold",
            referral_id=referral.id,
            created_by="system",
            ip_address=ip_address
        )

        # Marcar como concedido
        referral.reward_granted = True
        referral.reward_granted_at = datetime.utcnow()
        referral.threshold_reached_at = datetime.utcnow()
        referral.status = ReferralStatus.COMPLETED.value

        # Atualizar estatísticas do código de referência
        referral_code = self.db.query(ReferralCode).filter(
            ReferralCode.id == referral.referral_code_id
        ).first()

        if referral_code:
            referral_code.total_conversions += 1
            referral_code.total_earnings += referral.referrer_reward_amount

        self.db.commit()

        return transaction

    def retract_credit(
        self,
        user_id: str,
        original_transaction_id: int,
        reason: str,
        retracted_by: str = "system"
    ) -> Optional[CreditTransaction]:
        """
        Retrai um crédito previamente concedido (para casos de fraude/reembolso).

        Cria uma transação negativa para compensar o crédito original.
        O ledger permanece imutável (não deleta a transação original).

        Args:
            user_id: ID do usuário
            original_transaction_id: ID da transação original a ser retraída
            reason: Motivo da retração
            retracted_by: Quem está retraindo (user_id ou "system")

        Returns:
            CreditTransaction ou None se a transação original não existir
        """
        # Buscar transação original
        original = self.db.query(CreditTransaction).filter(
            CreditTransaction.id == original_transaction_id,
            CreditTransaction.user_id == user_id
        ).first()

        if not original:
            return None

        # Verificar se já foi retraída
        existing_retraction = self.db.query(CreditTransaction).filter(
            CreditTransaction.reference_id == str(original_transaction_id),
            CreditTransaction.reference_type == "credit_retraction",
            CreditTransaction.user_id == user_id
        ).first()

        if existing_retraction:
            return None  # Já foi retraída

        # Criar transação de retração (valor negativo do original)
        retraction_amount = -abs(original.amount)

        transaction = self.add_credit(
            user_id=user_id,
            amount=retraction_amount,
            transaction_type=TransactionType.CREDIT_RETRACTION.value,
            description=f"Credit retraction: {reason}",
            referral_id=original.referral_id,
            reference_id=str(original_transaction_id),
            reference_type="credit_retraction",
            created_by=retracted_by
        )

        return transaction

    def manual_adjustment(
        self,
        user_id: str,
        amount: float,
        reason: str,
        adjusted_by: str
    ) -> CreditTransaction:
        """
        Faz um ajuste manual de crédito (por admin).

        Args:
            user_id: ID do usuário
            amount: Valor do ajuste (positivo para adicionar, negativo para remover)
            reason: Motivo do ajuste
            adjusted_by: ID do admin que está fazendo o ajuste

        Returns:
            CreditTransaction: Transação criada
        """
        return self.add_credit(
            user_id=user_id,
            amount=amount,
            transaction_type=TransactionType.MANUAL_ADJUSTMENT.value,
            description=f"Manual adjustment: {reason}",
            created_by=adjusted_by
        )

    def update_referred_spend(
        self,
        referred_user_id: str,
        spend_amount: float
    ) -> Optional[CreditTransaction]:
        """
        Atualiza o total de gastos de um usuário indicado e verifica threshold.

        Se o usuário atingir o threshold de $50, o reward é automaticamente
        concedido ao referrer.

        Args:
            referred_user_id: ID do usuário indicado
            spend_amount: Valor do gasto a adicionar

        Returns:
            CreditTransaction ou None (retorna a transação de reward se concedida)
        """
        # Buscar referência do usuário
        referral = self.db.query(Referral).filter(
            Referral.referred_id == referred_user_id,
            Referral.status.in_([
                ReferralStatus.PENDING.value,
                ReferralStatus.ACTIVE.value
            ])
        ).first()

        if not referral:
            return None

        # Atualizar total de gastos
        referral.referred_total_spend = round(
            referral.referred_total_spend + spend_amount, 2
        )
        self.db.commit()

        # Verificar se atingiu threshold
        if referral.referred_total_spend >= referral.spend_threshold:
            return self.grant_referrer_reward(referral)

        return None

    def get_user_credit_summary(self, user_id: str) -> Dict:
        """
        Retorna um resumo de créditos para um usuário.

        Args:
            user_id: ID do usuário

        Returns:
            Dict com resumo de créditos
        """
        balance = self.get_balance(user_id)

        # Total de créditos recebidos
        total_credits = self.db.query(func.sum(CreditTransaction.amount)).filter(
            CreditTransaction.user_id == user_id,
            CreditTransaction.amount > 0
        ).scalar() or 0.0

        # Total de débitos
        total_debits = self.db.query(func.sum(CreditTransaction.amount)).filter(
            CreditTransaction.user_id == user_id,
            CreditTransaction.amount < 0
        ).scalar() or 0.0

        # Contagem por tipo
        type_counts = self.db.query(
            CreditTransaction.transaction_type,
            func.count(CreditTransaction.id).label("count"),
            func.sum(CreditTransaction.amount).label("total")
        ).filter(
            CreditTransaction.user_id == user_id
        ).group_by(CreditTransaction.transaction_type).all()

        breakdown = {
            t.transaction_type: {
                "count": t.count,
                "total": round(t.total or 0, 2)
            }
            for t in type_counts
        }

        return {
            "balance": round(balance, 2),
            "total_credits": round(total_credits, 2),
            "total_debits": round(abs(total_debits), 2),
            "transaction_count": self.get_transaction_count(user_id),
            "breakdown": breakdown
        }

    def get_pending_referrer_rewards(self, user_id: str) -> Dict:
        """
        Retorna informações sobre rewards pendentes para um referrer.

        Args:
            user_id: ID do referrer

        Returns:
            Dict com informações de rewards pendentes
        """
        # Buscar referências ativas (que ainda não atingiram threshold)
        pending_referrals = self.db.query(Referral).filter(
            Referral.referrer_id == user_id,
            Referral.reward_granted == False,
            Referral.status.in_([
                ReferralStatus.PENDING.value,
                ReferralStatus.ACTIVE.value
            ])
        ).all()

        pending_count = len(pending_referrals)
        potential_earnings = sum(r.referrer_reward_amount for r in pending_referrals)

        # Calcular progresso médio
        if pending_count > 0:
            avg_progress = sum(r.spend_progress for r in pending_referrals) / pending_count
        else:
            avg_progress = 0.0

        return {
            "pending_count": pending_count,
            "potential_earnings": round(potential_earnings, 2),
            "average_progress": round(avg_progress, 4),
            "referrals": [
                {
                    "id": r.id,
                    "referred_id": r.referred_id,
                    "spend_progress": r.spend_progress,
                    "current_spend": r.referred_total_spend,
                    "threshold": r.spend_threshold,
                    "reward_amount": r.referrer_reward_amount
                }
                for r in pending_referrals
            ]
        }

    def has_sufficient_balance(self, user_id: str, amount: float) -> bool:
        """
        Verifica se o usuário tem saldo suficiente para uma operação.

        Args:
            user_id: ID do usuário
            amount: Valor necessário

        Returns:
            bool: True se tiver saldo suficiente
        """
        return self.get_balance(user_id) >= amount

    def use_credits(
        self,
        user_id: str,
        amount: float,
        description: str,
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None,
        skip_verification: bool = False
    ) -> Optional[CreditTransaction]:
        """
        Usa créditos do saldo do usuário (para pagamentos).

        Requer que o email do usuário esteja verificado (para usuários indicados).

        Args:
            user_id: ID do usuário
            amount: Valor a usar (deve ser positivo)
            description: Descrição do uso
            reference_id: ID de referência externa (ex: billing_id)
            reference_type: Tipo de referência (ex: "billing")
            skip_verification: Pular verificação de email (apenas para uso interno)

        Returns:
            CreditTransaction ou None se saldo insuficiente

        Raises:
            ValueError: Se amount for negativo ou zero
            EmailNotVerifiedError: Se email não está verificado
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")

        # Verificar se email está verificado antes de permitir uso de créditos
        if not skip_verification:
            self.require_email_verification(user_id)

        if not self.has_sufficient_balance(user_id, amount):
            return None

        # Criar transação negativa para usar créditos
        return self.add_credit(
            user_id=user_id,
            amount=-amount,  # Negativo para débito
            transaction_type=TransactionType.AFFILIATE_PAYOUT.value,  # Pode ser outro tipo
            description=description,
            reference_id=reference_id,
            reference_type=reference_type,
            created_by="system"
        )
