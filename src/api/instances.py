"""
API Routes para gerenciamento de instancias GPU
"""
import subprocess
import time
from flask import Blueprint, jsonify, request, g
from src.services.gpu.vast import VastService
from src.services.storage.restic import ResticService
from src.services.codeserver_service import CodeServerService, CodeServerConfig

instances_bp = Blueprint('instances', __name__, url_prefix='/api')


def post_restore_setup(ssh_host: str, ssh_port: int, instance_id: int, target_path: str = "/workspace", ssh_user: str = "root") -> dict:
    """
    Executa setup pos-restore: instala e inicia todos os servicos necessarios.

    Usa CodeServerService para instalacao modular do code-server.

    Servicos instalados:
    - code-server (porta 8080) via CodeServerService
    - DumontAgent (sync automatico)

    Args:
        ssh_host: IP ou hostname do servidor
        ssh_port: Porta SSH
        instance_id: ID da instancia vast.ai
        target_path: Diretorio workspace (default: /workspace)
        ssh_user: Usuario SSH (default: root)

    Returns:
        dict com status de cada servico instalado
    """
    results = {
        "success": True,
        "services": {},
        "errors": [],
        "instance_id": instance_id
    }

    # ========================================
    # 1. INSTALAR CODE-SERVER VIA SERVICE
    # ========================================
    try:
        config = CodeServerConfig(
            port=8080,
            workspace=target_path,
            theme="Default Dark+",
            trust_enabled=False,
            user=ssh_user,
        )

        codeserver = CodeServerService(ssh_host, ssh_port, ssh_user)
        cs_result = codeserver.setup_full(config)

        results["services"]["code_server"] = {
            "installed": cs_result.get("success", False),
            "running": cs_result.get("success", False),
            "port": config.port,
            "steps": cs_result.get("steps", [])
        }

        if not cs_result.get("success"):
            results["errors"].append(f"code-server: {cs_result.get('error', 'Falha desconhecida')}")

    except Exception as e:
        results["services"]["code_server"] = {
            "installed": False,
            "running": False,
            "port": 8080,
            "error": str(e)
        }
        results["errors"].append(f"code-server: {str(e)}")

    # ========================================
    # 2. INSTALAR DUMONT AGENT E OUTROS SERVICOS
    # ========================================
    agent_script = f'''#!/bin/bash
echo "=== POST-RESTORE SETUP ==="
echo "Instance: {instance_id}"
echo "Target: {target_path}"
echo ""

# ========================================
# INSTALAR DUMONT AGENT
# ========================================
echo ">>> Verificando DumontAgent..."

INSTALL_DIR="/opt/dumont"
mkdir -p "$INSTALL_DIR"
mkdir -p /var/log

# Instalar restic se necessario
if ! command -v restic &> /dev/null || ! restic version 2>/dev/null | grep -q "0.17"; then
    echo "Instalando restic 0.17.3..."
    wget -q https://github.com/restic/restic/releases/download/v0.17.3/restic_0.17.3_linux_amd64.bz2 -O /tmp/restic.bz2
    bunzip2 -f /tmp/restic.bz2
    chmod +x /tmp/restic
    mv /tmp/restic /usr/local/bin/restic
    echo "RESTIC_INSTALLED=yes"
else
    echo "RESTIC_INSTALLED=already"
fi

# Verificar se DumontAgent ja esta instalado
if [ -f "$INSTALL_DIR/dumont-agent.sh" ] && pgrep -f "dumont-agent.sh" > /dev/null; then
    echo "DUMONT_AGENT_INSTALLED=already"
    echo "DUMONT_AGENT_RUNNING=yes"
else
    echo "DUMONT_AGENT_INSTALLED=pending"
    echo "DUMONT_AGENT_RUNNING=no"
fi

# ========================================
# VERIFICAR SERVICOS DO TEMPLATE
# ========================================
echo ""
echo ">>> Verificando servicos do template..."

# Jupyter
if pgrep -f "jupyter" > /dev/null; then
    JUPYTER_PORT=$(ss -tlnp 2>/dev/null | grep jupyter | awk '{{print $4}}' | grep -oE '[0-9]+$' | head -1)
    echo "JUPYTER_RUNNING=yes"
    echo "JUPYTER_PORT=${{JUPYTER_PORT:-8888}}"
else
    echo "JUPYTER_RUNNING=no"
fi

# Syncthing
if pgrep -f "syncthing" > /dev/null; then
    echo "SYNCTHING_RUNNING=yes"
else
    echo "SYNCTHING_RUNNING=no"
fi

# Tensorboard
if pgrep -f "tensorboard" > /dev/null; then
    echo "TENSORBOARD_RUNNING=yes"
else
    echo "TENSORBOARD_RUNNING=no"
fi

# GPU
if command -v nvidia-smi &> /dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
    echo "GPU_AVAILABLE=yes"
    echo "GPU_NAME=$GPU_NAME"
else
    echo "GPU_AVAILABLE=no"
fi

echo ""
echo "=== SETUP COMPLETE ==="
echo "POST_RESTORE_SETUP_COMPLETE=yes"
'''

    try:
        result = subprocess.run(
            ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=30',
             '-p', str(ssh_port), f'{ssh_user}@{ssh_host}', agent_script],
            capture_output=True,
            text=True,
            timeout=120  # 2 minutos max
        )

        output = result.stdout

        # Parse resultados
        def get_value(key):
            import re
            match = re.search(f'{key}=(.+)', output)
            return match.group(1).strip() if match else None

        # Restic
        results["services"]["restic"] = {
            "installed": get_value("RESTIC_INSTALLED") in ["yes", "already"]
        }

        # DumontAgent
        results["services"]["dumont_agent"] = {
            "installed": get_value("DUMONT_AGENT_INSTALLED") in ["yes", "already"],
            "running": get_value("DUMONT_AGENT_RUNNING") == "yes"
        }

        # Jupyter
        results["services"]["jupyter"] = {
            "running": get_value("JUPYTER_RUNNING") == "yes",
            "port": int(get_value("JUPYTER_PORT") or 0) or 8888
        }

        # Syncthing
        results["services"]["syncthing"] = {
            "running": get_value("SYNCTHING_RUNNING") == "yes"
        }

        # GPU
        results["services"]["gpu"] = {
            "available": get_value("GPU_AVAILABLE") == "yes",
            "name": get_value("GPU_NAME") or "Unknown"
        }

        results["output"] = output

        if "POST_RESTORE_SETUP_COMPLETE=yes" not in output:
            results["errors"].append("Setup nao completou corretamente")
            results["stderr"] = result.stderr

    except subprocess.TimeoutExpired:
        results["errors"].append("Timeout no setup (>120s)")
    except Exception as e:
        results["errors"].append(str(e))

    # Determinar sucesso geral
    code_server_ok = results["services"].get("code_server", {}).get("running", False)
    results["success"] = code_server_ok and len(results["errors"]) == 0

    return results


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


