"""
API Routes para DeployWizard

Expoe o DeployWizardService como API REST.
Estrategia multi-start: cria 5 maquinas, usa a primeira que ficar pronta.
"""
from flask import Blueprint, jsonify, request, g
from src.services import get_wizard_service, DeployConfig

deploy_bp = Blueprint('deploy', __name__, url_prefix='/api/wizard')


def get_wizard():
    """Factory para criar wizard com API key do usuario"""
    api_key = getattr(g, 'vast_api_key', '')
    if not api_key:
        return None
    return get_wizard_service(api_key)


@deploy_bp.route('/deploy', methods=['POST'])
def start_deploy():
    """
    Inicia deploy com estrategia multi-start (ASSINCRONO).

    Estrategia:
    - Cria 5 maquinas em paralelo
    - Timeout de 10 segundos por maquina
    - Se maquina nao ficar pronta em 10s, e destruida e tenta outra
    - Usa a primeira que responder
    - Repete ate 3 batches (maximo 15 maquinas)

    Request body:
    {
        "speed_tier": "fast",       # slow, medium, fast, ultra
        "gpu_name": "RTX 4090",     # opcional
        "region": "EU",             # global, US, EU, ASIA
        "disk_space": 50,           # GB minimo
        "max_price": 2.0,           # $/hora maximo
        "snapshot_id": "latest",    # opcional: restaurar snapshot
        "target_path": "/workspace" # path do restore
        "docker_options": "-p 10000-10010:10000-10010/udp"  # opcional: UDP para streaming
    }

    Retorna:
    {
        "job_id": "abc123",
        "status": "starting",
        "poll_url": "/api/wizard/jobs/abc123"
    }
    """
    wizard = get_wizard()
    if not wizard:
        return jsonify({'error': 'API key nao configurada'}), 400

    data = request.get_json() or {}

    config = DeployConfig(
        speed_tier=data.get('speed_tier', 'fast'),
        gpu_name=data.get('gpu_name'),
        region=data.get('region', 'global'),
        disk_space=data.get('disk_space', 50),
        max_price=data.get('max_price', 2.0),
        snapshot_id=data.get('snapshot_id'),
        target_path=data.get('target_path', '/workspace'),
        hot_start=data.get('hot_start', False),
        docker_options=data.get('docker_options'),  # Para UDP, portas extras
    )

    job = wizard.start_deploy(config)

    return jsonify({
        'job_id': job.id,
        'status': job.status,
        'poll_url': f'/api/wizard/jobs/{job.id}'
    })


@deploy_bp.route('/jobs/<job_id>', methods=['GET'])
def get_job_status(job_id: str):
    """Retorna status de um job de deploy"""
    wizard = get_wizard()
    if not wizard:
        return jsonify({'error': 'API key nao configurada'}), 400

    job = wizard.get_job(job_id)
    if not job:
        return jsonify({'error': 'Job nao encontrado'}), 404

    return jsonify(job.to_dict())


@deploy_bp.route('/jobs', methods=['GET'])
def list_jobs():
    """Lista os ultimos jobs de deploy"""
    wizard = get_wizard()
    if not wizard:
        return jsonify({'error': 'API key nao configurada'}), 400

    jobs = wizard.list_jobs(limit=20)
    return jsonify({
        'jobs': [j.to_dict() for j in jobs]
    })


@deploy_bp.route('/offers', methods=['GET'])
def preview_offers():
    """
    Preview das ofertas disponiveis por tier de velocidade.

    Query params:
    - gpu_name: filtrar por GPU
    - region: global, US, EU, ASIA
    - disk_space: GB minimo
    - max_price: $/hora maximo

    Retorna:
    {
        "total_offers": 64,
        "tiers": {
            "ultra": {"count": 24, "min_price": 0.17, ...},
            "fast": {"count": 17, ...},
            ...
        },
        "gpu_options": ["RTX 5090", "RTX 4090", ...],
        "regions": ["global", "US", "EU", "ASIA"]
    }
    """
    wizard = get_wizard()
    if not wizard:
        return jsonify({'error': 'API key nao configurada'}), 400

    config = DeployConfig(
        gpu_name=request.args.get('gpu_name'),
        region=request.args.get('region', 'global'),
        disk_space=float(request.args.get('disk_space', 50)),
        max_price=float(request.args.get('max_price', 2.0)),
    )

    preview = wizard.get_offers_preview(config)
    return jsonify(preview)


@deploy_bp.route('/config', methods=['GET'])
def get_wizard_config():
    """
    Retorna configuracoes disponiveis do wizard.

    Util para o frontend saber quais opcoes mostrar.
    """
    from src.services.deploy_wizard import SPEED_TIERS, GPU_OPTIONS, REGIONS, BATCH_TIMEOUT, BATCH_SIZE, MAX_BATCHES

    return jsonify({
        'speed_tiers': [
            {
                'id': tier_id,
                'name': tier['name'],
                'min_speed': tier['min'],
                'max_speed': tier['max'],
            }
            for tier_id, tier in SPEED_TIERS.items()
        ],
        'gpu_options': GPU_OPTIONS,
        'regions': list(REGIONS.keys()),
        'defaults': {
            'speed_tier': 'fast',
            'disk_space': 50,
            'max_price': 2.0,
            'region': 'global',
        },
        'limits': {
            'batch_timeout': BATCH_TIMEOUT,  # segundos por batch
            'batch_size': BATCH_SIZE,
            'max_batches': MAX_BATCHES,
            'max_machines': BATCH_SIZE * MAX_BATCHES,
        }
    })


# Manter retrocompatibilidade com a API antiga
@deploy_bp.route('/multistart', methods=['POST'])
def multistart_deploy():
    """Alias para /deploy - retrocompatibilidade"""
    return start_deploy()


@deploy_bp.route('/offers/preview', methods=['GET'])
def preview_offers_legacy():
    """Alias para /offers - retrocompatibilidade"""
    return preview_offers()
