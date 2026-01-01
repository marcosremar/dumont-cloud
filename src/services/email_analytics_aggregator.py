"""
Serviço de agregação de analytics para relatórios de email.

Calcula:
- Total de horas de GPU e custos para período especificado
- Economia vs AWS/GCP/Azure
- Comparação semana-a-semana (week-over-week)
- Breakdown por tipo de GPU
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.models.usage import UsageRecord, GPUPricingReference
from src.models.instance_status import HibernationEvent, InstanceStatus


@dataclass
class WeeklyUsageMetrics:
    """Métricas de uso semanal agregadas."""

    # Período
    week_start: datetime
    week_end: datetime

    # Métricas de uso
    total_hours: float
    total_cost_dumont: float
    total_cost_aws: float
    total_cost_gcp: float
    total_cost_azure: float

    # Economia
    savings_vs_aws: float
    savings_vs_gcp: float
    savings_vs_azure: float
    savings_percentage_aws: float

    # Auto-hibernação
    auto_hibernate_savings: float

    # Contadores
    total_sessions: int
    unique_gpus_used: int

    # Flags
    is_first_week: bool = False
    has_usage: bool = True

    def to_dict(self) -> Dict:
        """Converte para dicionário para uso em templates."""
        return {
            'week_start': self.week_start.isoformat(),
            'week_end': self.week_end.isoformat(),
            'week_start_formatted': self.week_start.strftime('%B %d'),
            'week_end_formatted': self.week_end.strftime('%B %d, %Y'),
            'total_hours': round(self.total_hours, 1),
            'total_cost_dumont': round(self.total_cost_dumont, 2),
            'total_cost_aws': round(self.total_cost_aws, 2),
            'total_cost_gcp': round(self.total_cost_gcp, 2),
            'total_cost_azure': round(self.total_cost_azure, 2),
            'savings_vs_aws': round(self.savings_vs_aws, 2),
            'savings_vs_gcp': round(self.savings_vs_gcp, 2),
            'savings_vs_azure': round(self.savings_vs_azure, 2),
            'savings_percentage_aws': round(self.savings_percentage_aws, 1),
            'auto_hibernate_savings': round(self.auto_hibernate_savings, 2),
            'total_sessions': self.total_sessions,
            'unique_gpus_used': self.unique_gpus_used,
            'is_first_week': self.is_first_week,
            'has_usage': self.has_usage,
        }


@dataclass
class WeekOverWeekComparison:
    """Comparação semana-a-semana."""

    # Mudanças em porcentagem
    hours_change_percent: float
    cost_change_percent: float
    savings_change_percent: float

    # Direção da mudança
    hours_trend: str  # 'up', 'down', 'stable'
    cost_trend: str
    savings_trend: str

    # Valores absolutos de mudança
    hours_diff: float
    cost_diff: float
    savings_diff: float

    # Flag se comparação é válida
    has_previous_week: bool = True

    def to_dict(self) -> Dict:
        """Converte para dicionário para uso em templates."""
        return {
            'hours_change_percent': round(self.hours_change_percent, 1),
            'cost_change_percent': round(self.cost_change_percent, 1),
            'savings_change_percent': round(self.savings_change_percent, 1),
            'hours_trend': self.hours_trend,
            'cost_trend': self.cost_trend,
            'savings_trend': self.savings_trend,
            'hours_diff': round(self.hours_diff, 1),
            'cost_diff': round(self.cost_diff, 2),
            'savings_diff': round(self.savings_diff, 2),
            'has_previous_week': self.has_previous_week,
        }


@dataclass
class GPUBreakdown:
    """Breakdown de uso por tipo de GPU."""

    gpu_type: str
    hours: float
    cost_dumont: float
    cost_aws: float
    savings: float
    sessions: int

    def to_dict(self) -> Dict:
        """Converte para dicionário."""
        return {
            'gpu_type': self.gpu_type,
            'hours': round(self.hours, 1),
            'cost_dumont': round(self.cost_dumont, 2),
            'cost_aws': round(self.cost_aws, 2),
            'savings': round(self.savings, 2),
            'sessions': self.sessions,
        }


class EmailAnalyticsAggregator:
    """Agregador de analytics para relatórios de email."""

    def __init__(self, db: Session):
        self.db = db

    def get_week_bounds(self, reference_date: Optional[datetime] = None) -> Tuple[datetime, datetime]:
        """
        Retorna os limites da semana anterior (segunda a domingo).

        Args:
            reference_date: Data de referência. Se None, usa data atual.

        Returns:
            Tuple com (início_segunda, fim_domingo) da semana anterior.
        """
        if reference_date is None:
            reference_date = datetime.utcnow()

        # Encontrar a última segunda-feira (início da semana anterior)
        days_since_monday = reference_date.weekday()

        # Se hoje é segunda, voltamos 7 dias. Senão, voltamos até a segunda anterior
        if days_since_monday == 0:
            # Hoje é segunda, a semana anterior começou há 7 dias
            week_start = reference_date - timedelta(days=7)
        else:
            # Voltar para segunda atual e depois mais 7 dias
            week_start = reference_date - timedelta(days=days_since_monday + 7)

        # Ajustar para meia-noite
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        # Fim da semana é domingo 23:59:59
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

        return week_start, week_end

    def calculate_weekly_metrics(
        self,
        user_id: str,
        week_start: datetime,
        week_end: datetime
    ) -> WeeklyUsageMetrics:
        """
        Calcula métricas de uso para uma semana específica.

        Args:
            user_id: ID do usuário
            week_start: Início da semana (segunda-feira 00:00)
            week_end: Fim da semana (domingo 23:59)

        Returns:
            WeeklyUsageMetrics com todos os dados agregados
        """
        # Query agregada de uso
        usage_query = self.db.query(
            func.sum(UsageRecord.cost_dumont).label("total_dumont"),
            func.sum(UsageRecord.cost_aws_equivalent).label("total_aws"),
            func.sum(UsageRecord.cost_gcp_equivalent).label("total_gcp"),
            func.sum(UsageRecord.cost_azure_equivalent).label("total_azure"),
            func.sum(UsageRecord.duration_minutes).label("total_minutes"),
            func.count(UsageRecord.id).label("total_sessions"),
            func.count(func.distinct(UsageRecord.gpu_type)).label("unique_gpus")
        ).filter(
            UsageRecord.user_id == user_id,
            UsageRecord.started_at >= week_start,
            UsageRecord.started_at <= week_end
        ).first()

        total_dumont = usage_query.total_dumont or 0.0
        total_aws = usage_query.total_aws or 0.0
        total_gcp = usage_query.total_gcp or 0.0
        total_azure = usage_query.total_azure or 0.0
        total_minutes = usage_query.total_minutes or 0
        total_sessions = usage_query.total_sessions or 0
        unique_gpus = usage_query.unique_gpus or 0

        # Calcular economia de auto-hibernação
        hibernation_savings = self._calculate_hibernation_savings(
            user_id, week_start, week_end
        )

        # Adicionar savings de hibernação ao AWS equivalent
        total_aws += hibernation_savings

        # Calcular economia
        savings_vs_aws = total_aws - total_dumont
        savings_vs_gcp = total_gcp - total_dumont
        savings_vs_azure = total_azure - total_dumont

        # Porcentagem de economia vs AWS
        savings_percentage_aws = 0.0
        if total_aws > 0:
            savings_percentage_aws = (savings_vs_aws / total_aws) * 100

        # Verificar se é primeira semana do usuário
        is_first_week = self._is_first_week(user_id, week_start)

        return WeeklyUsageMetrics(
            week_start=week_start,
            week_end=week_end,
            total_hours=total_minutes / 60,
            total_cost_dumont=total_dumont,
            total_cost_aws=total_aws,
            total_cost_gcp=total_gcp,
            total_cost_azure=total_azure,
            savings_vs_aws=savings_vs_aws,
            savings_vs_gcp=savings_vs_gcp,
            savings_vs_azure=savings_vs_azure,
            savings_percentage_aws=savings_percentage_aws,
            auto_hibernate_savings=hibernation_savings,
            total_sessions=total_sessions,
            unique_gpus_used=unique_gpus,
            is_first_week=is_first_week,
            has_usage=total_sessions > 0
        )

    def _calculate_hibernation_savings(
        self,
        user_id: str,
        week_start: datetime,
        week_end: datetime
    ) -> float:
        """Calcula economia de auto-hibernação para o período."""
        try:
            savings = self.db.query(func.sum(HibernationEvent.savings_usd))\
                .join(InstanceStatus, InstanceStatus.instance_id == HibernationEvent.instance_id)\
                .filter(InstanceStatus.user_id == user_id)\
                .filter(HibernationEvent.timestamp >= week_start)\
                .filter(HibernationEvent.timestamp <= week_end)\
                .scalar()
            return savings or 0.0
        except Exception:
            # Se tabelas não existem ou erro de join, retornar 0
            return 0.0

    def _is_first_week(self, user_id: str, week_start: datetime) -> bool:
        """Verifica se esta é a primeira semana de uso do usuário."""
        first_usage = self.db.query(func.min(UsageRecord.started_at))\
            .filter(UsageRecord.user_id == user_id)\
            .scalar()

        if first_usage is None:
            return True

        # Se o primeiro uso foi nesta semana ou na anterior
        return first_usage >= week_start - timedelta(days=7)

    def calculate_week_over_week(
        self,
        current_week: WeeklyUsageMetrics,
        previous_week: WeeklyUsageMetrics
    ) -> WeekOverWeekComparison:
        """
        Calcula comparação semana-a-semana.

        Args:
            current_week: Métricas da semana atual
            previous_week: Métricas da semana anterior

        Returns:
            WeekOverWeekComparison com as mudanças
        """
        # Se semana anterior não tem uso, não há comparação válida
        if not previous_week.has_usage:
            return WeekOverWeekComparison(
                hours_change_percent=0.0,
                cost_change_percent=0.0,
                savings_change_percent=0.0,
                hours_trend='stable',
                cost_trend='stable',
                savings_trend='stable',
                hours_diff=current_week.total_hours,
                cost_diff=current_week.total_cost_dumont,
                savings_diff=current_week.savings_vs_aws,
                has_previous_week=False
            )

        # Calcular diferenças
        hours_diff = current_week.total_hours - previous_week.total_hours
        cost_diff = current_week.total_cost_dumont - previous_week.total_cost_dumont
        savings_diff = current_week.savings_vs_aws - previous_week.savings_vs_aws

        # Calcular porcentagens
        hours_change = self._calculate_percent_change(
            previous_week.total_hours, current_week.total_hours
        )
        cost_change = self._calculate_percent_change(
            previous_week.total_cost_dumont, current_week.total_cost_dumont
        )
        savings_change = self._calculate_percent_change(
            previous_week.savings_vs_aws, current_week.savings_vs_aws
        )

        return WeekOverWeekComparison(
            hours_change_percent=hours_change,
            cost_change_percent=cost_change,
            savings_change_percent=savings_change,
            hours_trend=self._get_trend(hours_change),
            cost_trend=self._get_trend(cost_change),
            savings_trend=self._get_trend(savings_change),
            hours_diff=hours_diff,
            cost_diff=cost_diff,
            savings_diff=savings_diff,
            has_previous_week=True
        )

    def _calculate_percent_change(self, old_value: float, new_value: float) -> float:
        """Calcula mudança percentual entre dois valores."""
        if old_value == 0:
            if new_value == 0:
                return 0.0
            return 100.0  # De 0 para qualquer valor = 100% aumento
        return ((new_value - old_value) / old_value) * 100

    def _get_trend(self, percent_change: float, threshold: float = 1.0) -> str:
        """
        Determina direção da tendência.

        Args:
            percent_change: Mudança percentual
            threshold: Limite para considerar estável

        Returns:
            'up', 'down' ou 'stable'
        """
        if percent_change > threshold:
            return 'up'
        elif percent_change < -threshold:
            return 'down'
        return 'stable'

    def get_gpu_breakdown(
        self,
        user_id: str,
        week_start: datetime,
        week_end: datetime
    ) -> List[GPUBreakdown]:
        """
        Retorna breakdown de uso por tipo de GPU.

        Args:
            user_id: ID do usuário
            week_start: Início da semana
            week_end: Fim da semana

        Returns:
            Lista de GPUBreakdown ordenada por horas (decrescente)
        """
        breakdown = self.db.query(
            UsageRecord.gpu_type,
            func.sum(UsageRecord.duration_minutes).label("minutes"),
            func.sum(UsageRecord.cost_dumont).label("cost"),
            func.sum(UsageRecord.cost_aws_equivalent).label("aws"),
            func.count(UsageRecord.id).label("sessions")
        ).filter(
            UsageRecord.user_id == user_id,
            UsageRecord.started_at >= week_start,
            UsageRecord.started_at <= week_end
        ).group_by(UsageRecord.gpu_type).all()

        result = []
        for item in breakdown:
            result.append(GPUBreakdown(
                gpu_type=item.gpu_type,
                hours=item.minutes / 60,
                cost_dumont=item.cost,
                cost_aws=item.aws,
                savings=item.aws - item.cost,
                sessions=item.sessions
            ))

        # Ordenar por horas (maior primeiro)
        result.sort(key=lambda x: x.hours, reverse=True)
        return result


def aggregate_user_usage(
    db: Session,
    user_id: str,
    reference_date: Optional[datetime] = None
) -> Dict:
    """
    Função de conveniência para agregar uso de um usuário.

    Retorna todos os dados necessários para o email semanal:
    - Métricas da semana atual
    - Métricas da semana anterior
    - Comparação week-over-week
    - Breakdown por GPU

    Args:
        db: Sessão do banco de dados
        user_id: ID do usuário
        reference_date: Data de referência (default: agora)

    Returns:
        Dict com todos os dados agregados
    """
    aggregator = EmailAnalyticsAggregator(db)

    # Obter limites das semanas
    current_week_start, current_week_end = aggregator.get_week_bounds(reference_date)
    previous_week_start = current_week_start - timedelta(days=7)
    previous_week_end = current_week_end - timedelta(days=7)

    # Calcular métricas
    current_metrics = aggregator.calculate_weekly_metrics(
        user_id, current_week_start, current_week_end
    )
    previous_metrics = aggregator.calculate_weekly_metrics(
        user_id, previous_week_start, previous_week_end
    )

    # Comparação week-over-week
    wow_comparison = aggregator.calculate_week_over_week(current_metrics, previous_metrics)

    # Breakdown por GPU
    gpu_breakdown = aggregator.get_gpu_breakdown(
        user_id, current_week_start, current_week_end
    )

    return {
        'user_id': user_id,
        'current_week': current_metrics.to_dict(),
        'previous_week': previous_metrics.to_dict(),
        'week_over_week': wow_comparison.to_dict(),
        'gpu_breakdown': [gpu.to_dict() for gpu in gpu_breakdown],
        'generated_at': datetime.utcnow().isoformat(),
    }
