"""
API endpoints para gerenciamento de referências e códigos de referência.

Endpoints:
- GET /api/referral/code - Obtém ou cria código de referência do usuário
- POST /api/referral/apply - Aplica código de referência durante cadastro
- GET /api/referral/validate/<code> - Valida um código de referência
- GET /api/referral/stats - Obtém estatísticas de referência do usuário
- POST /api/referral/click/<code> - Registra clique em código de referência
- GET /api/referral/my-referrer - Verifica se usuário tem referrer e status de email
- GET /api/referral/credits - Obtém saldo e status de créditos do usuário
"""
import logging
from flask import Blueprint, request, jsonify, session, g
from functools import wraps

from src.config.database import SessionLocal
from src.services.referral_service import ReferralService
from src.services.credit_service import CreditService, EmailNotVerifiedError

logger = logging.getLogger(__name__)

referrals_bp = Blueprint('referrals', __name__)


def login_required(f):
    """Decorator para verificar autenticação."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


@referrals_bp.route('/api/referral/code', methods=['GET'])
@login_required
def get_referral_code():
    """
    Obtém ou cria código de referência do usuário autenticado.

    GET /api/referral/code

    Returns:
        {
            "success": true,
            "referral_code": "ABC12345",
            "share_url": "https://dumontcloud.com/signup?ref=ABC12345",
            "stats": {
                "total_referrals": 5,
                "pending_referrals": 2,
                "completed_referrals": 3,
                "total_earnings": 75.00,
                "pending_earnings": 50.00
            }
        }
    """
    db = SessionLocal()
    try:
        user_id = session['user']

        service = ReferralService(db)
        referral_code = service.get_or_create_code(user_id)
        stats = service.get_referrer_stats(user_id)

        return jsonify({
            'success': True,
            'referral_code': referral_code.code,
            'share_url': f"https://dumontcloud.com/signup?ref={referral_code.code}",
            'is_active': referral_code.is_active,
            'created_at': referral_code.created_at.isoformat() if referral_code.created_at else None,
            'stats': {
                'total_referrals': stats['total_referrals'],
                'pending_referrals': stats['pending_referrals'],
                'completed_referrals': stats['completed_referrals'],
                'total_earnings': stats['total_earnings'],
                'pending_earnings': stats['pending_earnings'],
                'conversion_rate': stats.get('conversion_rate', 0.0)
            }
        })

    except Exception as e:
        logger.error(f"Erro ao obter código de referência para usuário {session.get('user')}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        db.close()


@referrals_bp.route('/api/referral/apply', methods=['POST'])
@login_required
def apply_referral_code():
    """
    Aplica um código de referência para o usuário autenticado.

    POST /api/referral/apply
    Body: {
        "code": "ABC12345"
    }

    Returns:
        {
            "success": true,
            "message": "Referral code applied successfully",
            "welcome_credit": 10.00
        }

    Errors:
        400: Invalid code, self-referral, already has referrer
        401: Not authenticated
    """
    db = SessionLocal()
    try:
        user_id = session['user']
        data = request.json or {}

        code = data.get('code', '').strip()
        if not code:
            return jsonify({
                'success': False,
                'error': 'Referral code is required'
            }), 400

        # Obter IP do cliente para anti-fraude
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip:
            # Pegar primeiro IP se houver múltiplos (proxy chain)
            client_ip = client_ip.split(',')[0].strip()

        service = ReferralService(db)
        result = service.apply_code(
            referred_user_id=user_id,
            code=code,
            referred_ip=client_ip
        )

        if not result['success']:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400

        return jsonify({
            'success': True,
            'message': 'Referral code applied successfully. Welcome credit will be activated after email verification.',
            'welcome_credit': result['welcome_credit'],
            'credit_pending_verification': True
        })

    except Exception as e:
        logger.error(f"Erro ao aplicar código de referência: {e}", exc_info=True)
        db.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        db.close()


@referrals_bp.route('/api/referral/validate/<code>', methods=['GET'])
def validate_referral_code(code: str):
    """
    Valida um código de referência (endpoint público para uso no signup).

    GET /api/referral/validate/<code>

    Returns:
        {
            "valid": true,
            "message": "Valid referral code"
        }

    Note: Não expõe informações do referrer por privacidade.
    """
    db = SessionLocal()
    try:
        if not code:
            return jsonify({
                'valid': False,
                'error': 'Referral code is required'
            }), 400

        service = ReferralService(db)
        referral_code = service.get_code_by_code(code.upper())

        if not referral_code:
            return jsonify({
                'valid': False,
                'error': 'Invalid referral code'
            })

        if not referral_code.is_usable:
            if not referral_code.is_active:
                return jsonify({
                    'valid': False,
                    'error': 'Referral code is inactive'
                })
            if referral_code.is_expired:
                return jsonify({
                    'valid': False,
                    'error': 'Referral code has expired'
                })

        return jsonify({
            'valid': True,
            'message': 'Valid referral code'
        })

    except Exception as e:
        logger.error(f"Erro ao validar código de referência {code}: {e}", exc_info=True)
        return jsonify({
            'valid': False,
            'error': 'Validation error'
        }), 500
    finally:
        db.close()


@referrals_bp.route('/api/referral/stats', methods=['GET'])
@login_required
def get_referral_stats():
    """
    Obtém estatísticas de referência do usuário autenticado.

    GET /api/referral/stats

    Returns:
        {
            "success": true,
            "has_code": true,
            "code": "ABC12345",
            "total_referrals": 5,
            "pending_referrals": 2,
            "completed_referrals": 3,
            "total_earnings": 75.00,
            "pending_earnings": 50.00,
            "conversion_rate": 60.0
        }
    """
    db = SessionLocal()
    try:
        user_id = session['user']

        service = ReferralService(db)
        stats = service.get_referrer_stats(user_id)

        return jsonify({
            'success': True,
            **stats
        })

    except Exception as e:
        logger.error(f"Erro ao obter estatísticas de referência: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        db.close()


@referrals_bp.route('/api/referral/click/<code>', methods=['POST'])
def record_referral_click(code: str):
    """
    Registra um clique em código de referência (para tracking).

    POST /api/referral/click/<code>

    Este endpoint é público para permitir tracking de cliques em links compartilhados.

    Returns:
        {
            "success": true
        }
    """
    db = SessionLocal()
    try:
        if not code:
            return jsonify({
                'success': False,
                'error': 'Referral code is required'
            }), 400

        service = ReferralService(db)
        result = service.record_click(code)

        return jsonify({
            'success': result
        })

    except Exception as e:
        logger.error(f"Erro ao registrar clique em código {code}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        db.close()


@referrals_bp.route('/api/referral/my-referrer', methods=['GET'])
@login_required
def get_my_referrer():
    """
    Verifica se o usuário foi indicado por alguém.

    GET /api/referral/my-referrer

    Returns:
        {
            "success": true,
            "has_referrer": true,
            "status": "active",
            "welcome_credit": 10.00,
            "welcome_credit_granted": false,
            "email_verified": true,
            "can_use_credits": true,
            "verification_required_message": null
        }
    """
    db = SessionLocal()
    try:
        user_id = session['user']

        service = ReferralService(db)
        referral = service.get_referral_by_referred(user_id)

        if not referral:
            return jsonify({
                'success': True,
                'has_referrer': False,
                'can_use_credits': True,
                'email_verified': True,
                'verification_required_message': None
            })

        # Determinar se pode usar créditos
        can_use_credits = referral.email_verified
        verification_msg = None if can_use_credits else "Email verification required before using credits"

        return jsonify({
            'success': True,
            'has_referrer': True,
            'status': referral.status,
            'welcome_credit': referral.referred_welcome_credit,
            'welcome_credit_granted': referral.welcome_credit_granted,
            'email_verified': referral.email_verified,
            'can_use_credits': can_use_credits,
            'verification_required_message': verification_msg,
            'referred_at': referral.created_at.isoformat() if referral.created_at else None
        })

    except Exception as e:
        logger.error(f"Erro ao verificar referrer: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        db.close()


@referrals_bp.route('/api/referral/credits', methods=['GET'])
@login_required
def get_user_credits():
    """
    Obtém saldo de créditos e status de verificação do usuário.

    GET /api/referral/credits

    Returns:
        {
            "success": true,
            "balance": 10.00,
            "email_verified": true,
            "can_use_credits": true,
            "verification_required_message": null,
            "credit_summary": {
                "balance": 10.00,
                "total_credits": 10.00,
                "total_debits": 0.00,
                "transaction_count": 1
            }
        }
    """
    db = SessionLocal()
    try:
        user_id = session['user']

        credit_service = CreditService(db)

        # Obter saldo e resumo de créditos
        balance = credit_service.get_balance(user_id)
        credit_summary = credit_service.get_user_credit_summary(user_id)

        # Verificar status de email
        is_verified, error_message = credit_service.is_email_verified(user_id)

        return jsonify({
            'success': True,
            'balance': balance,
            'email_verified': is_verified,
            'can_use_credits': is_verified,
            'verification_required_message': error_message,
            'credit_summary': credit_summary
        })

    except Exception as e:
        logger.error(f"Erro ao obter créditos do usuário: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        db.close()


@referrals_bp.route('/api/referral/credits/use', methods=['POST'])
@login_required
def use_user_credits():
    """
    Usa créditos do usuário para pagamento.

    POST /api/referral/credits/use
    Body: {
        "amount": 5.00,
        "description": "Payment for service",
        "reference_id": "billing_123",
        "reference_type": "billing"
    }

    Returns:
        {
            "success": true,
            "transaction": {...},
            "new_balance": 5.00
        }

    Errors:
        400: Invalid amount, insufficient balance
        401: Not authenticated
        403: Email not verified
    """
    db = SessionLocal()
    try:
        user_id = session['user']
        data = request.json or {}

        amount = data.get('amount')
        if not amount or not isinstance(amount, (int, float)) or amount <= 0:
            return jsonify({
                'success': False,
                'error': 'Valid positive amount is required'
            }), 400

        description = data.get('description', 'Credit usage')
        reference_id = data.get('reference_id')
        reference_type = data.get('reference_type')

        credit_service = CreditService(db)

        # Usar créditos (inclui verificação de email)
        transaction = credit_service.use_credits(
            user_id=user_id,
            amount=float(amount),
            description=description,
            reference_id=reference_id,
            reference_type=reference_type
        )

        if transaction is None:
            return jsonify({
                'success': False,
                'error': 'Insufficient credit balance'
            }), 400

        new_balance = credit_service.get_balance(user_id)

        return jsonify({
            'success': True,
            'transaction': transaction.to_dict(),
            'new_balance': new_balance
        })

    except EmailNotVerifiedError as e:
        logger.warning(f"Tentativa de usar créditos com email não verificado: user={user_id}")
        return jsonify({
            'success': False,
            'error': str(e),
            'email_verification_required': True
        }), 403

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except Exception as e:
        logger.error(f"Erro ao usar créditos: {e}", exc_info=True)
        db.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        db.close()
