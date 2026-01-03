#!/usr/bin/env python3
"""
Teste do Widget de Failover no code-server real.

Este script:
1. Conecta à instância GPU na VAST.ai
2. Instala o widget de failover via Nginx
3. Testa se o widget aparece no code-server

Uso:
    python3 test_real_failover_widget.py --instance-id 12345

Ou com host/port direto:
    python3 test_real_failover_widget.py --host 69.176.92.110 --port 21858
"""

import argparse
import os
import sys
import time
import requests
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# Colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_header(text):
    print(f"\n{BOLD}{BLUE}{'=' * 60}{RESET}")
    print(f"{BOLD}{BLUE}  {text}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 60}{RESET}\n")


def print_step(num, text):
    print(f"{BOLD}[{num}]{RESET} {text}")


def print_success(text):
    print(f"  {GREEN}✓{RESET} {text}")


def print_warning(text):
    print(f"  {YELLOW}⚠{RESET} {text}")


def print_error(text):
    print(f"  {RED}✗{RESET} {text}")


def print_info(text):
    print(f"  {BLUE}ℹ{RESET} {text}")


def get_instance_info(instance_id: int) -> dict:
    """Obtém informações da instância VAST.ai"""
    api_key = os.getenv("VAST_API_KEY")
    if not api_key:
        raise ValueError("VAST_API_KEY não configurada")

    headers = {"Authorization": f"Bearer {api_key}"}
    resp = requests.get(
        "https://console.vast.ai/api/v0/instances/",
        headers=headers,
        timeout=30
    )
    resp.raise_for_status()

    for instance in resp.json().get("instances", []):
        if instance["id"] == instance_id:
            return {
                "id": instance["id"],
                "host": instance.get("ssh_host") or instance.get("public_ipaddr"),
                "port": instance.get("ssh_port"),
                "status": instance.get("actual_status"),
                "gpu_name": instance.get("gpu_name", "GPU"),
            }

    raise ValueError(f"Instância {instance_id} não encontrada")


def test_ssh_connection(host: str, port: int) -> bool:
    """Testa conexão SSH"""
    import subprocess
    try:
        result = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10",
             "-o", "BatchMode=yes", "-p", str(port), f"root@{host}", "echo ok"],
            capture_output=True,
            timeout=15
        )
        return result.returncode == 0
    except:
        return False


def main():
    parser = argparse.ArgumentParser(description="Teste do Widget de Failover")
    parser.add_argument("--instance-id", type=int, help="ID da instância VAST.ai")
    parser.add_argument("--host", help="SSH host direto")
    parser.add_argument("--port", type=int, help="SSH port direto")
    parser.add_argument("--codeserver-port", type=int, default=8080, help="Porta do code-server")
    parser.add_argument("--nginx-port", type=int, default=80, help="Porta do Nginx")
    parser.add_argument("--skip-install", action="store_true", help="Pular instalação")

    args = parser.parse_args()

    print_header("Teste do Widget de Failover - code-server Real")

    # Obter informações da instância
    if args.instance_id:
        print_step(1, f"Obtendo informações da instância {args.instance_id}...")
        try:
            info = get_instance_info(args.instance_id)
            host = info["host"]
            port = info["port"]
            gpu_name = info["gpu_name"]
            print_success(f"Instância encontrada: {host}:{port}")
            print_info(f"GPU: {gpu_name}")
            print_info(f"Status: {info['status']}")
        except Exception as e:
            print_error(f"Erro: {e}")
            return 1
    elif args.host and args.port:
        host = args.host
        port = args.port
        gpu_name = "GPU"
        print_step(1, f"Usando host direto: {host}:{port}")
    else:
        print_error("Forneça --instance-id ou --host e --port")
        return 1

    # Testar conexão SSH
    print_step(2, "Testando conexão SSH...")
    if test_ssh_connection(host, port):
        print_success("Conexão SSH OK")
    else:
        print_error("Falha na conexão SSH")
        print_info("Verifique se a instância está rodando e se você tem a chave SSH correta")
        return 1

    # Instalar widget
    if not args.skip_install:
        print_step(3, "Instalando widget de failover...")
        try:
            from src.services.codeserver_failover_widget import setup_failover_widget

            result = setup_failover_widget(
                ssh_host=host,
                ssh_port=port,
                codeserver_port=args.codeserver_port,
                nginx_port=args.nginx_port,
                gpu_name=gpu_name,
                cpu_name="CPU Standby",
            )

            if result.get("success"):
                print_success("Widget instalado com sucesso!")
                for step in result.get("steps", []):
                    status = "✓" if step.get("success") else "✗"
                    print_info(f"{status} {step.get('step')}: {step.get('message', step.get('error', ''))}")
            else:
                print_warning(f"Instalação parcial: {result.get('error', 'Erro desconhecido')}")
                for step in result.get("steps", []):
                    status = "✓" if step.get("success") else "✗"
                    print_info(f"{status} {step.get('step')}")

        except Exception as e:
            print_error(f"Erro na instalação: {e}")
            import traceback
            traceback.print_exc()
    else:
        print_step(3, "Instalação pulada (--skip-install)")

    # Verificar se está funcionando
    print_step(4, "Verificando widget...")
    time.sleep(3)

    # Tentar acessar via Nginx
    try:
        # Primeiro tenta a porta mapeada da VAST.ai
        # A VAST.ai mapeia portas internas para portas externas
        urls_to_try = [
            f"http://{host}:{args.nginx_port}/dumont-status/api",
            f"http://{host}:{args.codeserver_port}/",
        ]

        widget_working = False
        for url in urls_to_try:
            try:
                print_info(f"Tentando {url}...")
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    print_success(f"URL acessível: {url}")
                    if "dumont-status" in url:
                        widget_working = True
                        break
            except Exception as e:
                print_info(f"Não acessível: {e}")

        if widget_working:
            print_success("Widget de status respondendo!")
        else:
            print_warning("Widget pode não estar acessível externamente")
            print_info("A VAST.ai pode bloquear a porta 80")
            print_info(f"Tente acessar via SSH tunnel: ssh -L 8080:localhost:80 -p {port} root@{host}")

    except Exception as e:
        print_warning(f"Não foi possível verificar externamente: {e}")

    # Instruções finais
    print_header("INSTRUÇÕES")
    print(f"""
Para acessar o code-server com widget de failover:

{BOLD}Opção 1: SSH Tunnel (recomendado){RESET}
  ssh -L 8080:localhost:{args.nginx_port} -p {port} root@{host}
  Depois acesse: http://localhost:8080

{BOLD}Opção 2: Porta direta (se VAST permitir){RESET}
  http://{host}:{args.nginx_port}

{BOLD}O que você verá:{RESET}
  - Widget verde "GPU" no canto superior direito
  - Contagem de syncs quando houver sincronização
  - Mudança para azul "CPU Standby" em caso de failover
  - Notificação quando ocorrer troca de máquina

{BOLD}Para testar o failover manualmente:{RESET}
  ssh -p {port} root@{host}
  echo '{{"mode": "cpu"}}' > /tmp/dumont_status.json
  # O widget deve mudar para azul

  # Para restaurar:
  echo '{{"mode": "gpu"}}' > /tmp/dumont_status.json
    """)

    return 0


if __name__ == "__main__":
    sys.exit(main())
