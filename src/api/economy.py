"""
API endpoints para economia e economia de custos.
Compara custos do Dumont Cloud com AWS, GCP e Azure.
"""
from flask import Blueprint, request, jsonify, g
from functools import wraps
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

economy_bp = Blueprint('economy', __name__, url_prefix='/api/v1/economy')


# Precos base por hora de GPUs nos provedores de nuvem (USD)
# Estes valores sao aproximacoes baseadas em precos publicos
PROVIDER_GPU_PRICING = {
    'AWS': {
        'RTX 4090': 4.10,      # p5.xlarge equivalent
        'RTX 4080': 3.50,
        'RTX 3090': 3.06,      # p4d.xlarge equivalent
        'RTX 3080': 2.50,
        'A100': 32.77,         # p4d.24xlarge
        'A10': 5.67,           # g5.xlarge
        'V100': 3.06,          # p3.2xlarge
        'T4': 0.526,           # g4dn.xlarge
        'default': 3.00,
    },
    'GCP': {
        'RTX 4090': 3.80,
        'RTX 4080': 3.20,
        'RTX 3090': 2.80,
        'RTX 3080': 2.30,
        'A100': 29.39,         # a2-highgpu-1g
        'A10': 5.00,
        'V100': 2.48,
        'T4': 0.35,
        'default': 2.75,
    },
    'Azure': {
        'RTX 4090': 4.50,
        'RTX 4080': 3.80,
        'RTX 3090': 3.30,
        'RTX 3080': 2.70,
        'A100': 32.77,         # NC A100 v4
        'A10': 5.80,
        'V100': 3.06,
        'T4': 0.526,
        'default': 3.25,
    }
}


def get_provider_price(provider: str, gpu_type: str) -> float:
    """
    Retorna o preco por hora de uma GPU em um provedor especifico.

    Args:
        provider: Nome do provedor (AWS, GCP, Azure)
        gpu_type: Tipo da GPU (RTX 4090, A100, etc)

    Returns:
        Preco por hora em USD
    """
    provider_prices = PROVIDER_GPU_PRICING.get(provider, PROVIDER_GPU_PRICING['AWS'])

    # Tentar encontrar a GPU exata ou usar default
    for gpu_key in provider_prices:
        if gpu_key.lower() in gpu_type.lower() or gpu_type.lower() in gpu_key.lower():
            return provider_prices[gpu_key]

    return provider_prices.get('default', 3.00)


def calculate_savings(
    dumont_cost: float,
    hours_used: float,
    gpu_type: str,
    provider: str = 'AWS'
) -> Dict[str, Any]:
    """
    Calcula a economia comparando custo Dumont Cloud com um provedor.

    Args:
        dumont_cost: Custo total no Dumont Cloud (USD)
        hours_used: Total de horas utilizadas
        gpu_type: Tipo da GPU utilizada
        provider: Provedor para comparacao (AWS, GCP, Azure)

    Returns:
        Dict com detalhes da economia
    """
    provider_hourly = get_provider_price(provider, gpu_type)
    provider_cost = provider_hourly * hours_used

    savings = provider_cost - dumont_cost
    savings_percentage = (savings / provider_cost * 100) if provider_cost > 0 else 0

    return {
        'dumont_cost': round(dumont_cost, 2),
        'provider_cost': round(provider_cost, 2),
        'savings': round(savings, 2),
        'savings_percentage': round(savings_percentage, 1),
        'hours_used': round(hours_used, 2),
        'provider': provider,
        'gpu_type': gpu_type,
        'provider_hourly_rate': provider_hourly,
    }


