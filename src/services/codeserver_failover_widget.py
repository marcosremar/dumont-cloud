"""
Service para injetar widget de failover no code-server via Nginx.

Este serviço:
1. Instala Nginx na instância GPU
2. Configura Nginx como proxy reverso para code-server
3. Injeta widget de status no canto superior direito
4. Roda servidor de status local para comunicação com Dumont API

O widget mostra:
- GPU (verde) quando conectado à GPU
- CPU Standby (azul) quando em failover
- Failover... (amarelo) durante transição
- Notificações de troca de máquina
"""

import logging
import subprocess
import time
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FailoverWidgetConfig:
    """Configuração do widget de failover"""
    codeserver_port: int = 8080
    nginx_port: int = 80
    status_api_port: int = 8081
    dumont_api_url: str = "http://localhost:8000"
    machine_id: str = ""
    gpu_name: str = "GPU"
    cpu_name: str = "CPU Standby"


# CSS do widget (minificado)
WIDGET_CSS = """
#dumont-failover-widget{position:fixed;top:10px;right:10px;z-index:999999;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:12px;user-select:none}
.dumont-widget-inner{display:flex;align-items:center;gap:8px;background:rgba(30,30,30,.95);border:1px solid rgba(255,255,255,.1);border-radius:8px;padding:6px 12px;box-shadow:0 4px 12px rgba(0,0,0,.3);backdrop-filter:blur(8px)}
.dumont-status-indicator{display:flex;align-items:center;gap:6px}
.dumont-status-dot{width:8px;height:8px;border-radius:50%;animation:dumont-pulse 2s infinite}
.dumont-status-gpu{background:#22c55e;box-shadow:0 0 8px rgba(34,197,94,.6)}
.dumont-status-cpu{background:#3b82f6;box-shadow:0 0 8px rgba(59,130,246,.6)}
.dumont-status-failover{background:#eab308;box-shadow:0 0 8px rgba(234,179,8,.6);animation:dumont-blink .5s infinite}
.dumont-status-warning{background:#f97316!important;box-shadow:0 0 8px rgba(249,115,22,.6)!important}
.dumont-status-text{color:#e5e5e5;font-weight:500;white-space:nowrap}
.dumont-status-details{display:none;padding-left:8px;border-left:1px solid rgba(255,255,255,.1)}
.dumont-sync-count{color:#9ca3af;font-size:11px}
#dumont-failover-widget.dumont-gpu .dumont-widget-inner{border-color:rgba(34,197,94,.3)}
#dumont-failover-widget.dumont-cpu .dumont-widget-inner{border-color:rgba(59,130,246,.3)}
#dumont-failover-widget.dumont-failover .dumont-widget-inner{border-color:rgba(234,179,8,.5);background:rgba(40,35,20,.95)}
.dumont-notification{margin-top:8px;max-width:300px;animation:dumont-slideIn .3s ease}
.dumont-notification-content{display:flex;align-items:flex-start;gap:8px;padding:10px 14px;background:rgba(30,30,30,.95);border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,.4)}
.dumont-notification-warning .dumont-notification-content{border-left:3px solid #eab308;background:rgba(40,35,20,.95)}
.dumont-notification-error .dumont-notification-content{border-left:3px solid #ef4444;background:rgba(40,20,20,.95)}
.dumont-notification-success .dumont-notification-content{border-left:3px solid #22c55e;background:rgba(20,35,25,.95)}
.dumont-notification-icon{font-size:16px;line-height:1}
.dumont-notification-text{color:#e5e5e5;font-size:13px;line-height:1.4}
@keyframes dumont-pulse{0%,100%{opacity:1}50%{opacity:.6}}
@keyframes dumont-blink{0%,100%{opacity:1}50%{opacity:.3}}
@keyframes dumont-slideIn{from{opacity:0;transform:translateY(-10px)}to{opacity:1;transform:translateY(0)}}
"""

