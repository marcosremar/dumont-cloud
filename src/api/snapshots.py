"""
API Routes para operacoes com Snapshots
"""
from flask import Blueprint, jsonify, request, g
from src.services import ResticService
from src.config import settings

snapshots_bp = Blueprint('snapshots', __name__, url_prefix='/api')


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