@instances_bp.route('/instances', methods=['GET'])
def list_instances():
    """Lista todas as instancias do usuario com metricas em tempo real"""
    import subprocess
    vast = get_vast_service()
    instances = vast.get_my_instances()

    # Buscar metricas em tempo real para cada instancia rodando
    for instance in instances:
        if instance.get('actual_status') != 'running':
            continue

        instance_id = instance.get('id')
        public_ip = instance.get('public_ipaddr')
        ports = instance.get('ports', {})
        ssh_port_mapping = ports.get('22/tcp', [])

        if not public_ip or not ssh_port_mapping:
            continue

        ssh_port = ssh_port_mapping[0].get('HostPort') if ssh_port_mapping else None
        if not ssh_port:
            continue

        try:
            # Buscar metricas via SSH (timeout curto para nao travar)
            metrics_cmd = '''
nvidia-smi --query-gpu=utilization.gpu,utilization.memory,temperature.gpu --format=csv,noheader,nounits 2>/dev/null | head -1
top -bn1 | grep "Cpu(s)" | awk '{print 100 - $8}'
            '''
            result = subprocess.run(
                ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=5',
                 '-p', str(ssh_port), f'root@{public_ip}', metrics_cmd],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 1 and lines[0]:
                    # Parse GPU metrics
                    gpu_metrics = lines[0].split(',')
                    if len(gpu_metrics) >= 3:
                        instance['gpu_util'] = float(gpu_metrics[0].strip())
                        instance['mem_usage'] = float(gpu_metrics[1].strip())
                        instance['gpu_temp'] = float(gpu_metrics[2].strip())

                if len(lines) >= 2 and lines[1]:
                    # Parse CPU utilization
                    instance['cpu_util'] = float(lines[1].strip())

        except Exception as e:
            # Se falhar, nao adiciona metricas (frontend usa dados simulados)
            print(f"[Metrics] Falha ao buscar metricas da instancia {instance_id}: {e}")
            pass

    return jsonify({'instances': instances})


