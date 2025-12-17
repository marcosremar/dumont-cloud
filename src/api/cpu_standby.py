"""
API endpoints para CPU Standby Service
Sistema de failover transparente GPU → CPU
"""
import os
import json
import logging
from flask import Blueprint, request, jsonify, g

logger = logging.getLogger(__name__)

cpu_standby_bp = Blueprint('cpu_standby', __name__)

# Instância global do serviço (será inicializada pelo app)
_standby_service = None


def get_standby_service():
    """Obtém a instância do serviço de standby"""
    global _standby_service
    return _standby_service


def init_standby_service(vast_api_key: str, gcp_credentials: dict, config: dict = None):
    """
    Inicializa o serviço de CPU Standby.
    Deve ser chamado durante startup do app.
    """
    global _standby_service

    from src.services.cpu_standby_service import CPUStandbyService, CPUStandbyConfig

    # Configurar
    standby_config = CPUStandbyConfig(
        gcp_zone=config.get('gcp_zone', 'europe-west1-b') if config else 'europe-west1-b',
        gcp_machine_type=config.get('gcp_machine_type', 'e2-medium') if config else 'e2-medium',
        gcp_disk_size=config.get('gcp_disk_size', 100) if config else 100,
        gcp_spot=config.get('gcp_spot', True) if config else True,
        sync_interval_seconds=config.get('sync_interval', 30) if config else 30,
        auto_failover=config.get('auto_failover', True) if config else True,
        auto_recovery=config.get('auto_recovery', True) if config else True,
        gpu_min_ram=config.get('gpu_min_ram', 8) if config else 8,
        gpu_max_price=config.get('gpu_max_price', 0.50) if config else 0.50,
        r2_endpoint=os.getenv('R2_ENDPOINT', ''),
        r2_bucket=os.getenv('R2_BUCKET', ''),
    )

    _standby_service = CPUStandbyService(
        vast_api_key=vast_api_key,
        gcp_credentials=gcp_credentials,
        config=standby_config
    )

    logger.info("CPU Standby service initialized")
    return _standby_service


# ==================== STATUS ====================

@cpu_standby_bp.route('/api/standby/status', methods=['GET'])
def get_status():
    """
    Retorna status do sistema de CPU Standby.

    Returns:
        {
            "state": "ready|syncing|failover_active|...",
            "cpu_standby": {...},
            "gpu_instance": {...},
            "sync": {...},
            "failover": {...}
        }
    """
    service = get_standby_service()
    if not service:
        return jsonify({
            'enabled': False,
            'message': 'CPU Standby service not initialized'
        })

    return jsonify(service.get_status())


@cpu_standby_bp.route('/api/standby/active-endpoint', methods=['GET'])
def get_active_endpoint():
    """
    Retorna o endpoint ativo atual (GPU ou CPU).
    Use para redirecionar tráfego de forma transparente.

    Returns:
        {
            "type": "gpu|cpu_standby",
            "host": "...",
            "port": 22,
            "status": "active"
        }
    """
    service = get_standby_service()
    if not service:
        return jsonify({'error': 'CPU Standby service not initialized'}), 400

    endpoint = service.get_active_endpoint()
    if endpoint:
        return jsonify(endpoint)
    else:
        return jsonify({
            'error': 'No active endpoint',
            'hint': 'Register a GPU instance first'
        }), 404


# ==================== AUTO SETUP ====================

