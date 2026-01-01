"""
Referral and Affiliate Program Models

Modelos para o sistema de referência e afiliados:
- ReferralCode: Códigos únicos de referência por usuário
- Referral: Relacionamento de referência (quem indicou quem)
- CreditTransaction: Ledger imutável de transações de crédito
- AffiliateTracking: Métricas e conversões de afiliados
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Text, Index, ForeignKey, Enum
)
from sqlalchemy.orm import relationship
import enum

from src.config.database import Base


class TransactionType(enum.Enum):
    """Tipos de transações de crédito."""
    REFERRAL_BONUS = "referral_bonus"  # $25 para quem indicou
    WELCOME_CREDIT = "welcome_credit"  # $10 para novo usuário
    AFFILIATE_PAYOUT = "affiliate_payout"  # Pagamento de afiliado
    CREDIT_RETRACTION = "credit_retraction"  # Retração por fraude/reembolso
    MANUAL_ADJUSTMENT = "manual_adjustment"  # Ajuste manual por admin


class ReferralStatus(enum.Enum):
    """Status de uma referência."""
    PENDING = "pending"  # Aguardando verificação de email
    ACTIVE = "active"  # Email verificado, aguardando threshold
    COMPLETED = "completed"  # Threshold atingido, reward granted
    EXPIRED = "expired"  # Código expirado sem conversão
    FRAUD = "fraud"  # Bloqueado por fraude


class ReferralCode(Base):
    """
    Códigos de referência únicos por usuário.

    Cada usuário tem um código de referência único e permanente.
    Códigos são alfanuméricos de 8-12 caracteres.
    """
    __tablename__ = "referral_codes"

    id = Column(Integer, primary_key=True, index=True)

    # Identificação do usuário
    user_id = Column(String(100), nullable=False, unique=True, index=True)

    # Código de referência único
    code = Column(String(12), nullable=False, unique=True, index=True)

    # Status do código
    is_active = Column(Boolean, default=True, nullable=False)

    # Estatísticas
    total_clicks = Column(Integer, default=0)  # Quantas vezes o link foi acessado
    total_signups = Column(Integer, default=0)  # Quantos usuários se cadastraram
    total_conversions = Column(Integer, default=0)  # Quantos atingiram threshold
    total_earnings = Column(Float, default=0.0)  # Total ganho em créditos

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)  # Último uso do código
    expires_at = Column(DateTime, nullable=True)  # NULL = não expira

    # Relacionamentos
    referrals = relationship("Referral", back_populates="referral_code_obj", foreign_keys="Referral.referral_code_id")

    __table_args__ = (
        Index('idx_referral_code_user', 'user_id'),
        Index('idx_referral_code_active', 'is_active', 'code'),
        Index('idx_referral_code_created', 'created_at'),
    )

    @property
    def is_expired(self) -> bool:
        """Verifica se o código está expirado."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def is_usable(self) -> bool:
        """Verifica se o código pode ser usado."""
        return self.is_active and not self.is_expired

    @property
    def conversion_rate(self) -> float:
        """Calcula taxa de conversão (conversões/signups)."""
        if self.total_signups == 0:
            return 0.0
        return round(self.total_conversions / self.total_signups, 4)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "code": self.code,
            "is_active": self.is_active,
            "is_usable": self.is_usable,
            "total_clicks": self.total_clicks,
            "total_signups": self.total_signups,
            "total_conversions": self.total_conversions,
            "total_earnings": self.total_earnings,
            "conversion_rate": self.conversion_rate,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    def __repr__(self):
        status = "ACTIVE" if self.is_usable else "INACTIVE"
        return f"<ReferralCode [{status}] {self.code} user={self.user_id}>"