@instances_bp.route('/instances', methods=['POST'])
def create_instance():
    """Cria uma nova instancia com Tailscale opcional"""
    vast = get_vast_service()
    data = request.get_json()

    offer_id = data.get('offer_id')
    if not offer_id:
        return jsonify({'error': 'offer_id obrigatorio'}), 400

    image = data.get('image', 'pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime')

    # Obter Tailscale auth key das configuracoes do usuario
    user_settings = getattr(g, 'user_settings', {})
    tailscale_authkey = user_settings.get('tailscale_authkey')

    instance_id = vast.create_instance(
        offer_id=offer_id,
        image=image,
        tailscale_authkey=tailscale_authkey,
        instance_id_hint=offer_id,  # Usar offer_id como hint para hostname
    )
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


@instances_bp.route('/instances/<int:instance_id>/pause', methods=['POST'])
def pause_instance(instance_id: int):
    """Pausa uma instancia (stop sem destruir)"""
    vast = get_vast_service()
    success = vast.pause_instance(instance_id)
    if success:
        return jsonify({'success': True, 'message': f'Instancia {instance_id} pausada'})
    else:
        return jsonify({'error': 'Falha ao pausar instancia'}), 500


@instances_bp.route('/instances/<int:instance_id>/resume', methods=['POST'])
def resume_instance(instance_id: int):
    """Resume uma instancia pausada"""
    vast = get_vast_service()
    success = vast.resume_instance(instance_id)
    if success:
        return jsonify({'success': True, 'message': f'Instancia {instance_id} resumida'})
    else:
        return jsonify({'error': 'Falha ao resumir instancia'}), 500