@cpu_standby_bp.route('/api/standby/auto-setup', methods=['POST'])
def auto_setup():
    """
    Setup automático completo do sistema de failover.
    Provisiona CPU standby, registra GPU e inicia sincronização.

    Body:
    {
        "gpu_instance_id": 12345,
        "name_suffix": "my-standby"  // opcional
    }

    Este endpoint faz tudo automaticamente:
    1. Provisiona VM CPU no GCP (se não existir)
    2. Registra a GPU para monitoramento
    3. Inicia sincronização contínua
    4. Ativa health checks e auto-failover

    Returns:
    {
        "success": true,
        "cpu_standby": {...},
        "gpu_instance": {...},
        "sync_started": true,
        "auto_failover": true,
        "auto_recovery": true
    }
    """
    service = get_standby_service()
    if not service:
        return jsonify({'error': 'CPU Standby service not initialized'}), 400

    data = request.json or {}
    gpu_instance_id = data.get('gpu_instance_id')
    name_suffix = data.get('name_suffix', 'standby')

    if not gpu_instance_id:
        return jsonify({'error': 'gpu_instance_id is required'}), 400

    try:
        result = {
            'steps': [],
            'success': False
        }

        # Step 1: Provisionar CPU standby (se não existir)
        if not service.cpu_instance:
            logger.info("Step 1: Provisioning CPU standby...")
            instance_id = service.provision_cpu_standby(name_suffix)
            if not instance_id:
                return jsonify({
                    'error': 'Failed to provision CPU standby',
                    'step': 1
                }), 500
            result['steps'].append('cpu_provisioned')
            result['cpu_standby'] = {
                'instance_id': instance_id,
                'name': service.cpu_instance.get('name'),
                'ip': service.cpu_instance.get('external_ip')
            }
        else:
            result['steps'].append('cpu_already_exists')
            result['cpu_standby'] = {
                'name': service.cpu_instance.get('name'),
                'ip': service.cpu_instance.get('external_ip')
            }

        # Step 2: Registrar GPU
        logger.info(f"Step 2: Registering GPU {gpu_instance_id}...")
        if not service.register_gpu_instance(gpu_instance_id):
            return jsonify({
                'error': 'Failed to register GPU instance',
                'step': 2,
                'hint': 'Ensure the GPU instance is running'
            }), 500
        result['steps'].append('gpu_registered')
        result['gpu_instance'] = {
            'id': gpu_instance_id,
            'ssh_host': service.gpu_ssh_host,
            'ssh_port': service.gpu_ssh_port
        }

        # Step 3: Iniciar sync
        logger.info("Step 3: Starting sync...")
        if not service.start_sync():
            return jsonify({
                'error': 'Failed to start sync',
                'step': 3
            }), 500
        result['steps'].append('sync_started')
        result['sync_started'] = True

        # Success!
        result['success'] = True
        result['auto_failover'] = service.config.auto_failover
        result['auto_recovery'] = service.config.auto_recovery
        result['state'] = service.state.value
        result['message'] = 'Failover system fully configured and running'

        logger.info(f"Auto-setup complete: {result}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Auto-setup failed: {e}")
        return jsonify({
            'error': str(e),
            'steps_completed': result.get('steps', [])
        }), 500


# ==================== PROVISIONING ====================

@cpu_standby_bp.route('/api/standby/provision', methods=['POST'])
def provision_standby():
    """
    Provisiona uma nova VM CPU no GCP para standby.

    Body (opcional):
    {
        "name_suffix": "my-standby",
        "machine_type": "e2-medium",
        "zone": "europe-west1-b",
        "disk_size": 100,
        "spot": true
    }

    Returns:
        {
            "success": true,
            "instance_id": "...",
            "name": "dumont-standby-...",
            "ip": "..."
        }
    """
    service = get_standby_service()
    if not service:
        return jsonify({'error': 'CPU Standby service not initialized'}), 400

    data = request.json or {}
    name_suffix = data.get('name_suffix', 'standby')

    # Configurar opções se fornecidas
    if data.get('machine_type'):
        service.config.gcp_machine_type = data['machine_type']
    if data.get('zone'):
        service.config.gcp_zone = data['zone']
    if data.get('disk_size'):
        service.config.gcp_disk_size = data['disk_size']
    if 'spot' in data:
        service.config.gcp_spot = data['spot']

    instance_id = service.provision_cpu_standby(name_suffix)

    if instance_id:
        return jsonify({
            'success': True,
            'instance_id': instance_id,
            'name': service.cpu_instance.get('name'),
            'ip': service.cpu_instance.get('external_ip'),
            'zone': service.cpu_instance.get('zone'),
            'message': 'CPU standby provisioned. Use /api/standby/register-gpu to link a GPU.'
        })
    else:
        return jsonify({
            'error': 'Failed to provision CPU standby',
            'state': service.state.value
        }), 500


