#!/usr/bin/env python3
"""
SnapGPU - GPU Snapshot Manager
Aplicacao principal Flask
"""
import os
import sys
import json
from flask import Flask, g, session, redirect, url_for, request
from flask_cors import CORS
from functools import wraps

# Adiciona src ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import settings
from src.api import snapshots_bp, instances_bp


def create_app():
    """Factory function para criar a aplicacao Flask"""
    app = Flask(__name__, static_folder='web/build', static_url_path='')
    app.secret_key = settings.app.secret_key

    # CORS para desenvolvimento
    CORS(app, supports_credentials=True)

    # Registrar blueprints da API
    app.register_blueprint(snapshots_bp)
    app.register_blueprint(instances_bp)

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
            except:
                pass
        return {"users": {}}

    def save_user_config(config):
        config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            settings.app.config_file
        )
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

    # Usuarios (temporario - depois mover para DB)
    USERS = {
        "marcoslogin": {"password": "marcos123"}
    }

    def login_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
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
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if username in USERS and USERS[username]['password'] == password:
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

    # ========== FRONTEND ROUTES ==========

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            if username in USERS and USERS[username]['password'] == password:
                session['user'] = username
                return redirect('/')
        # Retorna pagina de login simples (sera substituida pelo React)
        return '''
        <!DOCTYPE html>
        <html>
        <head><title>SnapGPU Login</title>
        <style>
            body { font-family: system-ui; background: #0d1117; color: #c9d1d9; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
            .login { background: #161b22; padding: 40px; border-radius: 12px; border: 1px solid #30363d; width: 320px; }
            .logo { text-align: center; font-size: 1.8em; font-weight: 700; color: #58a6ff; margin-bottom: 24px; }
            input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #30363d; border-radius: 6px; background: #0d1117; color: #c9d1d9; box-sizing: border-box; }
            button { width: 100%; padding: 12px; background: #238636; border: none; border-radius: 6px; color: white; font-weight: 600; cursor: pointer; margin-top: 16px; }
            button:hover { background: #2ea043; }
        </style>
        </head>
        <body>
            <form class="login" method="POST">
                <div class="logo">SnapGPU</div>
                <input name="username" placeholder="Usuario" required>
                <input name="password" type="password" placeholder="Senha" required>
                <button type="submit">Entrar</button>
            </form>
        </body>
        </html>
        '''

    @app.route('/logout')
    def logout():
        session.pop('user', None)
        return redirect('/login')

    @app.route('/')
    @login_required
    def index():
        # Servir o React app quando estiver buildado
        if os.path.exists('web/build/index.html'):
            return app.send_static_file('index.html')
        # Fallback para pagina simples
        return redirect('/dashboard-legacy')

    @app.route('/dashboard-legacy')
    @login_required
    def dashboard_legacy():
        # Manter o dashboard antigo como fallback
        return '''
        <!DOCTYPE html>
        <html>
        <head><title>SnapGPU</title>
        <style>
            body { font-family: system-ui; background: #0d1117; color: #c9d1d9; margin: 0; padding: 24px; }
            .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
            .logo { font-size: 1.5em; font-weight: 700; color: #58a6ff; }
            .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin-bottom: 16px; }
            .btn { padding: 8px 16px; background: #238636; border: none; border-radius: 6px; color: white; cursor: pointer; text-decoration: none; }
            a { color: #58a6ff; }
        </style>
        </head>
        <body>
            <div class="header">
                <div class="logo">SnapGPU</div>
                <a href="/logout" class="btn" style="background: #21262d;">Sair</a>
            </div>
            <div class="card">
                <h3>Frontend em desenvolvimento</h3>
                <p>O novo frontend React esta sendo construido em <code>web/</code></p>
                <p>API disponivel em <code>/api/*</code></p>
            </div>
            <div class="card">
                <h3>Endpoints disponiveis:</h3>
                <ul>
                    <li><a href="/api/snapshots">/api/snapshots</a> - Lista snapshots</li>
                    <li><a href="/api/offers">/api/offers</a> - Lista ofertas de GPU</li>
                    <li><a href="/api/machines">/api/machines</a> - Suas instancias</li>
                    <li><a href="/api/settings">/api/settings</a> - Configuracoes</li>
                </ul>
            </div>
        </body>
        </html>
        '''

    return app


# Criar app
app = create_app()

if __name__ == '__main__':
    app.run(
        host=settings.app.host,
        port=settings.app.port,
        debug=settings.app.debug,
    )