@instances_bp.route('/instances/<int:instance_id>/restore', methods=['POST'])
def restore_to_instance(instance_id: int):
    """Restaura snapshot em uma instancia com verificacao e fallbacks"""
    vast = get_vast_service()
    restic = get_restic_service()
    data = request.get_json() or {}

    snapshot_id = data.get('snapshot_id', 'latest')
    target_path = data.get('target_path', '/workspace')
    verify = data.get('verify', True)  # Verificar apos restore

    # Obter info da instancia
    status = vast.get_instance_status(instance_id)
    actual_status = status.get('actual_status') or status.get('status')
    if actual_status != 'running':
        return jsonify({
            'success': False,
            'error': 'Instancia nao esta rodando',
            'instance_status': actual_status
        }), 400

    # Tentar IP publico e porta mapeada do SSH, senao usar ssh_host/ssh_port proxy
    public_ip = status.get('public_ipaddr')
    ports = status.get('ports', {})
    ssh_port_mapping = ports.get('22/tcp', [])

    if ssh_port_mapping:
        ssh_host = public_ip
        ssh_port = ssh_port_mapping[0].get('HostPort')
    elif status.get('ssh_host') and status.get('ssh_port'):
        # Fallback para SSH proxy do vast.ai
        ssh_host = status.get('ssh_host')
        ssh_port = status.get('ssh_port')
    else:
        return jsonify({
            'success': False,
            'error': 'SSH nao disponivel (sem porta mapeada ou proxy)'
        }), 400

    if not ssh_port:
        return jsonify({
            'success': False,
            'error': 'Porta SSH nao mapeada'
        }), 400

    disk_space = status.get('disk_space', 0)

    result = {
        'success': False,
        'instance_id': instance_id,
        'snapshot_id': snapshot_id,
        'target_path': target_path,
        'disk_space_gb': disk_space,
        'steps': []
    }

    start_time = time.time()

    def add_step(name, success, message, duration=None):
        result['steps'].append({
            'name': name,
            'success': success,
            'message': message,
            'duration_s': duration
        })

    # Step 1: Verificar espaco em disco
    try:
        step_start = time.time()
        disk_check = subprocess.run(
            ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=20',
             '-p', str(ssh_port), f'root@{ssh_host}',
             'df -BG /workspace 2>/dev/null | tail -1 | awk \'{print $4}\' | tr -d G'],
            capture_output=True, text=True, timeout=30
        )
        free_gb = int(disk_check.stdout.strip() or 0)
        add_step('disk_check', True, f'{free_gb}GB livre (SSH: {ssh_host}:{ssh_port})', time.time() - step_start)

        if free_gb < 70:  # Snapshot precisa de ~68GB
            add_step('disk_space_warning', False, f'Espaco insuficiente: {free_gb}GB livre, precisa de ~70GB')
            result['error'] = f'Espaco em disco insuficiente: {free_gb}GB livre (precisa ~70GB)'
            return jsonify(result), 400
    except Exception as e:
        add_step('disk_check', False, str(e))

    # Step 2: Instalar restic
    try:
        step_start = time.time()
        install_result = subprocess.run(
            ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=30',
             '-p', str(ssh_port), f'root@{ssh_host}',
             '''
             if command -v restic &> /dev/null && restic version | grep -q "0.17"; then
                 echo "RESTIC_OK"
             else
                 wget -q https://github.com/restic/restic/releases/download/v0.17.3/restic_0.17.3_linux_amd64.bz2 -O /tmp/restic.bz2 &&
                 bunzip2 -f /tmp/restic.bz2 &&
                 chmod +x /tmp/restic &&
                 mv /tmp/restic /usr/local/bin/restic &&
                 echo "RESTIC_INSTALLED"
             fi
             '''],
            capture_output=True, text=True, timeout=60
        )
        if 'RESTIC_OK' in install_result.stdout or 'RESTIC_INSTALLED' in install_result.stdout:
            add_step('install_restic', True, 'Restic pronto', time.time() - step_start)
        else:
            add_step('install_restic', False, install_result.stderr or 'Falha desconhecida')
            result['error'] = 'Falha ao instalar restic'
            return jsonify(result), 500
    except Exception as e:
        add_step('install_restic', False, str(e))
        result['error'] = f'Falha ao instalar restic: {e}'
        return jsonify(result), 500

    # Step 3: Executar restore
    try:
        step_start = time.time()
        user_settings = getattr(g, 'user_settings', {})
        from src.config import settings

        restore_cmd = f'''
export AWS_ACCESS_KEY_ID="{user_settings.get('r2_access_key') or settings.r2.access_key_id}"
export AWS_SECRET_ACCESS_KEY="{user_settings.get('r2_secret_key') or settings.r2.secret_access_key}"
export RESTIC_REPOSITORY="{user_settings.get('restic_repo') or settings.r2.restic_repo}"
export RESTIC_PASSWORD="{user_settings.get('restic_password') or settings.restic.password}"
mkdir -p {target_path}
restic restore {snapshot_id} --target / --no-owner -o s3.connections=32 2>&1
echo "RESTORE_EXIT_CODE=$?"
'''
        restore_result = subprocess.run(
            ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=30',
             '-p', str(ssh_port), f'root@{ssh_host}', restore_cmd],
            capture_output=True, text=True, timeout=600  # 10 minutos max
        )

        restore_duration = time.time() - step_start

        if 'RESTORE_EXIT_CODE=0' in restore_result.stdout:
            add_step('restore', True, f'Restore concluido em {restore_duration:.1f}s', restore_duration)
        else:
            # Verificar erros especificos
            if 'no space left' in restore_result.stdout.lower() or 'no space left' in restore_result.stderr.lower():
                add_step('restore', False, 'ERRO: Disco cheio durante restore', restore_duration)
                result['error'] = 'Disco cheio durante restore'
                return jsonify(result), 507  # Insufficient Storage
            else:
                add_step('restore', False, restore_result.stderr or restore_result.stdout[-500:], restore_duration)
                result['error'] = 'Falha no restore'
                return jsonify(result), 500
    except subprocess.TimeoutExpired:
        add_step('restore', False, 'Timeout (10 minutos)')
        result['error'] = 'Restore timeout (10 minutos)'
        return jsonify(result), 504
    except Exception as e:
        add_step('restore', False, str(e))
        result['error'] = f'Falha no restore: {e}'
        return jsonify(result), 500

    # Step 4: Verificar restore (se solicitado)
    if verify:
        try:
            step_start = time.time()
            verify_result = subprocess.run(
                ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=20',
                 '-p', str(ssh_port), f'root@{ssh_host}',
                 f'''
                 echo "=== Verificacao do Restore ==="
                 if [ -d "{target_path}/MuseTalk1.5" ]; then
                     echo "VERIFY_MUSETALK=OK"
                     du -sh {target_path}/MuseTalk1.5
                 else
                     echo "VERIFY_MUSETALK=MISSING"
                 fi

                 if [ -d "{target_path}/MuseTalk1.5/models" ]; then
                     echo "VERIFY_MODELS=OK"
                     ls {target_path}/MuseTalk1.5/models/ | wc -l
                 else
                     echo "VERIFY_MODELS=MISSING"
                 fi

                 TOTAL_SIZE=$(du -sm {target_path} 2>/dev/null | cut -f1)
                 echo "VERIFY_TOTAL_SIZE_MB=$TOTAL_SIZE"

                 if [ "$TOTAL_SIZE" -gt 60000 ]; then
                     echo "VERIFY_SIZE=OK"
                 else
                     echo "VERIFY_SIZE=SMALL"
                 fi

                 echo "VERIFY_COMPLETE"
                 '''],
                capture_output=True, text=True, timeout=120
            )

            verify_ok = ('VERIFY_MUSETALK=OK' in verify_result.stdout and
                        'VERIFY_MODELS=OK' in verify_result.stdout and
                        'VERIFY_SIZE=OK' in verify_result.stdout)

            if verify_ok:
                add_step('verify', True, 'Verificacao passou - todos arquivos presentes', time.time() - step_start)
            else:
                issues = []
                if 'VERIFY_MUSETALK=MISSING' in verify_result.stdout:
                    issues.append('MuseTalk1.5 ausente')
                if 'VERIFY_MODELS=MISSING' in verify_result.stdout:
                    issues.append('Models ausentes')
                if 'VERIFY_SIZE=SMALL' in verify_result.stdout:
                    issues.append('Tamanho menor que esperado')

                add_step('verify', False, f'Problemas: {", ".join(issues)}', time.time() - step_start)
                result['verification_issues'] = issues
                result['warning'] = 'Restore parcialmente incompleto'
        except Exception as e:
            add_step('verify', False, str(e))

    # Step 5: Verificar disco apos restore
    try:
        step_start = time.time()
        post_disk = subprocess.run(
            ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=20',
             '-p', str(ssh_port), f'root@{ssh_host}',
             'df -h /workspace | tail -1'],
            capture_output=True, text=True, timeout=30
        )
        add_step('post_disk_check', True, post_disk.stdout.strip(), time.time() - step_start)
        result['disk_after_restore'] = post_disk.stdout.strip()
    except Exception as e:
        add_step('post_disk_check', False, str(e))

    # Step 6: Executar post-restore setup (instalar code-server, etc)
    run_setup = data.get('run_setup', True)  # Por padrao, sempre executa setup
    if run_setup:
        try:
            step_start = time.time()
            setup_result = post_restore_setup(
                ssh_host=ssh_host,
                ssh_port=int(ssh_port),
                instance_id=instance_id,
                target_path=target_path
            )

            if setup_result['success']:
                # Resumo dos servicos
                services = setup_result.get('services', {})
                code_server = services.get('code_server', {})
                gpu = services.get('gpu', {})

                msg = f"code-server: {'OK' if code_server.get('running') else 'FALHOU'}"
                if gpu.get('available'):
                    msg += f" | GPU: {gpu.get('name', 'OK')}"

                add_step('post_setup', True, msg, time.time() - step_start)
            else:
                add_step('post_setup', False, ', '.join(setup_result.get('errors', ['Setup falhou'])), time.time() - step_start)

            result['setup'] = setup_result
        except Exception as e:
            add_step('post_setup', False, str(e), time.time() - step_start)
            result['setup_error'] = str(e)

    # Resultado final
    result['success'] = all(s['success'] for s in result['steps'] if s['name'] in ['install_restic', 'restore'])
    result['total_duration_s'] = time.time() - start_time

    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 500