@cpu_standby_bp.route('/api/standby/destroy', methods=['POST'])
def destroy_standby():
    """
    Destroi a VM CPU standby e limpa recursos.

    Returns:
        {"success": true}
    """
    service = get_standby_service()
    if not service:
        return jsonify({'error': 'CPU Standby service not initialized'}), 400

    service.cleanup()

    return jsonify({
        'success': True,
        'message': 'CPU standby destroyed'
    })


# ==================== GPU REGISTRATION ====================

@cpu_standby_bp.route('/api/standby/register-gpu', methods=['POST'])
def register_gpu():
    """
    Registra uma instância GPU para monitoramento e sync.

    Body:
    {
        "instance_id": 12345,
        "ssh_host": "...",  // opcional
        "ssh_port": 22      // opcional
    }

    Returns:
        {"success": true, "gpu_instance_id": 12345}
    """
    service = get_standby_service()
    if not service:
        return jsonify({'error': 'CPU Standby service not initialized'}), 400

    data = request.json
    if not data or not data.get('instance_id'):
        return jsonify({'error': 'instance_id is required'}), 400

    instance_id = data['instance_id']
    ssh_host = data.get('ssh_host')
    ssh_port = data.get('ssh_port')

    success = service.register_gpu_instance(
        instance_id=instance_id,
        ssh_host=ssh_host,
        ssh_port=ssh_port
    )

    if success:
        return jsonify({
            'success': True,
            'gpu_instance_id': instance_id,
            'ssh_host': service.gpu_ssh_host,
            'ssh_port': service.gpu_ssh_port,
            'message': 'GPU registered. Use /api/standby/start-sync to begin syncing.'
        })
    else:
        return jsonify({
            'error': 'Failed to register GPU instance',
            'hint': 'Ensure the GPU instance is running'
        }), 400


# ==================== SYNC CONTROL ====================

@cpu_standby_bp.route('/api/standby/start-sync', methods=['POST'])
def start_sync():
    """
    Inicia sincronização contínua GPU → CPU.

    Returns:
        {"success": true, "state": "syncing"}
    """
    service = get_standby_service()
    if not service:
        return jsonify({'error': 'CPU Standby service not initialized'}), 400

    success = service.start_sync()

    if success:
        return jsonify({
            'success': True,
            'state': service.state.value,
            'sync_interval': service.config.sync_interval_seconds,
            'message': 'Sync started. GPU → CPU every {}s'.format(service.config.sync_interval_seconds)
        })
    else:
        return jsonify({
            'error': 'Failed to start sync',
            'hint': 'Ensure CPU standby is provisioned and GPU is registered'
        }), 400


@cpu_standby_bp.route('/api/standby/stop-sync', methods=['POST'])
def stop_sync():
    """
    Para a sincronização.

    Returns:
        {"success": true}
    """
    service = get_standby_service()
    if not service:
        return jsonify({'error': 'CPU Standby service not initialized'}), 400

    service.stop_sync()

    return jsonify({
        'success': True,
        'state': service.state.value,
        'message': 'Sync stopped'
    })


# ==================== FAILOVER ====================

@cpu_standby_bp.route('/api/standby/failover', methods=['POST'])
def trigger_failover():
    """
    Executa failover manual para CPU standby.
    Use quando a GPU está com problemas.

    Returns:
        {
            "success": true,
            "active_endpoint": {...},
            "message": "Failover to CPU standby activated"
        }
    """
    service = get_standby_service()
    if not service:
        return jsonify({'error': 'CPU Standby service not initialized'}), 400

    result = service.trigger_failover()

    if result.get('error'):
        return jsonify(result), 400

    return jsonify(result)


