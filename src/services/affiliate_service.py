"""
Serviço para gerenciar tracking e analytics de afiliados.

Responsável por:
- Rastrear métricas de conversão (cliques, signups, conversões)
- Agregar estatísticas para o dashboard de afiliados
- Gerar relatórios e exportação de dados
- Gerenciar tracking diário de métricas
"""
import csv
import io
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from src.models.referral import (
    AffiliateTracking, ReferralCode, Referral, CreditTransaction,
    TransactionType, ReferralStatus
)


class AffiliateService:
    """
    Serviço para tracking e analytics de afiliados.

    Fornece métricas de conversão, estatísticas para dashboard,
    e funcionalidades de exportação de dados.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_or_create_daily_tracking(
        self,
        affiliate_id: str,
        referral_code_id: int,
        tracking_date: Optional[datetime] = None
    ) -> AffiliateTracking:
        """
        Obtém ou cria registro de tracking para um dia específico.

        Args:
            affiliate_id: ID do afiliado
            referral_code_id: ID do código de referência
            tracking_date: Data do tracking (default: hoje)

        Returns:
            AffiliateTracking: Registro de tracking
        """
        if tracking_date is None:
            tracking_date = datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        else:
            tracking_date = tracking_date.replace(
                hour=0, minute=0, second=0, microsecond=0
            )

        # Buscar registro existente
        existing = self.db.query(AffiliateTracking).filter(
            AffiliateTracking.affiliate_id == affiliate_id,
            AffiliateTracking.referral_code_id == referral_code_id,
            AffiliateTracking.tracking_date == tracking_date
        ).first()

        if existing:
            return existing

        # Criar novo registro
        tracking = AffiliateTracking(
            affiliate_id=affiliate_id,
            referral_code_id=referral_code_id,
            tracking_date=tracking_date,
            clicks=0,
            unique_clicks=0,
            signups=0,
            verified_signups=0,
            conversions=0,
            revenue_generated=0.0,
            credits_earned=0.0,
            credits_pending=0.0,
            credits_paid=0.0,
            created_at=datetime.utcnow()
        )

        self.db.add(tracking)
        self.db.commit()
        self.db.refresh(tracking)

        return tracking

    def record_click(
        self,
        affiliate_id: str,
        referral_code_id: int,
        is_unique: bool = True
    ) -> AffiliateTracking:
        """
        Registra um clique em link de afiliado.

        Args:
            affiliate_id: ID do afiliado
            referral_code_id: ID do código de referência
            is_unique: Se é um clique único (novo visitante)

        Returns:
            AffiliateTracking: Registro atualizado
        """
        tracking = self.get_or_create_daily_tracking(
            affiliate_id, referral_code_id
        )

        tracking.clicks += 1
        if is_unique:
            tracking.unique_clicks += 1
        tracking.updated_at = datetime.utcnow()

        self.db.commit()
        return tracking

    def record_signup(
        self,
        affiliate_id: str,
        referral_code_id: int,
        is_verified: bool = False
    ) -> AffiliateTracking:
        """
        Registra um novo signup através de link de afiliado.

        Args:
            affiliate_id: ID do afiliado
            referral_code_id: ID do código de referência
            is_verified: Se o email já foi verificado

        Returns:
            AffiliateTracking: Registro atualizado
        """
        tracking = self.get_or_create_daily_tracking(
            affiliate_id, referral_code_id
        )

        tracking.signups += 1
        if is_verified:
            tracking.verified_signups += 1
        tracking.updated_at = datetime.utcnow()

        self.db.commit()
        return tracking

    def record_email_verification(
        self,
        affiliate_id: str,
        referral_code_id: int
    ) -> AffiliateTracking:
        """
        Registra verificação de email de um signup.

        Args:
            affiliate_id: ID do afiliado
            referral_code_id: ID do código de referência

        Returns:
            AffiliateTracking: Registro atualizado
        """
        tracking = self.get_or_create_daily_tracking(
            affiliate_id, referral_code_id
        )

        tracking.verified_signups += 1
        tracking.updated_at = datetime.utcnow()

        self.db.commit()
        return tracking

    def record_conversion(
        self,
        affiliate_id: str,
        referral_code_id: int,
        revenue: float,
        credits_earned: float
    ) -> AffiliateTracking:
        """
        Registra uma conversão (usuário atingiu threshold de $50).

        Args:
            affiliate_id: ID do afiliado
            referral_code_id: ID do código de referência
            revenue: Receita gerada pelo indicado
            credits_earned: Créditos ganhos pelo afiliado

        Returns:
            AffiliateTracking: Registro atualizado
        """
        tracking = self.get_or_create_daily_tracking(
            affiliate_id, referral_code_id
        )

        tracking.conversions += 1
        tracking.revenue_generated = round(
            tracking.revenue_generated + revenue, 2
        )
        tracking.credits_earned = round(
            tracking.credits_earned + credits_earned, 2
        )
        tracking.updated_at = datetime.utcnow()

        self.db.commit()
        return tracking

    def get_affiliate_stats(
        self,
        affiliate_id: str,
        period: str = "month"
    ) -> Dict:
        """
        Retorna estatísticas do afiliado para o período especificado.

        Args:
            affiliate_id: ID do afiliado
            period: Período ("day", "week", "month", "year", "all")

        Returns:
            Dict com estatísticas do afiliado
        """
        now = datetime.utcnow()

        if period == "day":
            start_date = now - timedelta(days=1)
        elif period == "week":
            start_date = now - timedelta(weeks=1)
        elif period == "year":
            start_date = now - timedelta(days=365)
        elif period == "all":
            start_date = datetime(2000, 1, 1)  # Início de tudo
        else:  # default month
            start_date = now - timedelta(days=30)

        # Agregar métricas do período
        stats_query = self.db.query(
            func.sum(AffiliateTracking.clicks).label("total_clicks"),
            func.sum(AffiliateTracking.unique_clicks).label("unique_clicks"),
            func.sum(AffiliateTracking.signups).label("total_signups"),
            func.sum(AffiliateTracking.verified_signups).label("verified_signups"),
            func.sum(AffiliateTracking.conversions).label("total_conversions"),
            func.sum(AffiliateTracking.revenue_generated).label("total_revenue"),
            func.sum(AffiliateTracking.credits_earned).label("total_earnings"),
            func.sum(AffiliateTracking.credits_pending).label("pending_earnings"),
            func.sum(AffiliateTracking.credits_paid).label("paid_earnings")
        ).filter(
            AffiliateTracking.affiliate_id == affiliate_id,
            AffiliateTracking.tracking_date >= start_date
        ).first()

        total_clicks = stats_query.total_clicks or 0
        unique_clicks = stats_query.unique_clicks or 0
        total_signups = stats_query.total_signups or 0
        verified_signups = stats_query.verified_signups or 0
        total_conversions = stats_query.total_conversions or 0
        total_revenue = stats_query.total_revenue or 0.0
        total_earnings = stats_query.total_earnings or 0.0
        pending_earnings = stats_query.pending_earnings or 0.0
        paid_earnings = stats_query.paid_earnings or 0.0

        # Calcular taxas de conversão
        click_to_signup_rate = 0.0
        if unique_clicks > 0:
            click_to_signup_rate = round(total_signups / unique_clicks, 4)

        signup_to_conversion_rate = 0.0
        if total_signups > 0:
            signup_to_conversion_rate = round(total_conversions / total_signups, 4)

        total_conversion_rate = 0.0
        if unique_clicks > 0:
            total_conversion_rate = round(total_conversions / unique_clicks, 4)

        # Buscar código de referência do afiliado
        referral_code = self.db.query(ReferralCode).filter(
            ReferralCode.user_id == affiliate_id
        ).first()

        return {
            "period": period,
            "affiliate_id": affiliate_id,
            "referral_code": referral_code.code if referral_code else None,
            "metrics": {
                "total_clicks": total_clicks,
                "unique_clicks": unique_clicks,
                "total_signups": total_signups,
                "verified_signups": verified_signups,
                "total_conversions": total_conversions,
            },
            "rates": {
                "click_to_signup_rate": round(click_to_signup_rate * 100, 2),
                "signup_to_conversion_rate": round(signup_to_conversion_rate * 100, 2),
                "total_conversion_rate": round(total_conversion_rate * 100, 2),
            },
            "earnings": {
                "total_revenue": round(total_revenue, 2),
                "total_earnings": round(total_earnings, 2),
                "pending_earnings": round(pending_earnings, 2),
                "paid_earnings": round(paid_earnings, 2),
            }
        }

    def get_daily_metrics(
        self,
        affiliate_id: str,
        days: int = 30
    ) -> List[Dict]:
        """
        Retorna métricas diárias para gráficos do dashboard.

        Args:
            affiliate_id: ID do afiliado
            days: Número de dias para retornar

        Returns:
            Lista de dicts com métricas por dia
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

        tracking_records = self.db.query(AffiliateTracking).filter(
            AffiliateTracking.affiliate_id == affiliate_id,
            AffiliateTracking.tracking_date >= start_date
        ).order_by(AffiliateTracking.tracking_date).all()

        # Criar mapa de datas para fácil acesso
        tracking_map = {
            t.tracking_date.strftime("%Y-%m-%d"): t
            for t in tracking_records
        }

        # Gerar lista com todos os dias (incluindo zeros)
        result = []
        current_date = start_date

        while current_date <= datetime.utcnow():
            date_key = current_date.strftime("%Y-%m-%d")
            tracking = tracking_map.get(date_key)

            if tracking:
                result.append({
                    "date": date_key,
                    "clicks": tracking.clicks,
                    "unique_clicks": tracking.unique_clicks,
                    "signups": tracking.signups,
                    "conversions": tracking.conversions,
                    "revenue": round(tracking.revenue_generated, 2),
                    "earnings": round(tracking.credits_earned, 2)
                })
            else:
                result.append({
                    "date": date_key,
                    "clicks": 0,
                    "unique_clicks": 0,
                    "signups": 0,
                    "conversions": 0,
                    "revenue": 0.0,
                    "earnings": 0.0
                })

            current_date += timedelta(days=1)

        return result

    def get_referrals_list(
        self,
        affiliate_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """
        Retorna lista de referências do afiliado.

        Args:
            affiliate_id: ID do afiliado
            status: Filtrar por status (opcional)
            limit: Limite de resultados
            offset: Offset para paginação

        Returns:
            Lista de dicts com informações das referências
        """
        query = self.db.query(Referral).filter(
            Referral.referrer_id == affiliate_id
        )

        if status:
            query = query.filter(Referral.status == status)

        referrals = query.order_by(
            Referral.created_at.desc()
        ).offset(offset).limit(limit).all()

        return [
            {
                "id": r.id,
                "status": r.status,
                "email_verified": r.email_verified,
                "spend_progress": round(r.spend_progress * 100, 1),
                "current_spend": round(r.referred_total_spend, 2),
                "threshold": round(r.spend_threshold, 2),
                "reward_amount": round(r.referrer_reward_amount, 2),
                "reward_granted": r.reward_granted,
                "welcome_credit_granted": r.welcome_credit_granted,
                "is_suspicious": r.is_suspicious,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "reward_granted_at": r.reward_granted_at.isoformat() if r.reward_granted_at else None,
            }
            for r in referrals
        ]

    def get_payout_history(
        self,
        affiliate_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """
        Retorna histórico de pagamentos do afiliado.

        Args:
            affiliate_id: ID do afiliado
            limit: Limite de resultados
            offset: Offset para paginação

        Returns:
            Lista de dicts com informações de pagamentos
        """
        # Buscar transações de crédito relacionadas a referências
        transactions = self.db.query(CreditTransaction).filter(
            CreditTransaction.user_id == affiliate_id,
            CreditTransaction.transaction_type.in_([
                TransactionType.REFERRAL_BONUS.value,
                TransactionType.AFFILIATE_PAYOUT.value
            ])
        ).order_by(
            CreditTransaction.created_at.desc()
        ).offset(offset).limit(limit).all()

        return [
            {
                "id": t.id,
                "type": t.transaction_type,
                "amount": round(t.amount, 2),
                "balance_after": round(t.balance_after, 2),
                "description": t.description,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in transactions
        ]

    def get_top_affiliates(
        self,
        period: str = "month",
        limit: int = 10
    ) -> List[Dict]:
        """
        Retorna ranking dos top afiliados.

        Args:
            period: Período ("week", "month", "year", "all")
            limit: Número de afiliados a retornar

        Returns:
            Lista de dicts com informações dos top afiliados
        """
        now = datetime.utcnow()

        if period == "week":
            start_date = now - timedelta(weeks=1)
        elif period == "year":
            start_date = now - timedelta(days=365)
        elif period == "all":
            start_date = datetime(2000, 1, 1)
        else:  # default month
            start_date = now - timedelta(days=30)

        # Agregar por afiliado
        top_query = self.db.query(
            AffiliateTracking.affiliate_id,
            func.sum(AffiliateTracking.conversions).label("total_conversions"),
            func.sum(AffiliateTracking.signups).label("total_signups"),
            func.sum(AffiliateTracking.credits_earned).label("total_earnings"),
            func.sum(AffiliateTracking.revenue_generated).label("total_revenue")
        ).filter(
            AffiliateTracking.tracking_date >= start_date
        ).group_by(
            AffiliateTracking.affiliate_id
        ).order_by(
            func.sum(AffiliateTracking.conversions).desc()
        ).limit(limit).all()

        result = []
        for i, row in enumerate(top_query):
            result.append({
                "rank": i + 1,
                "affiliate_id": row.affiliate_id,
                "total_conversions": row.total_conversions or 0,
                "total_signups": row.total_signups or 0,
                "total_earnings": round(row.total_earnings or 0, 2),
                "total_revenue": round(row.total_revenue or 0, 2)
            })

        return result

    def export_to_csv(
        self,
        affiliate_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> str:
        """
        Exporta dados do afiliado para CSV (para relatórios fiscais).

        Args:
            affiliate_id: ID do afiliado
            start_date: Data de início (default: 1 ano atrás)
            end_date: Data de fim (default: hoje)

        Returns:
            str: Conteúdo CSV
        """
        if start_date is None:
            start_date = datetime.utcnow() - timedelta(days=365)
        if end_date is None:
            end_date = datetime.utcnow()

        # Buscar transações de crédito
        transactions = self.db.query(CreditTransaction).filter(
            CreditTransaction.user_id == affiliate_id,
            CreditTransaction.transaction_type.in_([
                TransactionType.REFERRAL_BONUS.value,
                TransactionType.AFFILIATE_PAYOUT.value
            ]),
            CreditTransaction.created_at >= start_date,
            CreditTransaction.created_at <= end_date
        ).order_by(CreditTransaction.created_at).all()

        # Criar CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "Transaction ID",
            "Date",
            "Type",
            "Amount",
            "Balance After",
            "Description"
        ])

        # Dados
        for t in transactions:
            writer.writerow([
                t.id,
                t.created_at.strftime("%Y-%m-%d %H:%M:%S") if t.created_at else "",
                t.transaction_type,
                round(t.amount, 2),
                round(t.balance_after, 2),
                t.description or ""
            ])

        return output.getvalue()

    def get_lifetime_stats(self, affiliate_id: str) -> Dict:
        """
        Retorna estatísticas de lifetime do afiliado.

        Args:
            affiliate_id: ID do afiliado

        Returns:
            Dict com estatísticas de lifetime
        """
        # Buscar código de referência
        referral_code = self.db.query(ReferralCode).filter(
            ReferralCode.user_id == affiliate_id
        ).first()

        if not referral_code:
            return {
                "has_code": False,
                "code": None,
                "total_clicks": 0,
                "total_signups": 0,
                "total_conversions": 0,
                "total_earnings": 0.0,
                "conversion_rate": 0.0,
                "member_since": None
            }

        return {
            "has_code": True,
            "code": referral_code.code,
            "total_clicks": referral_code.total_clicks,
            "total_signups": referral_code.total_signups,
            "total_conversions": referral_code.total_conversions,
            "total_earnings": round(referral_code.total_earnings, 2),
            "conversion_rate": round(referral_code.conversion_rate * 100, 2),
            "member_since": referral_code.created_at.isoformat() if referral_code.created_at else None
        }

    def sync_tracking_with_referral_code(self, affiliate_id: str) -> None:
        """
        Sincroniza métricas do AffiliateTracking com ReferralCode.

        Útil para recalcular totais após alterações manuais.

        Args:
            affiliate_id: ID do afiliado
        """
        referral_code = self.db.query(ReferralCode).filter(
            ReferralCode.user_id == affiliate_id
        ).first()

        if not referral_code:
            return

        # Agregar todos os trackings
        totals = self.db.query(
            func.sum(AffiliateTracking.clicks).label("clicks"),
            func.sum(AffiliateTracking.signups).label("signups"),
            func.sum(AffiliateTracking.conversions).label("conversions"),
            func.sum(AffiliateTracking.credits_earned).label("earnings")
        ).filter(
            AffiliateTracking.affiliate_id == affiliate_id
        ).first()

        # Atualizar ReferralCode
        referral_code.total_clicks = totals.clicks or 0
        referral_code.total_signups = totals.signups or 0
        referral_code.total_conversions = totals.conversions or 0
        referral_code.total_earnings = round(totals.earnings or 0, 2)

        self.db.commit()

    def update_pending_to_paid(
        self,
        affiliate_id: str,
        amount: float
    ) -> None:
        """
        Atualiza créditos pendentes para pagos (após payout).

        Args:
            affiliate_id: ID do afiliado
            amount: Valor pago
        """
        # Buscar trackings com créditos pendentes
        trackings = self.db.query(AffiliateTracking).filter(
            AffiliateTracking.affiliate_id == affiliate_id,
            AffiliateTracking.credits_pending > 0
        ).order_by(AffiliateTracking.tracking_date).all()

        remaining = amount
        for tracking in trackings:
            if remaining <= 0:
                break

            to_pay = min(tracking.credits_pending, remaining)
            tracking.credits_pending = round(tracking.credits_pending - to_pay, 2)
            tracking.credits_paid = round(tracking.credits_paid + to_pay, 2)
            remaining -= to_pay

        self.db.commit()

    def get_dashboard_summary(self, affiliate_id: str) -> Dict:
        """
        Retorna resumo completo para o dashboard do afiliado.

        Combina estatísticas de período atual, lifetime e métricas diárias.

        Args:
            affiliate_id: ID do afiliado

        Returns:
            Dict com resumo completo do dashboard
        """
        return {
            "lifetime": self.get_lifetime_stats(affiliate_id),
            "current_month": self.get_affiliate_stats(affiliate_id, "month"),
            "current_week": self.get_affiliate_stats(affiliate_id, "week"),
            "daily_metrics": self.get_daily_metrics(affiliate_id, days=30),
            "recent_referrals": self.get_referrals_list(affiliate_id, limit=10),
            "recent_payouts": self.get_payout_history(affiliate_id, limit=5)
        }
