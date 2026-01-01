"""
API Routes para operacoes com Snapshots
"""
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, g
from src.services import ResticService
from src.config import settings
from src.config.database import SessionLocal
from src.models.snapshot_config import SnapshotConfig

snapshots_bp = Blueprint('snapshots', __name__, url_prefix='/api')


# Valid interval options (in minutes)
VALID_INTERVALS = [5, 15, 30, 60]


def get_restic_service() -> ResticService:
    """Factory para criar ResticService com settings do usuario ou defaults do .env"""
    user_settings = getattr(g, 'user_settings', {})

    # Usar settings do usuario se disponiveis, senao usar do .env
    return ResticService(
        repo=user_settings.get('restic_repo') or settings.r2.restic_repo,
        password=user_settings.get('restic_password') or settings.restic.password,
        access_key=user_settings.get('r2_access_key') or settings.r2.access_key,
        secret_key=user_settings.get('r2_secret_key') or settings.r2.secret_key,
        connections=user_settings.get('restic_connections', settings.restic.connections),
    )


@snapshots_bp.route('/snapshots')
def list_snapshots():
    """Lista todos os snapshots"""
    show_all = request.args.get('all', 'false').lower() == 'true'
    restic = get_restic_service()
    result = restic.list_snapshots(deduplicate=not show_all)
    return jsonify(result)


@snapshots_bp.route('/snapshots/<snapshot_id>')
def get_snapshot(snapshot_id: str):
    """Retorna detalhes de um snapshot"""
    restic = get_restic_service()
    result = restic.list_snapshots()

    for s in result.get('snapshots', []):
        if s['id'].startswith(snapshot_id):
            return jsonify(s)

    return jsonify({'error': 'Snapshot nao encontrado'}), 404


@snapshots_bp.route('/snapshots/<snapshot_id>/folders')
def get_snapshot_folders(snapshot_id: str):
    """Lista pastas de um snapshot"""
    restic = get_restic_service()
    folders = restic.get_snapshot_folders(snapshot_id)
    return jsonify({'folders': folders})


@snapshots_bp.route('/snapshots/<snapshot_id>/tree')
def get_snapshot_tree(snapshot_id: str):
    """Lista arvore de arquivos de um snapshot"""
    restic = get_restic_service()
    max_depth = request.args.get('depth', 3, type=int)
    tree = restic.get_snapshot_tree(snapshot_id, max_depth=max_depth)
    return jsonify({'tree': tree})


@snapshots_bp.route('/snapshots/config/<instance_id>', methods=['GET'])
def get_snapshot_config(instance_id: str):
    """
    Get snapshot configuration for an instance.

    Returns the current snapshot scheduling configuration including:
    - interval_minutes: How often snapshots are taken
    - enabled: Whether automatic snapshots are enabled
    - next_snapshot_at: When the next snapshot is scheduled
    - last_snapshot_at: When the last snapshot was taken
    - status: Current status (success, failure, overdue, pending, disabled)
    """
    db = SessionLocal()
    try:
        config = db.query(SnapshotConfig).filter(
            SnapshotConfig.instance_id == instance_id
        ).first()

        if not config:
            # Return default config if none exists
            return jsonify({
                'instance_id': instance_id,
                'interval_minutes': settings.snapshot.default_interval_minutes,
                'enabled': True,
                'next_snapshot_at': None,
                'last_snapshot_at': None,
                'last_snapshot_status': None,
                'last_snapshot_error': None,
                'consecutive_failures': 0,
                'status': 'pending',
                'created_at': None,
                'updated_at': None,
            })

        result = config.to_dict()
        result['status'] = config.status
        return jsonify(result)
    finally:
        db.close()


@snapshots_bp.route('/snapshots/status', methods=['GET'])
def get_snapshots_status():
    """
    Get aggregate snapshot status across all instances.

    Returns an overview of snapshot health including:
    - total_instances: Total number of instances with snapshot configs
    - enabled_count: Number of instances with snapshots enabled
    - disabled_count: Number of instances with snapshots disabled
    - status_counts: Count of instances by status (success, failure, overdue, pending, disabled)
    - instances: List of all instance configurations with their status
    """
    db = SessionLocal()
    try:
        configs = db.query(SnapshotConfig).all()

        # Initialize counters
        status_counts = {
            'success': 0,
            'failure': 0,
            'overdue': 0,
            'pending': 0,
            'disabled': 0,
        }
        enabled_count = 0
        disabled_count = 0
        instances = []

        for config in configs:
            status = config.status
            status_counts[status] = status_counts.get(status, 0) + 1

            if config.enabled:
                enabled_count += 1
            else:
                disabled_count += 1

            instance_data = config.to_dict()
            instance_data['status'] = status
            instances.append(instance_data)

        return jsonify({
            'total_instances': len(configs),
            'enabled_count': enabled_count,
            'disabled_count': disabled_count,
            'status_counts': status_counts,
            'healthy': status_counts['failure'] == 0 and status_counts['overdue'] == 0,
            'instances': instances,
        })
    finally:
        db.close()


@snapshots_bp.route('/snapshots/config/<instance_id>', methods=['POST'])
def update_snapshot_config(instance_id: str):
    """
    Update snapshot configuration for an instance.

    Request body:
    - interval_minutes (int): Snapshot interval (5, 15, 30, or 60 minutes)
    - enabled (bool): Whether to enable automatic snapshots

    Validation:
    - interval_minutes must be one of: 5, 15, 30, 60
    - enabled must be a boolean

    Returns the updated configuration.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    # Validate interval_minutes
    interval_minutes = data.get('interval_minutes')
    if interval_minutes is not None:
        if not isinstance(interval_minutes, int):
            return jsonify({'error': 'interval_minutes must be an integer'}), 400
        if interval_minutes not in VALID_INTERVALS:
            return jsonify({
                'error': f'interval_minutes must be one of: {VALID_INTERVALS}'
            }), 400

    # Validate enabled
    enabled = data.get('enabled')
    if enabled is not None and not isinstance(enabled, bool):
        return jsonify({'error': 'enabled must be a boolean'}), 400

    db = SessionLocal()
    try:
        config = db.query(SnapshotConfig).filter(
            SnapshotConfig.instance_id == instance_id
        ).first()

        if not config:
            # Create new config
            config = SnapshotConfig(
                instance_id=instance_id,
                interval_minutes=interval_minutes if interval_minutes else settings.snapshot.default_interval_minutes,
                enabled=enabled if enabled is not None else True,
            )
            db.add(config)
        else:
            # Update existing config
            if interval_minutes is not None:
                config.interval_minutes = interval_minutes
            if enabled is not None:
                config.enabled = enabled

        # Calculate next snapshot time if enabled
        if config.enabled:
            config.next_snapshot_at = datetime.utcnow() + timedelta(minutes=config.interval_minutes)

        db.commit()
        db.refresh(config)

        result = config.to_dict()
        result['status'] = config.status
        return jsonify(result)
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()