@instances_bp.route('/instances/<int:instance_id>/install-restic', methods=['POST'])
def install_restic_on_instance(instance_id: int):
    """Instala restic em uma instancia"""
    vast = get_vast_service()
    restic = get_restic_service()

    status = vast.get_instance_status(instance_id)
    if (status.get('actual_status') or status.get('status')) != 'running':
        return jsonify({'error': 'Instancia nao esta rodando'}), 400

    ssh_host = status.get('ssh_host')
    ssh_port = status.get('ssh_port')

    success = restic.install_on_remote(ssh_host, ssh_port)
    return jsonify({'success': success})


@instances_bp.route('/instances/<int:instance_id>/logs')
def get_instance_logs(instance_id: int):
    """Retorna logs de uma instancia"""
    vast = get_vast_service()
    logs = vast.get_instance_logs(instance_id)
    return jsonify({'logs': logs})


@instances_bp.route('/instances/<int:instance_id>/lock', methods=['POST'])
def toggle_instance_lock(instance_id: int):
    """Alterna o estado de bloqueio de uma instancia"""
    import json
    import os

    data = request.get_json()
    locked = data.get('locked', False)

    # Salvar estado de lock no config.json
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.json')

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except:
        config = {}

    if 'locked_instances' not in config:
        config['locked_instances'] = {}

    config['locked_instances'][str(instance_id)] = locked

    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    return jsonify({'success': True, 'locked': locked})