# JavaScript do widget (minificado)
WIDGET_JS = """
(function(){
'use strict';
const POLL_INTERVAL=2000,API_ENDPOINT='/dumont-status/api';
let currentState={mode:'gpu',gpuName:'GPU_NAME_PLACEHOLDER',cpuName:'CPU_NAME_PLACEHOLDER',lastSync:null,syncCount:0,healthy:true};
function createWidget(){
const c=document.createElement('div');c.id='dumont-failover-widget';
c.innerHTML='<div class="dumont-widget-inner"><div class="dumont-status-indicator"><span class="dumont-status-dot"></span><span class="dumont-status-text">GPU</span></div><div class="dumont-status-details"><span class="dumont-sync-count">0 syncs</span></div></div><div class="dumont-notification" style="display:none"><div class="dumont-notification-content"><span class="dumont-notification-icon">⚠️</span><span class="dumont-notification-text"></span></div></div>';
document.body.appendChild(c);return c}
function updateWidget(s){
const w=document.getElementById('dumont-failover-widget');if(!w)return;
const d=w.querySelector('.dumont-status-dot'),t=w.querySelector('.dumont-status-text'),sc=w.querySelector('.dumont-sync-count');
switch(s.mode){
case'gpu':d.className='dumont-status-dot dumont-status-gpu';t.textContent=s.gpuName||'GPU';w.classList.remove('dumont-failover','dumont-cpu');w.classList.add('dumont-gpu');break;
case'cpu':d.className='dumont-status-dot dumont-status-cpu';t.textContent=s.cpuName||'CPU Standby';w.classList.remove('dumont-failover','dumont-gpu');w.classList.add('dumont-cpu');break;
case'failover':d.className='dumont-status-dot dumont-status-failover';t.textContent='Failover...';w.classList.remove('dumont-gpu','dumont-cpu');w.classList.add('dumont-failover');break}
if(s.syncCount>0){sc.textContent=s.syncCount+' syncs';w.querySelector('.dumont-status-details').style.display='block'}
s.healthy?d.classList.remove('dumont-status-warning'):d.classList.add('dumont-status-warning')}
function showNotification(m,type='info'){
const w=document.getElementById('dumont-failover-widget');if(!w)return;
const n=w.querySelector('.dumont-notification'),nt=w.querySelector('.dumont-notification-text'),ni=w.querySelector('.dumont-notification-icon');
switch(type){case'warning':ni.textContent='⚠️';n.className='dumont-notification dumont-notification-warning';break;case'error':ni.textContent='❌';n.className='dumont-notification dumont-notification-error';break;case'success':ni.textContent='✅';n.className='dumont-notification dumont-notification-success';break;default:ni.textContent='ℹ️';n.className='dumont-notification dumont-notification-info'}
nt.textContent=m;n.style.display='block';
if(type!=='error')setTimeout(()=>{n.style.display='none'},10000)}
function handleFailover(o,n){
console.log('[Dumont] Failover:',o.mode,'->',n.mode);
if(o.mode==='gpu'&&n.mode==='cpu')showNotification('GPU falhou! Trocando para '+n.cpuName+'. Seus arquivos estão salvos.','warning');
else if(o.mode==='cpu'&&n.mode==='gpu')showNotification('Nova GPU provisionada! Voltando para '+n.gpuName+'.','success')}
async function pollStatus(){
try{const r=await fetch(API_ENDPOINT);if(!r.ok)throw new Error('HTTP '+r.status);
const d=await r.json(),ns={mode:d.mode||'gpu',gpuName:d.gpu_name||'GPU',cpuName:d.cpu_name||'CPU Standby',lastSync:d.last_sync,syncCount:d.sync_count||0,healthy:d.healthy!==false};
if(currentState.mode!==ns.mode)handleFailover(currentState,ns);currentState=ns;updateWidget(currentState)}
catch(e){console.warn('[Dumont] Status poll failed:',e.message);currentState.healthy=false;updateWidget(currentState)}}
function init(){
if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',init);return}
console.log('[Dumont] Widget init');createWidget();updateWidget(currentState);pollStatus();setInterval(pollStatus,POLL_INTERVAL);
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')pollStatus()})}
init()})();
"""