@cpu_standby_bp.route('/api/standby/restore-to-gpu', methods=['POST'])
def restore_to_gpu():
    """
    Restaura dados da CPU standby para uma nova GPU.
    Use após provisionar uma nova GPU.

    Body:
    {
        "new_gpu_instance_id": 12345
    }

    Returns:
        {"success": true, "gpu_instance_id": 12345}
    """
    service = get_standby_service()
    if not service:
        return jsonify({'error': 'CPU Standby service not initialized'}), 400

    data = request.json
    if not data or not data.get('new_gpu_instance_id'):
        return jsonify({'error': 'new_gpu_instance_id is required'}), 400

    result = service.restore_to_gpu(data['new_gpu_instance_id'])

    if result.get('error'):
        return jsonify(result), 400

    return jsonify(result)


# ==================== CONFIGURATION ====================

@cpu_standby_bp.route('/api/standby/config', methods=['GET'])
def get_config():
    """
    Retorna configuração atual do sistema de standby.
    """
    service = get_standby_service()
    if not service:
        return jsonify({'error': 'CPU Standby service not initialized'}), 400

    config = service.config
    return jsonify({
        'gcp': {
            'zone': config.gcp_zone,
            'machine_type': config.gcp_machine_type,
            'disk_size_gb': config.gcp_disk_size,
            'spot': config.gcp_spot
        },
        'sync': {
            'interval_seconds': config.sync_interval_seconds,
            'path': config.sync_path,
            'exclude': config.sync_exclude
        },
        'failover': {
            'health_check_interval': config.health_check_interval,
            'threshold': config.failover_threshold,
            'auto': config.auto_failover
        },
        'backup': {
            'interval_seconds': config.r2_backup_interval,
            'enabled': bool(config.r2_endpoint and config.r2_bucket)
        }
    })


@cpu_standby_bp.route('/api/standby/config', methods=['PUT'])
def update_config():
    """
    Atualiza configuração do sistema de standby.

    Body:
    {
        "sync_interval": 30,
        "auto_failover": true,
        "failover_threshold": 3
    }
    """
    service = get_standby_service()
    if not service:
        return jsonify({'error': 'CPU Standby service not initialized'}), 400

    data = request.json or {}

    if 'sync_interval' in data:
        service.config.sync_interval_seconds = data['sync_interval']
    if 'auto_failover' in data:
        service.config.auto_failover = data['auto_failover']
    if 'failover_threshold' in data:
        service.config.failover_threshold = data['failover_threshold']

    return jsonify({
        'success': True,
        'message': 'Configuration updated'
    })


# ==================== GCP PRICING ====================

@cpu_standby_bp.route('/api/standby/pricing', methods=['GET'])
def get_pricing():
    """
    Retorna estimativa de preços para CPU standby no GCP.

    Query params:
        machine_type: e2-medium (default)
        zone: europe-west1-b (default)
        disk_gb: 100 (default)
    """
    service = get_standby_service()
    if not service:
        return jsonify({'error': 'CPU Standby service not initialized'}), 400

    machine_type = request.args.get('machine_type', 'e2-medium')
    zone = request.args.get('zone', 'europe-west1-b')
    disk_gb = int(request.args.get('disk_gb', 100))

    pricing = service.gcp_provider.get_spot_pricing(machine_type, zone)

    # Adicionar custo de disco
    disk_monthly = disk_gb * pricing['disk_per_gb_monthly_usd']
    total_monthly = pricing['estimated_monthly_usd'] + disk_monthly

    return jsonify({
        'vm': pricing,
        'disk': {
            'size_gb': disk_gb,
            'monthly_usd': disk_monthly
        },
        'total': {
            'estimated_monthly_usd': round(total_monthly, 2),
            'estimated_hourly_usd': round(total_monthly / 720, 4)  # ~720 horas/mês
        }
    })
