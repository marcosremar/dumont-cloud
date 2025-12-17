"""
API de relatórios de preços de GPUs.

Fornece endpoints para análise de histórico de preços,
tendências e alertas.
"""

from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from typing import Dict, List

from src.config.database import SessionLocal
from src.models.price_history import PriceHistory, PriceAlert
from src.services.agent_manager import agent_manager

price_reports_bp = Blueprint('price_reports', __name__)


@price_reports_bp.route('/api/price-monitor/status', methods=['GET'])
def get_monitor_status():
    """Retorna status do agente de monitoramento."""
    try:
        status = agent_manager.get_status()

        # Encontrar agente de monitoramento de preços
        monitor_agent = None
        for agent_status in status:
            if 'PriceMonitor' in agent_status['class']:
                monitor_agent = agent_status
                break

        if monitor_agent:
            # Obter estatísticas do agente se estiver rodando
            agent = agent_manager.agents.get(monitor_agent['name'])
            if agent and hasattr(agent, 'get_stats'):
                detailed_stats = agent.get_stats()
                monitor_agent.update(detailed_stats)

        return jsonify({
            'success': True,
            'agent': monitor_agent,
            'all_agents': status
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@price_reports_bp.route('/api/price-monitor/history', methods=['GET'])
def get_price_history():
    """
    Retorna histórico de preços.

    Query params:
        gpu_name: Nome da GPU (opcional, se não fornecido retorna todas)
        hours: Horas de histórico (padrão: 24)
        limit: Limite de registros (padrão: 100)
    """
    gpu_name = request.args.get('gpu_name')
    hours = int(request.args.get('hours', 24))
    limit = int(request.args.get('limit', 100))

    db = SessionLocal()
    try:
        # Calcular timestamp de início
        start_time = datetime.utcnow() - timedelta(hours=hours)

        # Query base
        query = db.query(PriceHistory).filter(PriceHistory.timestamp >= start_time)

        # Filtrar por GPU se especificado
        if gpu_name:
            query = query.filter(PriceHistory.gpu_name == gpu_name)

        # Ordenar por timestamp (mais recente primeiro) e limitar
        records = query.order_by(desc(PriceHistory.timestamp)).limit(limit).all()

        # Converter para dicionário
        history = []
        for record in records:
            history.append({
                'id': record.id,
                'gpu_name': record.gpu_name,
                'timestamp': record.timestamp.isoformat(),
                'min_price': record.min_price,
                'max_price': record.max_price,
                'avg_price': record.avg_price,
                'median_price': record.median_price,
                'total_offers': record.total_offers,
                'available_gpus': record.available_gpus,
            })

        return jsonify({
            'success': True,
            'count': len(history),
            'history': history
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@price_reports_bp.route('/api/price-monitor/summary', methods=['GET'])
def get_price_summary():
    """
    Retorna resumo de preços atuais e tendências.

    Query params:
        gpu_name: Nome da GPU (opcional)
    """
    gpu_name = request.args.get('gpu_name')

    db = SessionLocal()
    try:
        # Query base - últimas 24 horas
        start_time = datetime.utcnow() - timedelta(hours=24)
        query = db.query(PriceHistory).filter(PriceHistory.timestamp >= start_time)

        if gpu_name:
            query = query.filter(PriceHistory.gpu_name == gpu_name)

        # Agrupar por GPU
        gpus = db.query(PriceHistory.gpu_name).distinct().all()
        gpu_names = [gpu[0] for gpu in gpus]

        summary = []
        for gpu in gpu_names:
            # Filtrar dados da GPU específica
            gpu_query = query.filter(PriceHistory.gpu_name == gpu)

            # Pegar último registro (mais recente)
            latest = gpu_query.order_by(desc(PriceHistory.timestamp)).first()

            if not latest:
                continue

            # Pegar registro de 24h atrás para calcular tendência
            old_record = gpu_query.order_by(PriceHistory.timestamp).first()

            # Calcular tendência
            trend = None
            trend_percent = None
            if old_record and old_record.avg_price > 0:
                price_change = latest.avg_price - old_record.avg_price
                trend_percent = (price_change / old_record.avg_price) * 100

                if abs(trend_percent) < 1:
                    trend = 'stable'
                elif trend_percent > 0:
                    trend = 'up'
                else:
                    trend = 'down'

            # Estatísticas do período
            stats = db.query(
                func.min(PriceHistory.avg_price).label('lowest_avg'),
                func.max(PriceHistory.avg_price).label('highest_avg'),
                func.avg(PriceHistory.avg_price).label('period_avg'),
                func.sum(PriceHistory.total_offers).label('total_offers_sum')
            ).filter(
                PriceHistory.gpu_name == gpu,
                PriceHistory.timestamp >= start_time
            ).first()

            summary.append({
                'gpu_name': gpu,
                'current': {
                    'min_price': latest.min_price,
                    'avg_price': latest.avg_price,
                    'max_price': latest.max_price,
                    'median_price': latest.median_price,
                    'total_offers': latest.total_offers,
                    'available_gpus': latest.available_gpus,
                    'timestamp': latest.timestamp.isoformat(),
                },
                'trend_24h': {
                    'direction': trend,
                    'change_percent': round(trend_percent, 2) if trend_percent else None,
                    'lowest_avg': float(stats.lowest_avg) if stats.lowest_avg else None,
                    'highest_avg': float(stats.highest_avg) if stats.highest_avg else None,
                    'period_avg': float(stats.period_avg) if stats.period_avg else None,
                }
            })

        return jsonify({
            'success': True,
            'summary': summary
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@price_reports_bp.route('/api/price-monitor/alerts', methods=['GET'])
def get_price_alerts():
    """
    Retorna alertas de preço.

    Query params:
        gpu_name: Nome da GPU (opcional)
        hours: Horas de histórico (padrão: 24)
        limit: Limite de registros (padrão: 50)
    """
    gpu_name = request.args.get('gpu_name')
    hours = int(request.args.get('hours', 24))
    limit = int(request.args.get('limit', 50))

    db = SessionLocal()
    try:
        # Calcular timestamp de início
        start_time = datetime.utcnow() - timedelta(hours=hours)

        # Query base
        query = db.query(PriceAlert).filter(PriceAlert.timestamp >= start_time)

        # Filtrar por GPU se especificado
        if gpu_name:
            query = query.filter(PriceAlert.gpu_name == gpu_name)

        # Ordenar por timestamp (mais recente primeiro) e limitar
        alerts = query.order_by(desc(PriceAlert.timestamp)).limit(limit).all()

        # Converter para dicionário
        alert_list = []
        for alert in alerts:
            alert_list.append({
                'id': alert.id,
                'gpu_name': alert.gpu_name,
                'timestamp': alert.timestamp.isoformat(),
                'alert_type': alert.alert_type,
                'previous_value': alert.previous_value,
                'current_value': alert.current_value,
                'change_percent': alert.change_percent,
                'message': alert.message,
            })

        return jsonify({
            'success': True,
            'count': len(alert_list),
            'alerts': alert_list
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@price_reports_bp.route('/api/price-monitor/best-times', methods=['GET'])
def get_best_times():
    """
    Analisa quando os preços costumam ser mais baixos.

    Query params:
        gpu_name: Nome da GPU (obrigatório)
        days: Dias de histórico para análise (padrão: 7)
    """
    gpu_name = request.args.get('gpu_name')
    if not gpu_name:
        return jsonify({'success': False, 'error': 'gpu_name é obrigatório'}), 400

    days = int(request.args.get('days', 7))

    db = SessionLocal()
    try:
        # Calcular timestamp de início
        start_time = datetime.utcnow() - timedelta(days=days)

        # Buscar histórico
        records = db.query(PriceHistory).filter(
            PriceHistory.gpu_name == gpu_name,
            PriceHistory.timestamp >= start_time
        ).all()

        if not records:
            return jsonify({
                'success': False,
                'error': f'Sem dados históricos para {gpu_name}'
            }), 404

        # Agrupar por hora do dia
        hourly_prices = {}
        for record in records:
            hour = record.timestamp.hour
            if hour not in hourly_prices:
                hourly_prices[hour] = []
            hourly_prices[hour].append(record.avg_price)

        # Calcular média por hora
        hourly_avg = {}
        for hour, prices in hourly_prices.items():
            hourly_avg[hour] = sum(prices) / len(prices)

        # Encontrar melhores horários (preços mais baixos)
        sorted_hours = sorted(hourly_avg.items(), key=lambda x: x[1])
        best_hours = sorted_hours[:5]  # Top 5 horários mais baratos

        # Agrupar por dia da semana
        daily_prices = {}
        for record in records:
            day = record.timestamp.weekday()  # 0 = Monday, 6 = Sunday
            if day not in daily_prices:
                daily_prices[day] = []
            daily_prices[day].append(record.avg_price)

        # Calcular média por dia
        daily_avg = {}
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for day, prices in daily_prices.items():
            daily_avg[day_names[day]] = sum(prices) / len(prices)

        # Encontrar melhores dias
        sorted_days = sorted(daily_avg.items(), key=lambda x: x[1])
        best_days = sorted_days[:3]  # Top 3 dias mais baratos

        return jsonify({
            'success': True,
            'gpu_name': gpu_name,
            'analysis_period_days': days,
            'best_hours': [
                {
                    'hour': hour,
                    'avg_price': round(price, 4),
                    'time_range': f"{hour:02d}:00-{hour:02d}:59"
                }
                for hour, price in best_hours
            ],
            'best_days': [
                {
                    'day': day,
                    'avg_price': round(price, 4)
                }
                for day, price in best_days
            ],
            'hourly_average': {
                f"{hour:02d}:00": round(price, 4)
                for hour, price in sorted(hourly_avg.items())
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@price_reports_bp.route('/api/price-monitor/compare', methods=['GET'])
def compare_gpus():
    """
    Compara preços entre diferentes GPUs.

    Query params:
        gpus: Lista de GPUs separadas por vírgula (ex: "RTX 4090,RTX 4050")
    """
    gpus_param = request.args.get('gpus')
    if not gpus_param:
        return jsonify({'success': False, 'error': 'parâmetro gpus é obrigatório'}), 400

    gpu_list = [gpu.strip() for gpu in gpus_param.split(',')]

    db = SessionLocal()
    try:
        comparison = []

        for gpu_name in gpu_list:
            # Pegar último registro
            latest = db.query(PriceHistory).filter(
                PriceHistory.gpu_name == gpu_name
            ).order_by(desc(PriceHistory.timestamp)).first()

            if latest:
                comparison.append({
                    'gpu_name': gpu_name,
                    'avg_price': latest.avg_price,
                    'min_price': latest.min_price,
                    'max_price': latest.max_price,
                    'total_offers': latest.total_offers,
                    'available_gpus': latest.available_gpus,
                    'last_update': latest.timestamp.isoformat(),
                })
            else:
                comparison.append({
                    'gpu_name': gpu_name,
                    'error': 'Sem dados disponíveis'
                })

        # Ordenar por preço médio (mais barato primeiro)
        comparison_sorted = sorted(
            [c for c in comparison if 'avg_price' in c],
            key=lambda x: x['avg_price']
        )

        return jsonify({
            'success': True,
            'comparison': comparison_sorted,
            'cheapest': comparison_sorted[0] if comparison_sorted else None,
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()