@instances_bp.route('/balance')
def get_balance():
    """Retorna o saldo da conta vast.ai"""
    vast = get_vast_service()
    balance_info = vast.get_balance()
    return jsonify(balance_info)


@instances_bp.route('/instances/<int:instance_id>/snapshot', methods=['POST'])
def force_snapshot(instance_id: int):
    """Força criação de snapshot na instância via DumontAgent"""
    import subprocess

    vast = get_vast_service()

    # Obter info da instancia
    status = vast.get_instance_status(instance_id)
    if (status.get('actual_status') or status.get('status')) != 'running':
        return jsonify({'error': 'Instancia nao esta rodando'}), 400

    # Usar IP publico e porta mapeada do SSH (22/tcp)
    public_ip = status.get('public_ipaddr')
    ports = status.get('ports', {})
    ssh_port_mapping = ports.get('22/tcp', [])

    if not public_ip or not ssh_port_mapping:
        return jsonify({'error': 'SSH nao disponivel (sem IP publico ou porta 22)'}), 400

    ssh_port = ssh_port_mapping[0].get('HostPort') if ssh_port_mapping else None
    if not ssh_port:
        return jsonify({'error': 'Porta SSH nao mapeada'}), 400

    # Executar backup via dumontctl
    try:
        result = subprocess.run(
            ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=30',
             '-p', str(ssh_port), f'root@{public_ip}',
             'dumontctl backup 2>&1 || (source /opt/dumont/config.env && restic backup /workspace --tag manual -o s3.connections=32)'],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': 'Snapshot criado com sucesso',
                'output': result.stdout
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Falha ao criar snapshot',
                'output': result.stdout,
                'stderr': result.stderr
            }), 500

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Timeout ao criar snapshot (>120s)'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@instances_bp.route('/instances/<int:instance_id>/agent-status')
def get_instance_agent_status(instance_id: int):
    """Retorna status do DumontAgent em uma instância"""
    import subprocess

    vast = get_vast_service()

    status = vast.get_instance_status(instance_id)
    if (status.get('actual_status') or status.get('status')) != 'running':
        return jsonify({'error': 'Instancia nao esta rodando', 'agent_installed': False}), 400

    # Usar IP publico e porta mapeada do SSH (22/tcp)
    public_ip = status.get('public_ipaddr')
    ports = status.get('ports', {})
    ssh_port_mapping = ports.get('22/tcp', [])

    if not public_ip or not ssh_port_mapping:
        return jsonify({'error': 'SSH nao disponivel', 'agent_installed': False}), 400

    ssh_port = ssh_port_mapping[0].get('HostPort') if ssh_port_mapping else None
    if not ssh_port:
        return jsonify({'error': 'Porta SSH nao mapeada', 'agent_installed': False}), 400

    try:
        # Verificar status do agente
        result = subprocess.run(
            ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=20',
             '-p', str(ssh_port), f'root@{public_ip}',
             'cat /tmp/dumont-agent-status.json 2>/dev/null || echo "{}"'],
            capture_output=True,
            text=True,
            timeout=30
        )

        import json
        try:
            agent_status = json.loads(result.stdout.strip() or '{}')
        except:
            agent_status = {}

        # Verificar se agente está instalado
        check_result = subprocess.run(
            ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=10',
             '-p', str(ssh_port), f'root@{public_ip}',
             'test -f /opt/dumont/dumont-agent.sh && pgrep -f dumont-agent.sh > /dev/null && echo "running" || echo "stopped"'],
            capture_output=True,
            text=True,
            timeout=15
        )

        return jsonify({
            'agent_installed': 'running' in check_result.stdout or bool(agent_status),
            'agent_running': 'running' in check_result.stdout,
            'status': agent_status
        })

    except Exception as e:
        return jsonify({'error': str(e), 'agent_installed': False}), 500


