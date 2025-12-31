"""
API endpoints para gerenciamento de afiliados e analytics.

Endpoints:
- GET /api/affiliate/stats - Obtém estatísticas do afiliado
- GET /api/affiliate/payouts - Obtém histórico de pagamentos
- GET /api/affiliate/dashboard - Obtém resumo completo do dashboard
- GET /api/affiliate/referrals - Obtém lista de referências
- GET /api/affiliate/daily-metrics - Obtém métricas diárias para gráficos
- GET /api/affiliate/export - Exporta dados para CSV
"""
import logging
from flask import Blueprint, request, jsonify, session, Response
from functools import wraps
from datetime import datetime

from src.config.database import SessionLocal
from src.services.affiliate_service import AffiliateService

logger = logging.getLogger(__name__)

affiliates_bp = Blueprint('affiliates', __name__)


def login_required(f):
    """Decorator para verificar autenticação."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


@affiliates_bp.route('/api/affiliate/stats', methods=['GET'])
@login_required
def get_affiliate_stats():
    """
    Obtém estatísticas do afiliado para o período especificado.

    GET /api/affiliate/stats?period=month

    Query params:
        period: Período ("day", "week", "month", "year", "all") - default: "month"

    Returns:
        {
            "success": true,
            "period": "month",
            "affiliate_id": "user@example.com",
            "referral_code": "ABC12345",
            "metrics": {
                "total_clicks": 100,
                "unique_clicks": 80,
                "total_signups": 20,
                "verified_signups": 15,
                "total_conversions": 10
            },
            "rates": {
                "click_to_signup_rate": 25.0,
                "signup_to_conversion_rate": 50.0,
                "total_conversion_rate": 12.5
            },
            "earnings": {
                "total_revenue": 500.00,
                "total_earnings": 250.00,
                "pending_earnings": 50.00,
                "paid_earnings": 200.00
            }
        }
    """
    db = SessionLocal()
    try:
        user_id = session['user']
        period = request.args.get('period', 'month')

        # Validar período
        valid_periods = ['day', 'week', 'month', 'year', 'all']
        if period not in valid_periods:
            return jsonify({
                'success': False,
                'error': f'Invalid period. Must be one of: {", ".join(valid_periods)}'
            }), 400

        service = AffiliateService(db)
        stats = service.get_affiliate_stats(user_id, period)

        return jsonify({
            'success': True,
            **stats
        })

    except Exception as e:
        logger.error(f"Erro ao obter estatísticas de afiliado: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        db.close()


@affiliates_bp.route('/api/affiliate/payouts', methods=['GET'])
@login_required
def get_affiliate_payouts():
    """
    Obtém histórico de pagamentos do afiliado.

    GET /api/affiliate/payouts?limit=50&offset=0

    Query params:
        limit: Limite de resultados (default: 50)
        offset: Offset para paginação (default: 0)

    Returns:
        {
            "success": true,
            "payouts": [
                {
                    "id": 1,
                    "type": "referral_bonus",
                    "amount": 25.00,
                    "balance_after": 75.00,
                    "description": "Referral bonus for user reaching $50 spend",
                    "created_at": "2025-01-15T10:30:00Z"
                }
            ],
            "pagination": {
                "limit": 50,
                "offset": 0,
                "has_more": false
            }
        }
    """
    db = SessionLocal()
    try:
        user_id = session['user']

        # Validar e parsear parâmetros
        try:
            limit = int(request.args.get('limit', 50))
            offset = int(request.args.get('offset', 0))
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid limit or offset parameter'
            }), 400

        # Limitar valores
        limit = max(1, min(limit, 100))
        offset = max(0, offset)

        service = AffiliateService(db)
        payouts = service.get_payout_history(user_id, limit=limit + 1, offset=offset)

        # Verificar se há mais resultados
        has_more = len(payouts) > limit
        if has_more:
            payouts = payouts[:limit]

        return jsonify({
            'success': True,
            'payouts': payouts,
            'pagination': {
                'limit': limit,
                'offset': offset,
                'has_more': has_more
            }
        })

    except Exception as e:
        logger.error(f"Erro ao obter histórico de pagamentos: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        db.close()


@affiliates_bp.route('/api/affiliate/dashboard', methods=['GET'])
@login_required
def get_affiliate_dashboard():
    """
    Obtém resumo completo do dashboard de afiliados.

    GET /api/affiliate/dashboard

    Returns:
        {
            "success": true,
            "lifetime": { ... },
            "current_month": { ... },
            "current_week": { ... },
            "daily_metrics": [ ... ],
            "recent_referrals": [ ... ],
            "recent_payouts": [ ... ]
        }
    """
    db = SessionLocal()
    try:
        user_id = session['user']

        service = AffiliateService(db)
        dashboard = service.get_dashboard_summary(user_id)

        return jsonify({
            'success': True,
            **dashboard
        })

    except Exception as e:
        logger.error(f"Erro ao obter dashboard de afiliado: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        db.close()


@affiliates_bp.route('/api/affiliate/referrals', methods=['GET'])
@login_required
def get_affiliate_referrals():
    """
    Obtém lista de referências do afiliado.

    GET /api/affiliate/referrals?status=active&limit=50&offset=0

    Query params:
        status: Filtrar por status (opcional: "pending", "active", "completed", "cancelled")
        limit: Limite de resultados (default: 50)
        offset: Offset para paginação (default: 0)

    Returns:
        {
            "success": true,
            "referrals": [
                {
                    "id": 1,
                    "status": "active",
                    "email_verified": true,
                    "spend_progress": 60.0,
                    "current_spend": 30.00,
                    "threshold": 50.00,
                    "reward_amount": 25.00,
                    "reward_granted": false,
                    "welcome_credit_granted": true,
                    "is_suspicious": false,
                    "created_at": "2025-01-10T08:00:00Z",
                    "reward_granted_at": null
                }
            ],
            "pagination": {
                "limit": 50,
                "offset": 0,
                "has_more": false
            }
        }
    """
    db = SessionLocal()
    try:
        user_id = session['user']

        # Obter parâmetros
        status = request.args.get('status')

        # Validar e parsear parâmetros
        try:
            limit = int(request.args.get('limit', 50))
            offset = int(request.args.get('offset', 0))
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid limit or offset parameter'
            }), 400

        # Limitar valores
        limit = max(1, min(limit, 100))
        offset = max(0, offset)

        # Validar status se fornecido
        valid_statuses = ['pending', 'active', 'completed', 'cancelled', 'expired', 'suspended']
        if status and status not in valid_statuses:
            return jsonify({
                'success': False,
                'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            }), 400

        service = AffiliateService(db)
        referrals = service.get_referrals_list(
            user_id,
            status=status,
            limit=limit + 1,
            offset=offset
        )

        # Verificar se há mais resultados
        has_more = len(referrals) > limit
        if has_more:
            referrals = referrals[:limit]

        return jsonify({
            'success': True,
            'referrals': referrals,
            'pagination': {
                'limit': limit,
                'offset': offset,
                'has_more': has_more
            }
        })

    except Exception as e:
        logger.error(f"Erro ao obter lista de referências: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        db.close()


@affiliates_bp.route('/api/affiliate/daily-metrics', methods=['GET'])
@login_required
def get_affiliate_daily_metrics():
    """
    Obtém métricas diárias para gráficos do dashboard.

    GET /api/affiliate/daily-metrics?days=30

    Query params:
        days: Número de dias (default: 30, max: 365)

    Returns:
        {
            "success": true,
            "days": 30,
            "metrics": [
                {
                    "date": "2025-01-15",
                    "clicks": 10,
                    "unique_clicks": 8,
                    "signups": 2,
                    "conversions": 1,
                    "revenue": 50.00,
                    "earnings": 25.00
                }
            ]
        }
    """
    db = SessionLocal()
    try:
        user_id = session['user']

        # Validar e parsear parâmetros
        try:
            days = int(request.args.get('days', 30))
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid days parameter'
            }), 400

        # Limitar valores
        days = max(1, min(days, 365))

        service = AffiliateService(db)
        metrics = service.get_daily_metrics(user_id, days=days)

        return jsonify({
            'success': True,
            'days': days,
            'metrics': metrics
        })

    except Exception as e:
        logger.error(f"Erro ao obter métricas diárias: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        db.close()


@affiliates_bp.route('/api/affiliate/export', methods=['GET'])
@login_required
def export_affiliate_data():
    """
    Exporta dados do afiliado para CSV (para relatórios fiscais).

    GET /api/affiliate/export?start_date=2025-01-01&end_date=2025-12-31

    Query params:
        start_date: Data de início no formato YYYY-MM-DD (default: 1 ano atrás)
        end_date: Data de fim no formato YYYY-MM-DD (default: hoje)

    Returns:
        CSV file download
    """
    db = SessionLocal()
    try:
        user_id = session['user']

        # Parsear datas
        start_date = None
        end_date = None

        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid start_date format. Use YYYY-MM-DD'
                }), 400

        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid end_date format. Use YYYY-MM-DD'
                }), 400

        service = AffiliateService(db)
        csv_content = service.export_to_csv(
            user_id,
            start_date=start_date,
            end_date=end_date
        )

        # Gerar nome do arquivo
        filename = f"affiliate_report_{user_id}_{datetime.utcnow().strftime('%Y%m%d')}.csv"

        return Response(
            csv_content,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )

    except Exception as e:
        logger.error(f"Erro ao exportar dados do afiliado: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        db.close()


@affiliates_bp.route('/api/affiliate/lifetime', methods=['GET'])
@login_required
def get_affiliate_lifetime_stats():
    """
    Obtém estatísticas de lifetime do afiliado.

    GET /api/affiliate/lifetime

    Returns:
        {
            "success": true,
            "has_code": true,
            "code": "ABC12345",
            "total_clicks": 500,
            "total_signups": 100,
            "total_conversions": 50,
            "total_earnings": 1250.00,
            "conversion_rate": 10.0,
            "member_since": "2024-06-15T10:00:00Z"
        }
    """
    db = SessionLocal()
    try:
        user_id = session['user']

        service = AffiliateService(db)
        stats = service.get_lifetime_stats(user_id)

        return jsonify({
            'success': True,
            **stats
        })

    except Exception as e:
        logger.error(f"Erro ao obter estatísticas de lifetime: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        db.close()