class Referral(Base):
    """
    Relacionamento de referência entre usuários.

    Registra quem indicou quem e o status do processo de referência.
    Usado para rastrear quando o threshold de $50 é atingido.
    """
    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, index=True)

    # Relacionamento de referência
    referrer_id = Column(String(100), nullable=False, index=True)  # Quem indicou
    referred_id = Column(String(100), nullable=False, unique=True, index=True)  # Quem foi indicado
    referral_code_id = Column(Integer, ForeignKey("referral_codes.id"), nullable=False, index=True)

    # Status da referência
    status = Column(String(20), default=ReferralStatus.PENDING.value, nullable=False, index=True)

    # Verificação
    email_verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime, nullable=True)

    # Tracking de gastos do indicado
    referred_total_spend = Column(Float, default=0.0)  # Total gasto pelo indicado
    spend_threshold = Column(Float, default=50.0)  # Threshold para reward ($50)
    threshold_reached_at = Column(DateTime, nullable=True)  # Quando atingiu threshold

    # Rewards
    referrer_reward_amount = Column(Float, default=25.0)  # $25 para quem indicou
    referred_welcome_credit = Column(Float, default=10.0)  # $10 para novo usuário
    reward_granted = Column(Boolean, default=False)  # Reward já foi dado
    reward_granted_at = Column(DateTime, nullable=True)
    welcome_credit_granted = Column(Boolean, default=False)  # Welcome credit já foi dado
    welcome_credit_granted_at = Column(DateTime, nullable=True)

    # Anti-fraude
    referrer_ip = Column(String(45), nullable=True)  # IPv6 pode ter até 45 chars
    referred_ip = Column(String(45), nullable=True)
    is_suspicious = Column(Boolean, default=False)
    fraud_reason = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    referral_code_obj = relationship("ReferralCode", back_populates="referrals", foreign_keys=[referral_code_id])

    __table_args__ = (
        Index('idx_referral_referrer', 'referrer_id', 'created_at'),
        Index('idx_referral_referred', 'referred_id'),
        Index('idx_referral_status', 'status', 'created_at'),
        Index('idx_referral_reward', 'reward_granted', 'threshold_reached_at'),
        Index('idx_referral_suspicious', 'is_suspicious', 'created_at'),
    )

    @property
    def is_threshold_reached(self) -> bool:
        """Verifica se o threshold de gastos foi atingido."""
        return self.referred_total_spend >= self.spend_threshold

    @property
    def spend_progress(self) -> float:
        """Retorna progresso em direção ao threshold (0.0 a 1.0)."""
        if self.spend_threshold == 0:
            return 1.0
        return min(1.0, self.referred_total_spend / self.spend_threshold)

    def to_dict(self):
        return {
            "id": self.id,
            "referrer_id": self.referrer_id,
            "referred_id": self.referred_id,
            "referral_code_id": self.referral_code_id,
            "status": self.status,
            "email_verified": self.email_verified,
            "referred_total_spend": self.referred_total_spend,
            "spend_threshold": self.spend_threshold,
            "spend_progress": self.spend_progress,
            "is_threshold_reached": self.is_threshold_reached,
            "reward_granted": self.reward_granted,
            "reward_granted_at": self.reward_granted_at.isoformat() if self.reward_granted_at else None,
            "welcome_credit_granted": self.welcome_credit_granted,
            "is_suspicious": self.is_suspicious,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Referral {self.referrer_id} -> {self.referred_id} [{self.status}]>"


class CreditTransaction(Base):
    """
    Ledger imutável de transações de crédito.

    Todas as transações de crédito são registradas aqui para auditoria.
    Esta tabela é append-only (não deve haver updates ou deletes).
    """
    __tablename__ = "credit_transactions"

    id = Column(Integer, primary_key=True, index=True)

    # Identificação
    user_id = Column(String(100), nullable=False, index=True)
    transaction_type = Column(String(50), nullable=False, index=True)  # referral_bonus, welcome_credit, etc

    # Valores
    amount = Column(Float, nullable=False)  # Valor da transação (positivo = crédito, negativo = débito)
    balance_before = Column(Float, nullable=False)  # Saldo antes da transação
    balance_after = Column(Float, nullable=False)  # Saldo após a transação

    # Referência
    referral_id = Column(Integer, ForeignKey("referrals.id"), nullable=True, index=True)
    reference_id = Column(String(100), nullable=True)  # ID externo de referência
    reference_type = Column(String(50), nullable=True)  # Tipo de referência (billing_id, payout_id, etc)

    # Descrição
    description = Column(String(500), nullable=True)

    # Metadados
    created_by = Column(String(100), nullable=True)  # user_id ou "system"
    ip_address = Column(String(45), nullable=True)

    # Timestamp (imutável)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index('idx_credit_tx_user', 'user_id', 'created_at'),
        Index('idx_credit_tx_type', 'transaction_type', 'created_at'),
        Index('idx_credit_tx_referral', 'referral_id'),
        Index('idx_credit_tx_reference', 'reference_type', 'reference_id'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "transaction_type": self.transaction_type,
            "amount": self.amount,
            "balance_before": self.balance_before,
            "balance_after": self.balance_after,
            "referral_id": self.referral_id,
            "reference_id": self.reference_id,
            "reference_type": self.reference_type,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        sign = "+" if self.amount >= 0 else ""
        return f"<CreditTransaction {self.user_id} {sign}${self.amount} ({self.transaction_type})>"


class AffiliateTracking(Base):
    """
    Tracking de métricas de afiliados.

    Rastreia cliques, conversões e pagamentos para afiliados.
    Usado para o dashboard de afiliados.
    """
    __tablename__ = "affiliate_tracking"

    id = Column(Integer, primary_key=True, index=True)

    # Identificação do afiliado
    affiliate_id = Column(String(100), nullable=False, index=True)  # user_id do afiliado
    referral_code_id = Column(Integer, ForeignKey("referral_codes.id"), nullable=False, index=True)

    # Período de tracking (para agregação por dia/semana/mês)
    tracking_date = Column(DateTime, nullable=False, index=True)  # Data do tracking

    # Métricas de cliques
    clicks = Column(Integer, default=0)
    unique_clicks = Column(Integer, default=0)

    # Métricas de conversão
    signups = Column(Integer, default=0)  # Novos cadastros
    verified_signups = Column(Integer, default=0)  # Cadastros com email verificado
    conversions = Column(Integer, default=0)  # Atingiram threshold

    # Métricas financeiras
    revenue_generated = Column(Float, default=0.0)  # Receita gerada pelos indicados
    credits_earned = Column(Float, default=0.0)  # Créditos ganhos pelo afiliado
    credits_pending = Column(Float, default=0.0)  # Créditos pendentes
    credits_paid = Column(Float, default=0.0)  # Créditos já pagos

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_affiliate_user', 'affiliate_id', 'tracking_date'),
        Index('idx_affiliate_date', 'tracking_date'),
        Index('idx_affiliate_code', 'referral_code_id', 'tracking_date'),
    )

    @property
    def click_to_signup_rate(self) -> float:
        """Taxa de conversão de cliques para signups."""
        if self.unique_clicks == 0:
            return 0.0
        return round(self.signups / self.unique_clicks, 4)

    @property
    def signup_to_conversion_rate(self) -> float:
        """Taxa de conversão de signups para conversões."""
        if self.signups == 0:
            return 0.0
        return round(self.conversions / self.signups, 4)

    @property
    def total_conversion_rate(self) -> float:
        """Taxa de conversão total (cliques para conversões)."""
        if self.unique_clicks == 0:
            return 0.0
        return round(self.conversions / self.unique_clicks, 4)

    def to_dict(self):
        return {
            "id": self.id,
            "affiliate_id": self.affiliate_id,
            "referral_code_id": self.referral_code_id,
            "tracking_date": self.tracking_date.isoformat() if self.tracking_date else None,
            "clicks": self.clicks,
            "unique_clicks": self.unique_clicks,
            "signups": self.signups,
            "verified_signups": self.verified_signups,
            "conversions": self.conversions,
            "revenue_generated": self.revenue_generated,
            "credits_earned": self.credits_earned,
            "credits_pending": self.credits_pending,
            "credits_paid": self.credits_paid,
            "click_to_signup_rate": self.click_to_signup_rate,
            "signup_to_conversion_rate": self.signup_to_conversion_rate,
            "total_conversion_rate": self.total_conversion_rate,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<AffiliateTracking {self.affiliate_id} {self.tracking_date.strftime('%Y-%m-%d') if self.tracking_date else 'N/A'} clicks={self.clicks} conv={self.conversions}>"