@instances_bp.route('/instances/<int:instance_id>/codeserver-status')
def get_codeserver_status(instance_id: int):
    """Retorna status do code-server em uma instância"""
    vast = get_vast_service()

    status = vast.get_instance_status(instance_id)
    if (status.get('actual_status') or status.get('status')) != 'running':
        return jsonify({'error': 'Instancia nao esta rodando', 'running': False}), 400

    # Usar IP publico e porta mapeada do SSH (22/tcp)
    public_ip = status.get('public_ipaddr')
    ports = status.get('ports', {})
    ssh_port_mapping = ports.get('22/tcp', [])

    if not public_ip or not ssh_port_mapping:
        return jsonify({'error': 'SSH nao disponivel', 'running': False}), 400

    ssh_port = ssh_port_mapping[0].get('HostPort') if ssh_port_mapping else None
    if not ssh_port:
        return jsonify({'error': 'Porta SSH nao mapeada', 'running': False}), 400

    try:
        codeserver = CodeServerService(public_ip, int(ssh_port), "root")
        cs_status = codeserver.status()

        # Pegar porta mapeada do code-server (8080 interno)
        codeserver_port_mapping = ports.get('8080/tcp', [])
        host_port = codeserver_port_mapping[0].get('HostPort') if codeserver_port_mapping else None

        return jsonify({
            'running': cs_status.get('running', False),
            'installed': codeserver.is_installed(),
            'internal_port': 8080,
            'host_port': host_port,
            'access_url': f"http://{public_ip}:{host_port}" if host_port else None,
            'output': cs_status.get('output', '')
        })

    except Exception as e:
        return jsonify({'error': str(e), 'running': False}), 500