class FailoverWidgetService:
    """
    Serviço para instalar e configurar o widget de failover no code-server.

    Usa Nginx como proxy reverso para injetar HTML/CSS/JS no code-server.
    """

    def __init__(self, ssh_host: str, ssh_port: int, ssh_user: str = "root"):
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.ssh_user = ssh_user

    def _ssh_cmd(self, command: str, timeout: int = 60) -> Tuple[bool, str]:
        """Executa comando via SSH"""
        import os
        ssh_key = os.path.expanduser("~/.ssh/id_rsa")
        ssh_command = [
            "ssh",
            "-i", ssh_key,
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "LogLevel=ERROR",
            "-o", f"ConnectTimeout={min(timeout, 30)}",
            "-p", str(self.ssh_port),
            f"{self.ssh_user}@{self.ssh_host}",
            command
        ]

        try:
            result = subprocess.run(
                ssh_command,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)

    def install_nginx(self) -> Dict[str, Any]:
        """Instala Nginx na instância"""
        logger.info("Instalando Nginx...")

        # Instalar Nginx
        success, output = self._ssh_cmd(
            "apt-get update -qq && apt-get install -y -qq nginx && echo 'NGINX_INSTALLED'",
            timeout=120
        )

        if not success or "NGINX_INSTALLED" not in output:
            return {"success": False, "error": f"Falha ao instalar Nginx: {output}"}

        return {"success": True, "message": "Nginx instalado"}

    def configure_nginx(self, config: FailoverWidgetConfig) -> Dict[str, Any]:
        """Configura Nginx como proxy reverso com injeção de widget"""
        logger.info("Configurando Nginx...")

        # Criar diretório para assets do widget
        self._ssh_cmd("mkdir -p /var/www/dumont-status", timeout=10)

        # Criar CSS do widget
        css_escaped = WIDGET_CSS.replace("'", "'\\''")
        self._ssh_cmd(f"echo '{css_escaped}' > /var/www/dumont-status/widget.css", timeout=10)

        # Criar JS do widget (substituir placeholders)
        js_content = WIDGET_JS.replace("GPU_NAME_PLACEHOLDER", config.gpu_name)
        js_content = js_content.replace("CPU_NAME_PLACEHOLDER", config.cpu_name)
        js_escaped = js_content.replace("'", "'\\''")
        self._ssh_cmd(f"echo '{js_escaped}' > /var/www/dumont-status/widget.js", timeout=10)

        # Criar configuração do Nginx
        nginx_config = f"""
server {{
    listen {config.nginx_port};
    server_name _;

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/javascript application/json;

    # Widget assets
    location /dumont-status/ {{
        alias /var/www/dumont-status/;
        expires 1h;
    }}

    # Status API proxy
    location /dumont-status/api {{
        proxy_pass http://127.0.0.1:{config.status_api_port}/status;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }}

    # Code-server proxy com injeção de widget
    location / {{
        # Injetar CSS e JS antes de </head>
        sub_filter '</head>' '<link rel="stylesheet" href="/dumont-status/widget.css"><script src="/dumont-status/widget.js"></script></head>';
        sub_filter_once on;
        sub_filter_types text/html;

        proxy_pass http://127.0.0.1:{config.codeserver_port};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # Long timeouts for WebSocket
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;

        # Disable buffering for real-time
        proxy_buffering off;
    }}
}}
"""
        # Escrever config do Nginx
        nginx_escaped = nginx_config.replace("'", "'\\''")
        success, output = self._ssh_cmd(
            f"echo '{nginx_escaped}' > /etc/nginx/sites-available/dumont-codeserver && "
            "ln -sf /etc/nginx/sites-available/dumont-codeserver /etc/nginx/sites-enabled/ && "
            "rm -f /etc/nginx/sites-enabled/default && "
            "nginx -t && "
            "echo 'NGINX_CONFIGURED'",
            timeout=30
        )

        if "NGINX_CONFIGURED" not in output:
            return {"success": False, "error": f"Falha na configuração do Nginx: {output}"}

        return {"success": True, "message": "Nginx configurado"}

    def install_status_server(self, config: FailoverWidgetConfig) -> Dict[str, Any]:
        """Instala e inicia o servidor de status local"""
        logger.info("Instalando servidor de status...")

        # Script Python do servidor de status
        status_server_script = f'''
#!/usr/bin/env python3
"""Dumont Status Server - monitors GPU health and serves status API"""
import json
import os
import subprocess
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

STATE = {{"mode": "gpu", "gpu_name": "{config.gpu_name}", "cpu_name": "{config.cpu_name}",
         "healthy": True, "sync_count": 0, "last_sync": None}}
STATE_FILE = "/tmp/dumont_status.json"

def save_state():
    with open(STATE_FILE, "w") as f:
        json.dump(STATE, f)

def load_state():
    global STATE
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            STATE = json.load(f)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def do_GET(self):
        if self.path == "/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(STATE).encode())
        else:
            self.send_response(404)
            self.end_headers()

def check_gpu():
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                          capture_output=True, text=True, timeout=5)
        return r.returncode == 0
    except:
        return False

def monitor():
    failures = 0
    while True:
        if check_gpu():
            failures = 0
            STATE["healthy"] = True
        else:
            failures += 1
            if failures >= 3:
                STATE["healthy"] = False
        save_state()
        time.sleep(5)

if __name__ == "__main__":
    load_state()
    threading.Thread(target=monitor, daemon=True).start()
    HTTPServer(("0.0.0.0", {config.status_api_port}), Handler).serve_forever()
'''

        # Escrever script
        script_escaped = status_server_script.replace("'", "'\\''").replace("$", "\\$")
        success, output = self._ssh_cmd(
            f"cat > /opt/dumont-status-server.py << 'SCRIPT_EOF'\n{status_server_script}\nSCRIPT_EOF\n"
            "chmod +x /opt/dumont-status-server.py && echo 'SCRIPT_CREATED'",
            timeout=30
        )

        if "SCRIPT_CREATED" not in output:
            return {"success": False, "error": f"Falha ao criar script: {output}"}

        # Criar systemd service
        systemd_service = f"""
[Unit]
Description=Dumont Status Server
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/dumont-status-server.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""
        service_escaped = systemd_service.replace("'", "'\\''")
        success, output = self._ssh_cmd(
            f"echo '{service_escaped}' > /etc/systemd/system/dumont-status.service && "
            "systemctl daemon-reload && "
            "systemctl enable dumont-status && "
            "systemctl start dumont-status && "
            "echo 'SERVICE_STARTED'",
            timeout=30
        )

        if "SERVICE_STARTED" not in output:
            # Tentar iniciar manualmente
            self._ssh_cmd(
                "nohup python3 /opt/dumont-status-server.py > /tmp/dumont-status.log 2>&1 &",
                timeout=10
            )

        return {"success": True, "message": "Servidor de status instalado"}

    def start_services(self) -> Dict[str, Any]:
        """Inicia Nginx e servidor de status"""
        logger.info("Iniciando serviços...")

        # Iniciar/reiniciar Nginx
        success, output = self._ssh_cmd(
            "systemctl restart nginx || service nginx restart || nginx -s reload && echo 'NGINX_STARTED'",
            timeout=30
        )

        if "NGINX_STARTED" not in output:
            return {"success": False, "error": f"Falha ao iniciar Nginx: {output}"}

        # Verificar status
        success, output = self._ssh_cmd(
            f"curl -s http://localhost/dumont-status/api 2>/dev/null | grep mode && echo 'STATUS_OK' || echo 'STATUS_FAIL'",
            timeout=10
        )

        if "STATUS_OK" in output:
            return {"success": True, "message": "Serviços iniciados"}

        return {"success": True, "message": "Nginx iniciado (status server pode demorar)"}

    def setup_full(self, config: Optional[FailoverWidgetConfig] = None) -> Dict[str, Any]:
        """
        Instalação completa do widget de failover no code-server.

        Etapas:
        1. Instalar Nginx
        2. Configurar Nginx como proxy
        3. Instalar servidor de status
        4. Iniciar serviços
        """
        config = config or FailoverWidgetConfig()
        results = {"steps": [], "success": False}

        # 1. Instalar Nginx
        nginx_result = self.install_nginx()
        results["steps"].append({"step": "install_nginx", **nginx_result})
        if not nginx_result.get("success"):
            results["error"] = "Falha ao instalar Nginx"
            return results

        # 2. Configurar Nginx
        config_result = self.configure_nginx(config)
        results["steps"].append({"step": "configure_nginx", **config_result})
        if not config_result.get("success"):
            results["error"] = "Falha ao configurar Nginx"
            return results

        # 3. Instalar servidor de status
        status_result = self.install_status_server(config)
        results["steps"].append({"step": "install_status_server", **status_result})
        if not status_result.get("success"):
            results["error"] = "Falha ao instalar servidor de status"
            return results

        # 4. Iniciar serviços
        start_result = self.start_services()
        results["steps"].append({"step": "start_services", **start_result})

        results["success"] = True
        results["message"] = f"Widget de failover instalado. Acesse via porta {config.nginx_port}"
        results["url"] = f"http://{self.ssh_host}:{config.nginx_port}/"

        return results


def setup_failover_widget(
    ssh_host: str,
    ssh_port: int,
    ssh_user: str = "root",
    codeserver_port: int = 8080,
    nginx_port: int = 80,
    gpu_name: str = "GPU",
    cpu_name: str = "CPU Standby",
) -> Dict[str, Any]:
    """
    Função helper para setup rápido do widget de failover.

    Args:
        ssh_host: IP da instância
        ssh_port: Porta SSH
        ssh_user: Usuário SSH (default: root)
        codeserver_port: Porta do code-server (default: 8080)
        nginx_port: Porta do Nginx (default: 80)
        gpu_name: Nome da GPU para exibir
        cpu_name: Nome da CPU Standby para exibir

    Returns:
        Dict com resultado da instalação
    """
    config = FailoverWidgetConfig(
        codeserver_port=codeserver_port,
        nginx_port=nginx_port,
        gpu_name=gpu_name,
        cpu_name=cpu_name,
    )

    service = FailoverWidgetService(ssh_host, ssh_port, ssh_user)
    return service.setup_full(config)
