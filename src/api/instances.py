"""
API Routes para gerenciamento de instancias GPU
"""
from flask import Blueprint, jsonify, request, g
from src.services import VastService, ResticService

instances_bp = Blueprint('instances', __name__, url_prefix='/api')


def get_vast_service() -> VastService:
    """Factory para criar VastService com API key do usuario"""
    api_key = getattr(g, 'vast_api_key', '')
    return VastService(api_key)


def get_restic_service() -> ResticService:
    """Factory para criar ResticService com settings do usuario logado"""
    user_settings = getattr(g, 'user_settings', {})
    return ResticService(
        repo=user_settings.get('restic_repo', ''),
        password=user_settings.get('restic_password', ''),
        access_key=user_settings.get('r2_access_key', ''),
        secret_key=user_settings.get('r2_secret_key', ''),
        connections=user_settings.get('restic_connections', 32),
    )


@instances_bp.route('/offers')
def list_offers():
    """Lista ofertas de GPU disponiveis"""
    vast = get_vast_service()

    # Parametros de filtro com valores padrao mais permissivos
    params = {
        'gpu_name': request.args.get('gpu_name'),
        'num_gpus': int(request.args.get('num_gpus', 1)),
        'min_gpu_ram': float(request.args.get('gpu_ram', 8)),
        'min_cpu_cores': int(request.args.get('cpu_cores', 4)),
        'min_cpu_ram': float(request.args.get('cpu_ram', 8)),
        'min_disk': float(request.args.get('disk_space', 30)),
        'min_inet_down': float(request.args.get('inet_down', 100)),
        'max_price': float(request.args.get('dph_total', 2.0)),
        'min_cuda': request.args.get('cuda_max_good', '11.0'),
        'min_reliability': float(request.args.get('reliability2', 0.90)),
        'region': request.args.get('region'),
        'verified_only': request.args.get('verified', 'false').lower() == 'true',
        'static_ip': request.args.get('static_ip', 'false').lower() == 'true',
        'limit': int(request.args.get('limit', 50)),
    }

    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}

    offers = vast.search_offers(**params)
    return jsonify({'offers': offers, 'count': len(offers)})


@instances_bp.route('/machines')
def list_my_machines():
    """Lista instancias do usuario"""
    vast = get_vast_service()
    instances = vast.get_my_instances()
    return jsonify({'instances': instances})


@instances_bp.route('/instances', methods=['POST'])
def create_instance():
    """Cria uma nova instancia"""
    vast = get_vast_service()
    data = request.get_json()

    offer_id = data.get('offer_id')
    if not offer_id:
        return jsonify({'error': 'offer_id obrigatorio'}), 400

    image = data.get('image', 'pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime')

    instance_id = vast.create_instance(offer_id, image)
    if instance_id:
        return jsonify({'instance_id': instance_id, 'success': True})
    else:
        return jsonify({'error': 'Falha ao criar instancia'}), 500


@instances_bp.route('/instances/<int:instance_id>')
def get_instance_status(instance_id: int):
    """Retorna status de uma instancia"""
    vast = get_vast_service()
    status = vast.get_instance_status(instance_id)
    return jsonify(status)


@instances_bp.route('/instances/<int:instance_id>', methods=['DELETE'])
def destroy_instance(instance_id: int):
    """Destroi uma instancia"""
    vast = get_vast_service()
    success = vast.destroy_instance(instance_id)
    if success:
        return jsonify({'success': True, 'message': f'Instancia {instance_id} destruida'})
    else:
        return jsonify({'error': 'Falha ao destruir instancia'}), 500


@instances_bp.route('/instances/<int:instance_id>/restore', methods=['POST'])
def restore_to_instance(instance_id: int):
    """Restaura snapshot em uma instancia"""
    vast = get_vast_service()
    restic = get_restic_service()
    data = request.get_json()

    snapshot_id = data.get('snapshot_id', 'latest')
    target_path = data.get('target_path', '/root/workspace')

    # Obter info da instancia
    status = vast.get_instance_status(instance_id)
    if status.get('status') != 'running':
        return jsonify({'error': 'Instancia nao esta rodando'}), 400

    ssh_host = status.get('ssh_host')
    ssh_port = status.get('ssh_port')

    if not ssh_host or not ssh_port:
        return jsonify({'error': 'SSH nao disponivel'}), 400

    # Instalar restic
    if not restic.install_on_remote(ssh_host, ssh_port):
        return jsonify({'error': 'Falha ao instalar restic'}), 500

    # Executar restore
    result = restic.restore(snapshot_id, target_path, ssh_host, ssh_port)
    return jsonify(result)


@instances_bp.route('/instances/<int:instance_id>/install-restic', methods=['POST'])
def install_restic_on_instance(instance_id: int):
    """Instala restic em uma instancia"""
    vast = get_vast_service()
    restic = get_restic_service()

    status = vast.get_instance_status(instance_id)
    if status.get('status') != 'running':
        return jsonify({'error': 'Instancia nao esta rodando'}), 400

    ssh_host = status.get('ssh_host')
    ssh_port = status.get('ssh_port')

    success = restic.install_on_remote(ssh_host, ssh_port)
    return jsonify({'success': success})