@economy_bp.route('/savings', methods=['GET'])
def get_savings_summary():
    """
    Retorna resumo de economia do usuario.

    GET /api/v1/economy/savings?provider=AWS

    Query params:
        provider: AWS, GCP ou Azure (default: AWS)

    Returns:
        {
            "success": true,
            "lifetime_savings": 1234.56,
            "current_session_savings": 12.34,
            "hourly_comparison": {
                "dumont_rate": 0.50,
                "provider_rate": 3.06,
                "savings_per_hour": 2.56
            },
            "projections": {
                "monthly": 1920.00,
                "yearly": 23040.00
            },
            "provider": "AWS",
            "instances_summary": {...}
        }
    """
    try:
        provider = request.args.get('provider', 'AWS').upper()

        if provider not in PROVIDER_GPU_PRICING:
            return jsonify({
                'success': False,
                'error': f'Provedor invalido: {provider}. Use AWS, GCP ou Azure.'
            }), 400

        # Buscar dados de instancias ativas e historico
        # Por enquanto, retornar dados de exemplo que serao populados
        # quando integrarmos com o banco de dados de billing

        # TODO: Integrar com banco de dados real de billing
        # Por enquanto, calcular com base em instancias ativas

        from src.config.database import SessionLocal
        from src.models.instance_status import InstanceStatus, HibernationEvent

        db = SessionLocal()
        try:
            # Buscar instancias ativas
            active_instances = db.query(InstanceStatus).filter(
                InstanceStatus.status.in_(['running', 'idle'])
            ).all()

            total_lifetime_hours = 0.0
            total_lifetime_cost = 0.0
            current_session_hours = 0.0
            current_session_cost = 0.0
            current_hourly_rate = 0.0
            instances_data = []

            now = datetime.utcnow()

            for instance in active_instances:
                gpu_type = instance.gpu_type or 'RTX 3090'
                # Buscar taxa horaria do ultimo evento de hibernacao ou usar padrao
                last_event = db.query(HibernationEvent).filter(
                    HibernationEvent.instance_id == instance.instance_id,
                    HibernationEvent.dph_total.isnot(None)
                ).order_by(HibernationEvent.timestamp.desc()).first()
                hourly_rate = last_event.dph_total if last_event and last_event.dph_total else 0.50
                created_at = instance.created_at

                # Calcular horas desde criacao
                if created_at:
                    hours = (now - created_at).total_seconds() / 3600
                else:
                    hours = 0

                cost = hours * hourly_rate

                total_lifetime_hours += hours
                total_lifetime_cost += cost
                current_session_hours += hours
                current_session_cost += cost
                current_hourly_rate += hourly_rate

                instances_data.append({
                    'instance_id': instance.instance_id,
                    'gpu_type': gpu_type,
                    'hours_used': round(hours, 2),
                    'dumont_cost': round(cost, 2),
                    'status': instance.status,
                })

            # Calcular economia
            provider_hourly = get_provider_price(provider, 'RTX 3090')  # Media
            lifetime_savings_calc = calculate_savings(
                total_lifetime_cost,
                total_lifetime_hours,
                'RTX 3090',
                provider
            )

            current_savings_calc = calculate_savings(
                current_session_cost,
                current_session_hours,
                'RTX 3090',
                provider
            )

            # Calcular projecoes baseadas em uso atual
            avg_daily_hours = current_session_hours if current_session_hours > 0 else 8
            monthly_hours = avg_daily_hours * 30
            yearly_hours = avg_daily_hours * 365

            monthly_savings = (provider_hourly - current_hourly_rate) * monthly_hours if current_hourly_rate > 0 else monthly_hours * provider_hourly * 0.8
            yearly_savings = (provider_hourly - current_hourly_rate) * yearly_hours if current_hourly_rate > 0 else yearly_hours * provider_hourly * 0.8

            return jsonify({
                'success': True,
                'lifetime_savings': lifetime_savings_calc['savings'],
                'lifetime_hours': round(total_lifetime_hours, 2),
                'lifetime_cost': round(total_lifetime_cost, 2),
                'current_session_savings': current_savings_calc['savings'],
                'current_session_hours': round(current_session_hours, 2),
                'current_session_cost': round(current_session_cost, 2),
                'hourly_comparison': {
                    'dumont_rate': round(current_hourly_rate, 2) if current_hourly_rate > 0 else 0.50,
                    'provider_rate': provider_hourly,
                    'savings_per_hour': round(provider_hourly - (current_hourly_rate if current_hourly_rate > 0 else 0.50), 2),
                },
                'projections': {
                    'monthly': round(max(0, monthly_savings), 2),
                    'yearly': round(max(0, yearly_savings), 2),
                },
                'provider': provider,
                'active_instances_count': len(active_instances),
                'instances_summary': instances_data[:5],  # Limitar a 5 para resumo
            })

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Erro ao calcular economia: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@economy_bp.route('/savings/history', methods=['GET'])
def get_savings_history():
    """
    Retorna historico de economia por periodo.

    GET /api/v1/economy/savings/history?provider=AWS&days=30

    Query params:
        provider: AWS, GCP ou Azure (default: AWS)
        days: Numero de dias para buscar (default: 30)

    Returns:
        {
            "success": true,
            "history": [
                {
                    "date": "2024-01-15",
                    "hours_used": 8.5,
                    "dumont_cost": 4.25,
                    "provider_cost": 26.01,
                    "savings": 21.76
                },
                ...
            ],
            "totals": {
                "total_hours": 255.0,
                "total_dumont_cost": 127.50,
                "total_provider_cost": 780.30,
                "total_savings": 652.80
            }
        }
    """
    try:
        provider = request.args.get('provider', 'AWS').upper()
        days = request.args.get('days', 30, type=int)

        if provider not in PROVIDER_GPU_PRICING:
            return jsonify({
                'success': False,
                'error': f'Provedor invalido: {provider}. Use AWS, GCP ou Azure.'
            }), 400

        if days < 1 or days > 365:
            return jsonify({
                'success': False,
                'error': 'days deve estar entre 1 e 365'
            }), 400

        # TODO: Implementar busca de historico real do banco de dados
        # Por enquanto, retornar estrutura vazia que sera populada

        from src.config.database import SessionLocal
        from src.models.instance_status import HibernationEvent

        db = SessionLocal()
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            # Buscar eventos de hibernacao como proxy para uso
            events = db.query(HibernationEvent).filter(
                HibernationEvent.timestamp >= start_date,
                HibernationEvent.timestamp <= end_date
            ).order_by(HibernationEvent.timestamp.desc()).all()

            # Agrupar por dia
            daily_data = {}
            for event in events:
                date_key = event.timestamp.strftime('%Y-%m-%d')
                if date_key not in daily_data:
                    daily_data[date_key] = {
                        'date': date_key,
                        'hours_used': 0,
                        'dumont_cost': 0,
                        'events_count': 0,
                    }
                daily_data[date_key]['events_count'] += 1
                # Estimar 0.5 hora por evento como aproximacao
                daily_data[date_key]['hours_used'] += 0.5

            history = []
            total_hours = 0
            total_dumont_cost = 0
            total_provider_cost = 0
            total_savings = 0

            provider_hourly = get_provider_price(provider, 'RTX 3090')
            dumont_hourly = 0.50  # Taxa media Dumont

            for date_key in sorted(daily_data.keys(), reverse=True):
                data = daily_data[date_key]
                hours = data['hours_used']
                dumont_cost = hours * dumont_hourly
                provider_cost = hours * provider_hourly
                savings = provider_cost - dumont_cost

                history.append({
                    'date': date_key,
                    'hours_used': round(hours, 2),
                    'dumont_cost': round(dumont_cost, 2),
                    'provider_cost': round(provider_cost, 2),
                    'savings': round(savings, 2),
                })

                total_hours += hours
                total_dumont_cost += dumont_cost
                total_provider_cost += provider_cost
                total_savings += savings

            return jsonify({
                'success': True,
                'provider': provider,
                'period_days': days,
                'history': history,
                'totals': {
                    'total_hours': round(total_hours, 2),
                    'total_dumont_cost': round(total_dumont_cost, 2),
                    'total_provider_cost': round(total_provider_cost, 2),
                    'total_savings': round(total_savings, 2),
                }
            })

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Erro ao buscar historico de economia: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@economy_bp.route('/savings/realtime', methods=['GET'])
def get_realtime_savings():
    """
    Retorna metricas de economia em tempo real para instancias ativas.

    GET /api/v1/economy/savings/realtime?provider=AWS

    Query params:
        provider: AWS, GCP ou Azure (default: AWS)

    Returns:
        {
            "success": true,
            "timestamp": "2024-01-15T10:30:00Z",
            "active_instances": [
                {
                    "instance_id": "abc123",
                    "gpu_type": "RTX 3090",
                    "running_hours": 2.5,
                    "current_cost": 1.25,
                    "provider_equivalent": 7.65,
                    "savings_so_far": 6.40,
                    "savings_per_hour": 2.56
                }
            ],
            "totals": {
                "total_running_hours": 2.5,
                "total_current_cost": 1.25,
                "total_savings": 6.40,
                "savings_rate_per_hour": 2.56
            }
        }
    """
    try:
        provider = request.args.get('provider', 'AWS').upper()

        if provider not in PROVIDER_GPU_PRICING:
            return jsonify({
                'success': False,
                'error': f'Provedor invalido: {provider}. Use AWS, GCP ou Azure.'
            }), 400

        from src.config.database import SessionLocal
        from src.models.instance_status import InstanceStatus, HibernationEvent

        db = SessionLocal()
        try:
            # Buscar instancias rodando
            running_instances = db.query(InstanceStatus).filter(
                InstanceStatus.status == 'running'
            ).all()

            now = datetime.utcnow()
            instances_data = []

            total_running_hours = 0
            total_current_cost = 0
            total_savings = 0
            total_savings_rate = 0

            for instance in running_instances:
                gpu_type = instance.gpu_type or 'RTX 3090'
                # Buscar taxa horaria do ultimo evento de hibernacao ou usar padrao
                last_event = db.query(HibernationEvent).filter(
                    HibernationEvent.instance_id == instance.instance_id,
                    HibernationEvent.dph_total.isnot(None)
                ).order_by(HibernationEvent.timestamp.desc()).first()
                hourly_rate = last_event.dph_total if last_event and last_event.dph_total else 0.50
                created_at = instance.created_at

                # Calcular horas desde que comecou a rodar
                if created_at:
                    running_hours = (now - created_at).total_seconds() / 3600
                else:
                    running_hours = 0

                current_cost = running_hours * hourly_rate
                provider_hourly = get_provider_price(provider, gpu_type)
                provider_equivalent = running_hours * provider_hourly
                savings = provider_equivalent - current_cost
                savings_per_hour = provider_hourly - hourly_rate

                instances_data.append({
                    'instance_id': instance.instance_id,
                    'gpu_type': gpu_type,
                    'status': instance.status,
                    'running_hours': round(running_hours, 2),
                    'dumont_hourly_rate': hourly_rate,
                    'current_cost': round(current_cost, 2),
                    'provider_hourly_rate': provider_hourly,
                    'provider_equivalent': round(provider_equivalent, 2),
                    'savings_so_far': round(savings, 2),
                    'savings_per_hour': round(savings_per_hour, 2),
                })

                total_running_hours += running_hours
                total_current_cost += current_cost
                total_savings += savings
                total_savings_rate += savings_per_hour

            avg_savings_rate = total_savings_rate / len(running_instances) if running_instances else 0

            return jsonify({
                'success': True,
                'timestamp': now.isoformat() + 'Z',
                'provider': provider,
                'active_instances': instances_data,
                'totals': {
                    'instances_count': len(running_instances),
                    'total_running_hours': round(total_running_hours, 2),
                    'total_current_cost': round(total_current_cost, 2),
                    'total_savings': round(total_savings, 2),
                    'avg_savings_rate_per_hour': round(avg_savings_rate, 2),
                }
            })

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Erro ao buscar metricas em tempo real: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@economy_bp.route('/pricing', methods=['GET'])
def get_provider_pricing():
    """
    Retorna tabela de precos de referencia dos provedores.

    GET /api/v1/economy/pricing?provider=AWS

    Query params:
        provider: AWS, GCP, Azure ou 'all' (default: all)

    Returns:
        {
            "success": true,
            "pricing": {
                "AWS": {"RTX 4090": 4.10, ...},
                "GCP": {"RTX 4090": 3.80, ...},
                "Azure": {"RTX 4090": 4.50, ...}
            }
        }
    """
    try:
        provider = request.args.get('provider', 'all').upper()

        if provider == 'ALL':
            pricing = PROVIDER_GPU_PRICING
        elif provider in PROVIDER_GPU_PRICING:
            pricing = {provider: PROVIDER_GPU_PRICING[provider]}
        else:
            return jsonify({
                'success': False,
                'error': f'Provedor invalido: {provider}. Use AWS, GCP, Azure ou all.'
            }), 400

        return jsonify({
            'success': True,
            'pricing': pricing,
            'currency': 'USD',
            'unit': 'per_hour',
            'last_updated': datetime.utcnow().strftime('%Y-%m-%d'),
        })

    except Exception as e:
        logger.error(f"Erro ao buscar precos: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
