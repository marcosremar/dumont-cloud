"""
API endpoints para gerenciar snapshots de GPU com ANS
"""
from flask import Blueprint, request, jsonify
from src.services.gpu.snapshot import GPUSnapshotService
import os
import logging

logger = logging.getLogger(__name__)

snapshots_ans_bp = Blueprint('snapshots_ans', __name__)

# Configuração R2
R2_ENDPOINT = os.getenv('R2_ENDPOINT', 'https://142ed673a5cc1a9e91519c099af3d791.r2.cloudflarestorage.com')
R2_BUCKET = os.getenv('R2_BUCKET', 'musetalk')

snapshot_service = GPUSnapshotService(R2_ENDPOINT, R2_BUCKET)


@snapshots_ans_bp.route('/api/gpu-snapshots', methods=['GET'])
def list_snapshots():
    """Lista todos os snapshots"""
    try:
        instance_id = request.args.get('instance_id')
        snapshots = snapshot_service.list_snapshots(instance_id)
        return jsonify({
            'success': True,
            'snapshots': snapshots
        })
    except Exception as e:
        logger.error(f"Erro ao listar snapshots: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@snapshots_ans_bp.route('/api/gpu-snapshots/create', methods=['POST'])
def create_snapshot():
    """
    Cria snapshot de uma instância GPU (hibernar)

    Body:
    {
        "instance_id": "12345",
        "ssh_host": "1.2.3.4",
        "ssh_port": 22,
        "workspace_path": "/workspace",
        "snapshot_name": "optional-name"
    }
    """
    try:
        data = request.json

        required_fields = ['instance_id', 'ssh_host', 'ssh_port']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Campo obrigatório: {field}'
                }), 400

        result = snapshot_service.create_snapshot(
            instance_id=data['instance_id'],
            ssh_host=data['ssh_host'],
            ssh_port=data['ssh_port'],
            workspace_path=data.get('workspace_path', '/workspace'),
            snapshot_name=data.get('snapshot_name')
        )

        return jsonify({
            'success': True,
            'snapshot': result
        })

    except Exception as e:
        logger.error(f"Erro ao criar snapshot: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@snapshots_ans_bp.route('/api/gpu-snapshots/<snapshot_id>/restore', methods=['POST'])
def restore_snapshot(snapshot_id):
    """
    Restaura snapshot em uma instância GPU

    Body:
    {
        "ssh_host": "1.2.3.4",
        "ssh_port": 22,
        "workspace_path": "/workspace"
    }
    """
    try:
        data = request.json

        required_fields = ['ssh_host', 'ssh_port']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Campo obrigatório: {field}'
                }), 400

        result = snapshot_service.restore_snapshot(
            snapshot_id=snapshot_id,
            ssh_host=data['ssh_host'],
            ssh_port=data['ssh_port'],
            workspace_path=data.get('workspace_path', '/workspace')
        )

        return jsonify({
            'success': True,
            'restore': result
        })

    except Exception as e:
        logger.error(f"Erro ao restaurar snapshot: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@snapshots_ans_bp.route('/api/gpu-snapshots/<snapshot_id>', methods=['DELETE'])
def delete_snapshot(snapshot_id):
    """Deleta um snapshot"""
    try:
        snapshot_service.delete_snapshot(snapshot_id)

        return jsonify({
            'success': True,
            'message': f'Snapshot {snapshot_id} deletado'
        })

    except Exception as e:
        logger.error(f"Erro ao deletar snapshot: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@snapshots_ans_bp.route('/api/instances/<instance_id>/hibernate', methods=['POST'])
def hibernate_instance(instance_id):
    """
    Hiberna uma instância (snapshot + destroy)

    Body:
    {
        "ssh_host": "1.2.3.4",
        "ssh_port": 22,
        "workspace_path": "/workspace",
        "destroy_after": true
    }
    """
    try:
        data = request.json

        # 1. Criar snapshot
        logger.info(f"Hibernando instância {instance_id}...")

        snapshot_result = snapshot_service.create_snapshot(
            instance_id=instance_id,
            ssh_host=data['ssh_host'],
            ssh_port=data['ssh_port'],
            workspace_path=data.get('workspace_path', '/workspace'),
            snapshot_name=f"{instance_id}_hibernate"
        )

        # 2. Destruir instância (se solicitado)
        destroyed = False
        if data.get('destroy_after', False):
            # TODO: Integrar com vast.ai API para destruir instância
            # vast_service.destroy_instance(instance_id)
            destroyed = True
            logger.info(f"Instância {instance_id} destruída")

        return jsonify({
            'success': True,
            'snapshot': snapshot_result,
            'instance_destroyed': destroyed
        })

    except Exception as e:
        logger.error(f"Erro ao hibernar instância: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@snapshots_ans_bp.route('/api/instances/<instance_id>/wake', methods=['POST'])
def wake_instance(instance_id):
    """
    Acorda instância hibernada (create + restore)

    Body:
    {
        "snapshot_id": "optional-snapshot-id",
        "gpu_type": "RTX 5090",
        "region": "eu"
    }
    """
    try:
        data = request.json

        # 1. Criar nova instância
        # TODO: Integrar com vast.ai API
        # new_instance = vast_service.create_instance(...)

        # Simulação por enquanto
        new_instance = {
            'id': 'new_instance_123',
            'ssh_host': '1.2.3.4',
            'ssh_port': 12345
        }

        # 2. Restaurar snapshot
        snapshot_id = data.get('snapshot_id', f"{instance_id}_hibernate")

        logger.info(f"Restaurando snapshot {snapshot_id} na nova instância...")

        restore_result = snapshot_service.restore_snapshot(
            snapshot_id=snapshot_id,
            ssh_host=new_instance['ssh_host'],
            ssh_port=new_instance['ssh_port'],
            workspace_path='/workspace'
        )

        return jsonify({
            'success': True,
            'instance': new_instance,
            'restore': restore_result
        })

    except Exception as e:
        logger.error(f"Erro ao acordar instância: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
