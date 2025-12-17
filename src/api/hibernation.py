"""
API endpoints para gerenciar hibernação de instâncias GPU.
"""
from flask import Blueprint, request, jsonify, g
from functools import wraps
import logging
from src.config.database import SessionLocal
from src.models.instance_status import InstanceStatus, HibernationEvent

logger = logging.getLogger(__name__)

hibernation_bp = Blueprint('hibernation', __name__)


def get_hibernation_manager():
    """Obtém o manager de hibernação do contexto da aplicação."""
    from flask import current_app
    if not hasattr(current_app, 'hibernation_manager'):
        raise RuntimeError("AutoHibernationManager não inicializado")
    return current_app.hibernation_manager


@hibernation_bp.route('/api/instances/<instance_id>/wake', methods=['POST'])
def wake_instance(instance_id: str):
    """
    Acorda uma instância hibernada.

    POST /api/instances/{id}/wake
    Body: {
        "gpu_type": "RTX 3090" (opcional),
        "region": "EU" (opcional),
        "max_price": 1.0 (opcional)
    }

    Returns:
        {
            "success": true,
            "instance_id": "...",
            "vast_instance_id": 12345,
            "ssh_host": "1.2.3.4",
            "ssh_port": 22,
            "time_taken": 120.5
        }
    """
    try:
        data = request.json or {}

        manager = get_hibernation_manager()

        result = manager.wake_instance(
            instance_id=instance_id,
            gpu_type=data.get('gpu_type'),
            region=data.get('region'),
            max_price=data.get('max_price', 1.0)
        )

        return jsonify(result)

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except Exception as e:
        logger.error(f"Erro ao acordar instância {instance_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@hibernation_bp.route('/api/instances/<instance_id>/hibernate', methods=['POST'])
def force_hibernate(instance_id: str):
    """
    Força hibernação imediata de uma instância.

    POST /api/instances/{id}/hibernate

    Returns:
        {
            "success": true,
            "snapshot_id": "...",
            "instance_destroyed": true
        }
    """
    db = SessionLocal()
    try:
        instance = db.query(InstanceStatus).filter(
            InstanceStatus.instance_id == instance_id
        ).first()

        if not instance:
            return jsonify({
                'success': False,
                'error': f'Instância {instance_id} não encontrada'
            }), 404

        if instance.status in ['hibernated', 'deleted']:
            return jsonify({
                'success': False,
                'error': f'Instância já está hibernada (status: {instance.status})'
            }), 400

        # Forçar hibernação via manager
        manager = get_hibernation_manager()
        manager._hibernate_instance(db, instance)

        return jsonify({
            'success': True,
            'snapshot_id': instance.snapshot_id,
            'instance_destroyed': True
        })

    except Exception as e:
        logger.error(f"Erro ao hibernar instância {instance_id}: {e}", exc_info=True)
        db.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        db.close()


@hibernation_bp.route('/api/instances/<instance_id>/config', methods=['GET', 'PUT'])
def instance_config(instance_id: str):
    """
    Obtém ou atualiza configuração de auto-hibernação de uma instância.

    GET /api/instances/{id}/config
    Returns: {
        "auto_hibernation_enabled": true,
        "pause_after_minutes": 3,
        "delete_after_minutes": 30,
        "gpu_usage_threshold": 5.0
    }

    PUT /api/instances/{id}/config
    Body: {
        "auto_hibernation_enabled": false,
        "pause_after_minutes": 5,
        ...
    }
    """
    db = SessionLocal()
    try:
        instance = db.query(InstanceStatus).filter(
            InstanceStatus.instance_id == instance_id
        ).first()

        if not instance:
            return jsonify({
                'success': False,
                'error': f'Instância {instance_id} não encontrada'
            }), 404

        if request.method == 'GET':
            return jsonify({
                'auto_hibernation_enabled': instance.auto_hibernation_enabled,
                'pause_after_minutes': instance.pause_after_minutes,
                'delete_after_minutes': instance.delete_after_minutes,
                'gpu_usage_threshold': instance.gpu_usage_threshold,
            })

        elif request.method == 'PUT':
            data = request.json

            if 'auto_hibernation_enabled' in data:
                instance.auto_hibernation_enabled = bool(data['auto_hibernation_enabled'])

            if 'pause_after_minutes' in data:
                value = int(data['pause_after_minutes'])
                if value < 1:
                    return jsonify({'error': 'pause_after_minutes deve ser >= 1'}), 400
                instance.pause_after_minutes = value

            if 'delete_after_minutes' in data:
                value = int(data['delete_after_minutes'])
                if value < 1:
                    return jsonify({'error': 'delete_after_minutes deve ser >= 1'}), 400
                instance.delete_after_minutes = value

            if 'gpu_usage_threshold' in data:
                value = float(data['gpu_usage_threshold'])
                if value < 0 or value > 100:
                    return jsonify({'error': 'gpu_usage_threshold deve estar entre 0 e 100'}), 400
                instance.gpu_usage_threshold = value

            db.commit()

            return jsonify({
                'success': True,
                'config': {
                    'auto_hibernation_enabled': instance.auto_hibernation_enabled,
                    'pause_after_minutes': instance.pause_after_minutes,
                    'delete_after_minutes': instance.delete_after_minutes,
                    'gpu_usage_threshold': instance.gpu_usage_threshold,
                }
            })

    except Exception as e:
        logger.error(f"Erro ao gerenciar config: {e}")
        db.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        db.close()


@hibernation_bp.route('/api/instances/<instance_id>/schedule', methods=['GET', 'PUT', 'DELETE'])
def instance_schedule(instance_id: str):
    """
    Gerencia agendamento de wake/sleep automático.

    GET: Retorna agendamento atual
    PUT: Define/atualiza agendamento
    DELETE: Remove agendamento

    Body PUT: {
        "wake_time": "09:00",
        "sleep_time": "18:00",
        "timezone": "America/Sao_Paulo"
    }
    """
    db = SessionLocal()
    try:
        instance = db.query(InstanceStatus).filter(
            InstanceStatus.instance_id == instance_id
        ).first()

        if not instance:
            return jsonify({'error': f'Instância {instance_id} não encontrada'}), 404

        if request.method == 'GET':
            if not instance.scheduled_wake_enabled:
                return jsonify({'enabled': False})

            return jsonify({
                'enabled': True,
                'wake_time': instance.scheduled_wake_time,
                'sleep_time': instance.scheduled_sleep_time,
                'timezone': instance.timezone,
            })

        elif request.method == 'PUT':
            data = request.json

            instance.scheduled_wake_enabled = True
            instance.scheduled_wake_time = data.get('wake_time', '09:00')
            instance.scheduled_sleep_time = data.get('sleep_time', '18:00')
            instance.timezone = data.get('timezone', 'America/Sao_Paulo')

            db.commit()

            return jsonify({
                'success': True,
                'schedule': {
                    'enabled': True,
                    'wake_time': instance.scheduled_wake_time,
                    'sleep_time': instance.scheduled_sleep_time,
                    'timezone': instance.timezone,
                }
            })

        elif request.method == 'DELETE':
            instance.scheduled_wake_enabled = False
            db.commit()

            return jsonify({
                'success': True,
                'message': 'Agendamento removido'
            })

    except Exception as e:
        logger.error(f"Erro ao gerenciar agendamento: {e}")
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@hibernation_bp.route('/api/instances/<instance_id>/status', methods=['GET'])
def instance_status(instance_id: str):
    """
    Retorna status detalhado de uma instância.

    GET /api/instances/{id}/status

    Returns:
        {
            "instance_id": "...",
            "status": "running",
            "gpu_utilization": 2.5,
            "last_activity": "...",
            "auto_hibernation": {...},
            "vast_info": {...},
            ...
        }
    """
    db = SessionLocal()
    try:
        instance = db.query(InstanceStatus).filter(
            InstanceStatus.instance_id == instance_id
        ).first()

        if not instance:
            return jsonify({'error': f'Instância {instance_id} não encontrada'}), 404

        return jsonify(instance.to_dict())

    except Exception as e:
        logger.error(f"Erro ao obter status: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@hibernation_bp.route('/api/instances/<instance_id>/events', methods=['GET'])
def instance_events(instance_id: str):
    """
    Retorna histórico de eventos de hibernação de uma instância.

    GET /api/instances/{id}/events?limit=50

    Returns:
        {
            "events": [
                {
                    "event_type": "idle_detected",
                    "timestamp": "...",
                    "gpu_utilization": 2.5,
                    ...
                }
            ]
        }
    """
    db = SessionLocal()
    try:
        limit = request.args.get('limit', 50, type=int)

        events = db.query(HibernationEvent).filter(
            HibernationEvent.instance_id == instance_id
        ).order_by(
            HibernationEvent.timestamp.desc()
        ).limit(limit).all()

        return jsonify({
            'events': [event.to_dict() for event in events]
        })

    except Exception as e:
        logger.error(f"Erro ao obter eventos: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@hibernation_bp.route('/api/hibernation/stats', methods=['GET'])
def hibernation_stats():
    """
    Retorna estatísticas gerais de hibernação.

    Returns:
        {
            "total_instances": 10,
            "running": 3,
            "idle": 2,
            "hibernated": 4,
            "deleted": 1
        }
    """
    db = SessionLocal()
    try:
        from sqlalchemy import func

        stats = db.query(
            InstanceStatus.status,
            func.count(InstanceStatus.id).label('count')
        ).group_by(InstanceStatus.status).all()

        result = {status: count for status, count in stats}
        result['total_instances'] = sum(result.values())

        return jsonify(result)

    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()