@instances_bp.route('/instances/<int:instance_id>/codeserver-restart', methods=['POST'])
def restart_codeserver(instance_id: int):
    """Reinicia code-server em uma instância"""
    vast = get_vast_service()
    data = request.get_json() or {}

    status = vast.get_instance_status(instance_id)
    if (status.get('actual_status') or status.get('status')) != 'running':
        return jsonify({'error': 'Instancia nao esta rodando'}), 400

    public_ip = status.get('public_ipaddr')
    ports = status.get('ports', {})
    ssh_port_mapping = ports.get('22/tcp', [])

    if not public_ip or not ssh_port_mapping:
        return jsonify({'error': 'SSH nao disponivel'}), 400

    ssh_port = ssh_port_mapping[0].get('HostPort') if ssh_port_mapping else None
    if not ssh_port:
        return jsonify({'error': 'Porta SSH nao mapeada'}), 400

    workspace = data.get('workspace', '/workspace')

    try:
        config = CodeServerConfig(
            port=8080,
            workspace=workspace,
            theme="Default Dark+",
            trust_enabled=False,
            user="root",
        )

        codeserver = CodeServerService(public_ip, int(ssh_port), "root")

        # Verificar se esta instalado
        if not codeserver.is_installed():
            # Instalar e configurar
            result = codeserver.setup_full(config)
        else:
            # Apenas reiniciar
            result = codeserver.start(config)

        # Pegar porta mapeada
        codeserver_port_mapping = ports.get('8080/tcp', [])
        host_port = codeserver_port_mapping[0].get('HostPort') if codeserver_port_mapping else None

        return jsonify({
            'success': result.get('success', False),
            'message': result.get('message', 'Operacao concluida'),
            'port': config.port,
            'host_port': host_port,
            'access_url': f"http://{public_ip}:{host_port}" if host_port else None,
            'details': result
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@instances_bp.route('/instances/<int:instance_id>/services-health')
def check_services_health(instance_id: int):
    """Verifica saude de todos os servicos da instancia (code-server, agent, etc)"""
    vast = get_vast_service()

    status = vast.get_instance_status(instance_id)
    if (status.get('actual_status') or status.get('status')) != 'running':
        return jsonify({'error': 'Instancia nao esta rodando', 'healthy': False}), 400

    public_ip = status.get('public_ipaddr')
    ports = status.get('ports', {})
    ssh_port_mapping = ports.get('22/tcp', [])

    if not public_ip or not ssh_port_mapping:
        return jsonify({'error': 'SSH nao disponivel', 'healthy': False}), 400

    ssh_port = ssh_port_mapping[0].get('HostPort') if ssh_port_mapping else None
    if not ssh_port:
        return jsonify({'error': 'Porta SSH nao mapeada', 'healthy': False}), 400

    health = {
        'instance_id': instance_id,
        'healthy': True,
        'services': {}
    }

    try:
        # Verificar code-server
        codeserver = CodeServerService(public_ip, int(ssh_port), "root")
        cs_status = codeserver.status()
        codeserver_port_mapping = ports.get('8080/tcp', [])
        cs_host_port = codeserver_port_mapping[0].get('HostPort') if codeserver_port_mapping else None

        health['services']['code_server'] = {
            'running': cs_status.get('running', False),
            'port': 8080,
            'host_port': cs_host_port,
            'access_url': f"http://{public_ip}:{cs_host_port}" if cs_host_port else None
        }

        # Verificar DumontAgent
        agent_check = subprocess.run(
            ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=10',
             '-p', str(ssh_port), f'root@{public_ip}',
             'pgrep -f dumont-agent.sh > /dev/null && echo "running" || echo "stopped"'],
            capture_output=True,
            text=True,
            timeout=15
        )
        health['services']['dumont_agent'] = {
            'running': 'running' in agent_check.stdout
        }

        # Verificar GPU
        gpu_check = subprocess.run(
            ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=10',
             '-p', str(ssh_port), f'root@{public_ip}',
             'nvidia-smi --query-gpu=name,utilization.gpu --format=csv,noheader 2>/dev/null || echo "NO_GPU"'],
            capture_output=True,
            text=True,
            timeout=15
        )

        if 'NO_GPU' not in gpu_check.stdout:
            gpu_info = gpu_check.stdout.strip().split(',')
            health['services']['gpu'] = {
                'available': True,
                'name': gpu_info[0].strip() if gpu_info else 'Unknown',
                'utilization': gpu_info[1].strip() if len(gpu_info) > 1 else '0%'
            }
        else:
            health['services']['gpu'] = {'available': False}

        # Determinar saude geral
        health['healthy'] = health['services']['code_server']['running']

        return jsonify(health)

    except Exception as e:
        return jsonify({'error': str(e), 'healthy': False}), 500
