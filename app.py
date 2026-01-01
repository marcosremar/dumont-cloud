#!/usr/bin/env python3
"""
Dumont Cloud - GPU Cloud Manager
Aplicacao principal Flask
"""
import os
import sys
import json
from flask import Flask, g, session, redirect, url_for, request, Response, jsonify
from flask_cors import CORS
from functools import wraps
import requests
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, REGISTRY

# Adiciona src ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import settings
from src.api import snapshots_bp, instances_bp
from src.api.deploy import deploy_bp
from src.api.regions import regions_bp, users_regions_bp
from src.api.gpu_checkpoints import gpu_bp
from src.api.price_reports import price_reports_bp
from src.api.snapshots_ans import snapshots_ans_bp
from src.api.hibernation import hibernation_bp
from src.api.cpu_standby import cpu_standby_bp, init_standby_service
from src.api.chat import chat_bp
from src.api.economy import economy_bp
from src.api.templates import templates_bp
from src.api.email_preferences import email_preferences_bp
from src.api.unsubscribe import unsubscribe_bp
from src.api.referrals import referrals_bp
from src.api.affiliates import affiliates_bp
from src.api.credits import credits_bp
from src.api.templates import templates_bp


def create_app():
    """Factory function para criar a aplicacao Flask"""
    # Disable automatic static route - we'll handle everything in catchall
    app = Flask(__name__, static_folder=None)
    app.secret_key = settings.app.secret_key

    # Cookie de sessao valido para todos os subdominios
    app.config['SESSION_COOKIE_DOMAIN'] = '.dumontcloud.com'
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = True

    # CORS para desenvolvimento
    CORS(app, supports_credentials=True)

    # Registrar blueprints da API
    app.register_blueprint(snapshots_bp)
    app.register_blueprint(snapshots_ans_bp)
    app.register_blueprint(hibernation_bp)
    app.register_blueprint(instances_bp)
    app.register_blueprint(deploy_bp)
    app.register_blueprint(regions_bp)
    app.register_blueprint(users_regions_bp)
    app.register_blueprint(gpu_bp)
    app.register_blueprint(price_reports_bp)
    app.register_blueprint(cpu_standby_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(economy_bp)
    app.register_blueprint(templates_bp)
    app.register_blueprint(email_preferences_bp)
    app.register_blueprint(unsubscribe_bp)
    app.register_blueprint(referrals_bp)
    app.register_blueprint(affiliates_bp)
    app.register_blueprint(credits_bp)
    app.register_blueprint(templates_bp)

    # Inicializar sistema de agentes
    def init_agents():
        """Inicializa agentes automaticos (monitoramento de precos, auto-hibernacao, snapshot scheduler, etc)."""
        import logging
        import os
        from src.services.agent_manager import agent_manager
        from src.services.price_monitor_agent import PriceMonitorAgent
        from src.services.standby import AutoHibernationManager
        from src.services.snapshot_cleanup_agent import SnapshotCleanupAgent
        from src.services.email_report_scheduler import init_email_scheduler, shutdown_email_scheduler

        logger = logging.getLogger(__name__)
        logger.info("Inicializando agentes automaticos...")

        # ========== SNAPSHOT SCHEDULER INITIALIZATION ===        # Initialize the snapshot scheduler and restore state from database
        try:
            from src.services.snapshot_scheduler import get_snapshot_scheduler, SnapshotJobInfo
            from src.services.alert_manager import get_alert_manager
            from src.config.database import SessionLocal
            from src.models.snapshot_config import SnapshotConfig
            from datetime import datetime

            logger.info("Inicializando Snapshot Scheduler...")

            # Get AlertManager for Slack/webhook notifications
            alert_manager = get_alert_manager()

            # Define callback to persist scheduler state to database
            def on_snapshot_state_change(job_info: SnapshotJobInfo):
                """Persist scheduler state to database when it changes."""
                db = SessionLocal()
                try:
                    config = db.query(SnapshotConfig).filter(
                        SnapshotConfig.instance_id == job_info.instance_id
                    ).first()

                    if config:
                        # Update existing config with scheduler state
                        if job_info.last_snapshot_at:
                            config.last_snapshot_at = datetime.fromtimestamp(job_info.last_snapshot_at)
                        if job_info.next_snapshot_at:
                            config.next_snapshot_at = datetime.fromtimestamp(job_info.next_snapshot_at)
                        config.last_snapshot_status = job_info.last_status.value
                        config.last_snapshot_error = job_info.last_error
                        config.consecutive_failures = job_info.consecutive_failures
                        config.enabled = job_info.enabled
                        db.commit()
                        logger.debug(f"Persisted scheduler state for {job_info.instance_id}")
                except Exception as e:
                    logger.error(f"Failed to persist scheduler state for {job_info.instance_id}: {e}")
                    db.rollback()
                finally:
                    db.close()

            # Create snapshot scheduler with alert integration and state persistence callback
            snapshot_scheduler = get_snapshot_scheduler(
                alert_manager=alert_manager,
                on_state_change=on_snapshot_state_change,
            )

            # Load existing configurations from database
            db = SessionLocal()
            try:
                configs = db.query(SnapshotConfig).filter(
                    SnapshotConfig.enabled == True
                ).all()

                if configs:
                    # Convert database models to config dicts for scheduler
                    config_dicts = []
                    for config in configs:
                        config_dict = {
                            'instance_id': config.instance_id,
                            'interval_minutes': config.interval_minutes,
                            'enabled': config.enabled,
                            'consecutive_failures': config.consecutive_failures,
                        }
                        # Add timestamp fields if they exist
                        if config.last_snapshot_at:
                            config_dict['last_snapshot_at'] = config.last_snapshot_at.timestamp()
                        if config.next_snapshot_at:
                            config_dict['next_snapshot_at'] = config.next_snapshot_at.timestamp()

                        config_dicts.append(config_dict)

                    # Load configs into scheduler
                    snapshot_scheduler.load_from_configs(config_dicts)
                    logger.info(f"✓ Loaded {len(config_dicts)} snapshot configurations from database")
                else:
                    logger.info("No existing snapshot configurations found in database")

            finally:
                db.close()

            # Start the scheduler
            snapshot_scheduler.start()

            # Save reference in app for use in endpoints and shutdown
            app.snapshot_scheduler = snapshot_scheduler

            logger.info("✓ Snapshot Scheduler started successfully")

        except Exception as e:
            logger.error(f"Erro ao iniciar Snapshot Scheduler: {e}")
            import traceback
            traceback.print_exc()
        # Inicializar Email Report Scheduler (APScheduler)
        try:
            email_scheduler = init_email_scheduler()
            if email_scheduler:
                app.email_scheduler = email_scheduler
                logger.info("✓ Email Report Scheduler iniciado (APScheduler)")
        except Exception as e:
            logger.error(f"Erro ao iniciar Email Report Scheduler: {e}")

        # Carregar config do primeiro usuario para obter API key
        config = load_user_config()
        vast_api_key = None
        for user_data in config.get('users', {}).values():
            vast_api_key = user_data.get('vast_api_key')
            if vast_api_key:
                break

        if vast_api_key:
            # Registrar agente de monitoramento de precos
            try:
                agent_manager.register_agent(
                    PriceMonitorAgent,
                    vast_api_key=vast_api_key,
                    interval_minutes=30,
                    gpus_to_monitor=['RTX 4090', 'RTX 4080']
                )
                logger.info("✓ Agente de monitoramento de precos iniciado (RTX 4090, RTX 4080)")
            except Exception as e:
                logger.error(f"Erro ao iniciar agente de monitoramento: {e}")

            # Registrar agente de auto-hibernacao
            try:
                r2_endpoint = os.getenv('R2_ENDPOINT', 'https://142ed673a5cc1a9e91519c099af3d791.r2.cloudflarestorage.com')
                r2_bucket = os.getenv('R2_BUCKET', 'musetalk')
                
                # Carregar credenciais TensorDock do primeiro usuário
                tensordock_auth_id = None
                tensordock_api_token = None
                gcp_credentials = None
                
                for user_data in config.get('users', {}).values():
                    if not tensordock_auth_id and user_data.get('tensordock_auth_id'):
                        tensordock_auth_id = user_data.get('tensordock_auth_id')
                        tensordock_api_token = user_data.get('tensordock_api_token')
                    if not gcp_credentials and user_data.get('settings', {}).get('gcp_credentials'):
                        gcp_credentials = user_data.get('settings', {}).get('gcp_credentials')

                hibernation_manager = agent_manager.register_agent(
                    AutoHibernationManager,
                    vast_api_key=vast_api_key,
                    r2_endpoint=r2_endpoint,
                    r2_bucket=r2_bucket,
                    check_interval=30,
                    tensordock_auth_id=tensordock_auth_id,
                    tensordock_api_token=tensordock_api_token,
                    gcp_credentials=gcp_credentials,
                )

                # Salvar referência no app para uso nos endpoints
                app.hibernation_manager = hibernation_manager

                logger.info("✓ Agente de auto-hibernacao iniciado (check_interval=30s)")
            except Exception as e:
                logger.error(f"Erro ao iniciar agente de auto-hibernacao: {e}")

            # Inicializar CPU Standby Service (GCP)
            try:
                gcp_creds_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    'credentials', 'gcp-service-account.json'
                )
                if os.path.exists(gcp_creds_path):
                    with open(gcp_creds_path, 'r') as f:
                        gcp_credentials = json.load(f)

                    standby_service = init_standby_service(
                        vast_api_key=vast_api_key,
                        gcp_credentials=gcp_credentials,
                        config={
                            'gcp_zone': 'europe-west1-b',
                            'gcp_machine_type': 'e2-medium',
                            'gcp_disk_size': 100,
                            'sync_interval': 30,
                        }
                    )

                    # Salvar referência no app
                    app.cpu_standby_service = standby_service
                    logger.info("✓ CPU Standby service inicializado (GCP europe-west1-b)")
                else:
                    logger.warning("GCP credentials not found - CPU Standby disabled")
            except Exception as e:
                logger.error(f"Erro ao iniciar CPU Standby service: {e}")
        else:
            logger.warning("Nenhuma API key configurada - agentes nao iniciados")

        # Registrar agente de limpeza de snapshots (nao requer API key)
        try:
            agent_manager.register_agent(
                SnapshotCleanupAgent,
                interval_hours=24,  # Rodar diariamente
                dry_run=False,
                batch_size=100,
            )
            logger.info("✓ Agente de limpeza de snapshots iniciado (interval=24h)")
        except Exception as e:
            logger.error(f"Erro ao iniciar agente de limpeza de snapshots: {e}")

    # Shutdown handler para parar agentes
    import atexit
    def shutdown_agents():
        """Para todos os agentes ao desligar o servidor."""
        import logging
        from src.services.agent_manager import agent_manager
        from src.services.email_report_scheduler import shutdown_email_scheduler
        logger = logging.getLogger(__name__)
        logger.info("Parando agentes...")
        agent_manager.stop_all()

        # Stop snapshot scheduler if running
        if hasattr(app, 'snapshot_scheduler'):
            try:
                logger.info("Parando Snapshot Scheduler...")
                app.snapshot_scheduler.stop(wait=True)
                logger.info("Snapshot Scheduler parado")
            except Exception as e:
                logger.error(f"Erro ao parar Snapshot Scheduler: {e}")

        shutdown_email_scheduler()
        logger.info("Agentes parados")

    atexit.register(shutdown_agents)

    # Inicializar agentes apos criar app (mas antes de retornar)
    # Vamos fazer isso no final, antes do return
    app._init_agents = init_agents

    # Carregar config de usuarios
    def load_user_config():
        config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            settings.app.config_file
        )
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"users": {}}

    def save_user_config(config):
        config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            settings.app.config_file
        )
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

    # Usuarios carregados do config.json
    def get_users():
        config = load_user_config()
        return config.get('users', {})

    def login_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # Modo demo - bypass authentication using marcosremar@gmail.com
            if os.getenv('DEMO_MODE', 'false').lower() == 'true' or request.args.get('demo') == 'true':
                if 'user' not in session:
                    session['user'] = 'marcosremar@gmail.com'
                return f(*args, **kwargs)

            if 'user' not in session:
                if request.path.startswith('/api/'):
                    return {"error": "Nao autenticado"}, 401
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated

    @app.before_request
    def before_request():
        """Carrega dados do usuario antes de cada request"""
        if 'user' in session:
            config = load_user_config()
            user_data = config.get('users', {}).get(session['user'], {})
            g.vast_api_key = user_data.get('vast_api_key', '')
            g.user_settings = user_data.get('settings', {})

    # ========== AUTH ROUTES ==========

    @app.route('/api/auth/login', methods=['POST'])
    def api_login():
        import hashlib
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        users = get_users()
        if username in users:
            stored_hash = users[username].get('password', '')
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            if stored_hash == password_hash:
                session['user'] = username
                return {"success": True, "user": username}
        return {"error": "Usuario ou senha incorretos"}, 401

    @app.route('/api/auth/logout', methods=['POST'])
    def api_logout():
        session.pop('user', None)
        return {"success": True}

    @app.route('/api/auth/me')
    def api_me():
        if 'user' in session:
            return {"user": session['user'], "authenticated": True}
        return {"authenticated": False}

    @app.route('/api/auth/validate')
    def api_auth_validate():
        """Endpoint para nginx auth_request - valida sessao do usuario"""
        if 'user' in session:
            return '', 200  # Autenticado - nginx permite acesso
        return '', 401  # Nao autenticado - nginx bloqueia

    # ========== LATENCY ROUTES ==========

    @app.route('/api/latency')
    def measure_latency():
        """Mede latencia para endpoints representativos de cada regiao"""
        import subprocess
        import time

        # Endpoints representativos para cada regiao (servidores de CDN/cloud)
        region_endpoints = {
            'US': ['1.1.1.1', '8.8.8.8'],  # Cloudflare US, Google US
            'EU': ['1.0.0.1', '9.9.9.9'],  # Cloudflare EU, Quad9 EU
            'ASIA': ['168.63.129.16', '223.5.5.5'],  # Azure Asia, Alibaba DNS
        }

        results = {}
        for region, endpoints in region_endpoints.items():
            latencies = []
            for endpoint in endpoints:
                try:
                    # Fazer 2 pings rapidos
                    start = time.time()
                    result = subprocess.run(
                        ['ping', '-c', '2', '-W', '2', endpoint],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    elapsed = (time.time() - start) * 1000 / 2  # Media em ms

                    # Extrair tempo do output do ping
                    output = result.stdout
                    if 'time=' in output:
                        # Extrair ultimo tempo (mais preciso)
                        import re
                        times = re.findall(r'time=(\d+\.?\d*)', output)
                        if times:
                            latencies.append(float(times[-1]))
                        else:
                            latencies.append(elapsed)
                    elif result.returncode == 0:
                        latencies.append(elapsed)
                except Exception as e:
                    continue

            if latencies:
                results[region] = {
                    'latency': round(min(latencies), 1),
                    'unit': 'ms'
                }
            else:
                results[region] = {
                    'latency': None,
                    'error': 'timeout'
                }

        return jsonify(results)

    # ========== SETTINGS ROUTES ==========

    @app.route('/api/settings', methods=['GET'])
    @login_required
    def get_settings():
        config = load_user_config()
        user_data = config.get('users', {}).get(session['user'], {})
        return {
            "vast_api_key": user_data.get('vast_api_key', ''),
            "settings": user_data.get('settings', {})
        }

    @app.route('/api/settings', methods=['PUT'])
    @login_required
    def update_settings():
        data = request.get_json()
        config = load_user_config()

        if 'users' not in config:
            config['users'] = {}
        if session['user'] not in config['users']:
            config['users'][session['user']] = {}

        if 'vast_api_key' in data:
            config['users'][session['user']]['vast_api_key'] = data['vast_api_key']

        if 'settings' in data:
            config['users'][session['user']]['settings'] = data['settings']

        save_user_config(config)
        return {"success": True}

    # ========== AGENT SETTINGS ROUTES ==========

    @app.route('/api/settings/agent', methods=['GET'])
    @login_required
    def get_agent_settings():
        """Retorna configuracoes do DumontAgent"""
        config = load_user_config()
        user_data = config.get('users', {}).get(session['user'], {})
        agent_settings = user_data.get('agent_settings', {
            'sync_interval': 30,
            'keep_last': 10,
        })
        return jsonify(agent_settings)

    @app.route('/api/settings/agent', methods=['PUT'])
    @login_required
    def update_agent_settings():
        """Atualiza configuracoes do DumontAgent"""
        data = request.get_json()

        # Validacoes
        sync_interval = int(data.get('sync_interval', 30))
        keep_last = int(data.get('keep_last', 10))

        if sync_interval < 10:
            return jsonify({'error': 'Intervalo minimo e 10 segundos'}), 400
        if sync_interval > 3600:
            return jsonify({'error': 'Intervalo maximo e 1 hora (3600 segundos)'}), 400
        if keep_last < 1:
            return jsonify({'error': 'Deve manter ao menos 1 snapshot'}), 400
        if keep_last > 100:
            return jsonify({'error': 'Maximo de 100 snapshots'}), 400

        # Salvar
        config = load_user_config()
        if 'users' not in config:
            config['users'] = {}
        if session['user'] not in config['users']:
            config['users'][session['user']] = {}

        config['users'][session['user']]['agent_settings'] = {
            'sync_interval': sync_interval,
            'keep_last': keep_last,
        }
        save_user_config(config)

        return jsonify({
            'success': True,
            'agent_settings': config['users'][session['user']]['agent_settings']
        })

    # ========== METRICS ROUTES ==========

    @app.route('/metrics')
    def metrics():
        """Endpoint Prometheus para coletar metricas"""
        return generate_latest(REGISTRY), 200, {'Content-Type': CONTENT_TYPE_LATEST}

    return app


if __name__ == '__main__':
    app = create_app()
    
    # Inicializar agentes automaticos
    app._init_agents()
    
    # Executar aplicacao
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    )