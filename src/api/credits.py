"""
API endpoints para gerenciamento de saldo e historico de creditos.

Endpoints:
- GET /api/credits/balance - Obtem saldo atual de creditos do usuario
- GET /api/credits/history - Obtem historico de transacoes de creditos
- GET /api/credits/summary - Obtem resumo completo de creditos
"""
import logging
from flask import Blueprint, request, jsonify, session
from functools import wraps

from src.config.database import SessionLocal
from src.services.credit_service import CreditService

logger = logging.getLogger(__name__)

credits_bp = Blueprint('credits', __name__)


def login_required(f):
    """Decorator para verificar autenticacao."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


@credits_bp.route('/api/credits/balance', methods=['GET'])
@login_required
def get_credit_balance():
    """
    Obtem saldo atual de creditos do usuario autenticado.

    GET /api/credits/balance

    Returns:
        {
            "success": true,
            "balance": 35.00,
            "currency": "USD"
        }
    """
    db = SessionLocal()
    try:
        user_id = session['user']

        service = CreditService(db)
        balance = service.get_balance(user_id)

        return jsonify({
            'success': True,
            'balance': round(balance, 2),
            'currency': 'USD'
        })

    except Exception as e:
        logger.error(f"Erro ao obter saldo de creditos para usuario {session.get('user')}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        db.close()


@credits_bp.route('/api/credits/history', methods=['GET'])
@login_required
def get_credit_history():
    """
    Obtem historico de transacoes de creditos do usuario autenticado.

    GET /api/credits/history?limit=50&offset=0&type=referral_bonus

    Query params:
        - limit: Numero maximo de transacoes (default 50, max 100)
        - offset: Offset para paginacao (default 0)
        - type: Filtrar por tipo de transacao (opcional)
            - referral_bonus: $25 para quem indicou
            - welcome_credit: $10 para novo usuario
            - affiliate_payout: Pagamento de afiliado
            - credit_retraction: Retracao por fraude/reembolso
            - manual_adjustment: Ajuste manual por admin

    Returns:
        {
            "success": true,
            "transactions": [
                {
                    "id": 1,
                    "transaction_type": "welcome_credit",
                    "amount": 10.00,
                    "balance_before": 0.00,
                    "balance_after": 10.00,
                    "description": "Welcome credit for signing up with referral code",
                    "created_at": "2025-01-15T10:30:00Z"
                }
            ],
            "total": 15,
            "limit": 50,
            "offset": 0,
            "has_more": false
        }
    """
    db = SessionLocal()
    try:
        user_id = session['user']

        # Parse query params
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        transaction_type = request.args.get('type', None)

        # Validar limites
        if limit < 1:
            limit = 1
        elif limit > 100:
            limit = 100

        if offset < 0:
            offset = 0

        service = CreditService(db)

        # Obter transacoes
        transactions = service.get_transaction_history(
            user_id=user_id,
            limit=limit,
            offset=offset,
            transaction_type=transaction_type
        )

        # Obter contagem total para paginacao
        total = service.get_transaction_count(
            user_id=user_id,
            transaction_type=transaction_type
        )

        return jsonify({
            'success': True,
            'transactions': [tx.to_dict() for tx in transactions],
            'total': total,
            'limit': limit,
            'offset': offset,
            'has_more': offset + len(transactions) < total
        })

    except Exception as e:
        logger.error(f"Erro ao obter historico de creditos para usuario {session.get('user')}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        db.close()


@credits_bp.route('/api/credits/summary', methods=['GET'])
@login_required
def get_credit_summary():
    """
    Obtem resumo completo de creditos do usuario autenticado.

    GET /api/credits/summary

    Returns:
        {
            "success": true,
            "balance": 35.00,
            "total_credits": 45.00,
            "total_debits": 10.00,
            "transaction_count": 5,
            "breakdown": {
                "referral_bonus": {"count": 2, "total": 50.00},
                "welcome_credit": {"count": 1, "total": 10.00},
                "affiliate_payout": {"count": 1, "total": -25.00}
            }
        }
    """
    db = SessionLocal()
    try:
        user_id = session['user']

        service = CreditService(db)
        summary = service.get_user_credit_summary(user_id)

        return jsonify({
            'success': True,
            **summary
        })

    except Exception as e:
        logger.error(f"Erro ao obter resumo de creditos para usuario {session.get('user')}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        db.close()
