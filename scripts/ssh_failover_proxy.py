#!/usr/bin/env python3
"""
SSH Failover Proxy - Troca transparente GPU ↔ CPU para VS Code

Este proxy SSH permite que o VS Code (ou qualquer cliente SSH) se conecte
a um único endereço local e seja automaticamente redirecionado para a
GPU ativa ou CPU Standby quando houver failover.

Uso:
    python3 ssh_failover_proxy.py --machine-id 12345

    No VS Code, configure o Remote SSH para conectar em:
    ssh -p 2222 root@localhost

    O proxy irá:
    1. Verificar qual máquina está ativa (GPU ou CPU)
    2. Redirecionar a conexão para ela
    3. Se GPU cair, automaticamente redirecionar para CPU
    4. Mostrar notificação na conexão sobre a troca

Arquitetura:
    ┌────────────┐          ┌─────────────────┐
    │  VS Code   │  SSH     │  SSH Failover   │
    │  (local)   │ ───────► │  Proxy (:2222)  │
    └────────────┘          └────────┬────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                ▼
             ┌──────────┐     ┌──────────┐     ┌──────────┐
             │   GPU    │     │   CPU    │     │  Health  │
             │ Vast.ai  │     │ Standby  │     │ Monitor  │
             └──────────┘     └──────────┘     └──────────┘
"""

import os
import sys
import socket
import select
import threading
import time
import logging
import argparse
import json
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class TargetType(Enum):
    GPU = "gpu"
    CPU = "cpu"
    UNKNOWN = "unknown"


@dataclass
class Target:
    """Representa um target SSH (GPU ou CPU)"""
    type: TargetType
    host: str
    port: int
    healthy: bool = True
    last_check: float = 0


class SSHFailoverProxy:
    """
    Proxy SSH que automaticamente redireciona para GPU ou CPU ativa.
    """

    def __init__(
        self,
        machine_id: int,
        local_port: int = 2222,
        api_base_url: str = "http://localhost:8000",
        health_check_interval: int = 5,
        failover_threshold: int = 3,
    ):
        """
        Inicializa o proxy SSH de failover.

        Args:
            machine_id: ID da máquina no Dumont Cloud
            local_port: Porta local para escutar conexões
            api_base_url: URL base da API Dumont
            health_check_interval: Intervalo entre health checks (segundos)
            failover_threshold: Número de falhas antes de failover
        """
        self.machine_id = machine_id
        self.local_port = local_port
        self.api_base_url = api_base_url.rstrip('/')
        self.health_check_interval = health_check_interval
        self.failover_threshold = failover_threshold

        # Targets
        self.gpu_target: Optional[Target] = None
        self.cpu_target: Optional[Target] = None
        self.active_target: Optional[Target] = None
        self.previous_target: Optional[Target] = None

        # State
        self._running = False
        self._server_socket: Optional[socket.socket] = None
        self._health_thread: Optional[threading.Thread] = None
        self._connections: list = []
        self._failed_checks = 0

        # Failover callback
        self.on_failover = None  # Callback function(from_target, to_target)

    def _fetch_machine_info(self) -> bool:
        """Busca informações da máquina via API"""
        import requests

        try:
            # Buscar status da máquina
            resp = requests.get(
                f"{self.api_base_url}/api/v1/machines/{self.machine_id}",
                timeout=10
            )

            if resp.status_code != 200:
                logger.error(f"Failed to fetch machine info: {resp.status_code}")
                return False

            data = resp.json()

            # Configurar GPU target
            if data.get('ssh_host') and data.get('ssh_port'):
                self.gpu_target = Target(
                    type=TargetType.GPU,
                    host=data['ssh_host'],
                    port=int(data['ssh_port']),
                    healthy=data.get('status') == 'running'
                )
                logger.info(f"GPU target: {self.gpu_target.host}:{self.gpu_target.port}")

            # Configurar CPU Standby target
            standby = data.get('cpu_standby', {})
            if standby.get('ip'):
                self.cpu_target = Target(
                    type=TargetType.CPU,
                    host=standby['ip'],
                    port=22,
                    healthy=standby.get('status') == 'ready'
                )
                logger.info(f"CPU target: {self.cpu_target.host}:{self.cpu_target.port}")

            # Definir target ativo
            if self.gpu_target and self.gpu_target.healthy:
                self.active_target = self.gpu_target
            elif self.cpu_target and self.cpu_target.healthy:
                self.active_target = self.cpu_target

            return True

        except Exception as e:
            logger.error(f"Error fetching machine info: {e}")
            return False

    def _check_ssh_health(self, target: Target) -> bool:
        """Verifica se um target SSH está acessível"""
        if not target:
            return False

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((target.host, target.port))
            sock.close()
            return result == 0
        except Exception as e:
            logger.debug(f"Health check failed for {target.host}:{target.port}: {e}")
            return False

    def _health_check_loop(self):
        """Loop de verificação de saúde"""
        while self._running:
            try:
                # Verificar GPU
                if self.gpu_target:
                    gpu_healthy = self._check_ssh_health(self.gpu_target)
                    self.gpu_target.healthy = gpu_healthy
                    self.gpu_target.last_check = time.time()

                    if not gpu_healthy and self.active_target == self.gpu_target:
                        self._failed_checks += 1
                        logger.warning(
                            f"GPU health check failed ({self._failed_checks}/{self.failover_threshold})"
                        )

                        if self._failed_checks >= self.failover_threshold:
                            self._trigger_failover_to_cpu()
                    else:
                        self._failed_checks = 0

                # Verificar CPU
                if self.cpu_target:
                    cpu_healthy = self._check_ssh_health(self.cpu_target)
                    self.cpu_target.healthy = cpu_healthy
                    self.cpu_target.last_check = time.time()

                # Se estava em CPU e GPU voltou, fazer failback
                if (self.active_target and
                    self.active_target.type == TargetType.CPU and
                    self.gpu_target and
                    self.gpu_target.healthy):
                    self._trigger_failover_to_gpu()

            except Exception as e:
                logger.error(f"Health check error: {e}")

            time.sleep(self.health_check_interval)

    def _trigger_failover_to_cpu(self):
        """Dispara failover para CPU"""
        if not self.cpu_target or not self.cpu_target.healthy:
            logger.error("Cannot failover to CPU: not available")
            return

        logger.warning("=" * 60)
        logger.warning("FAILOVER: GPU caiu! Redirecionando para CPU Standby...")
        logger.warning("=" * 60)

        self.previous_target = self.active_target
        self.active_target = self.cpu_target
        self._failed_checks = 0

        # Notificar callback
        if self.on_failover:
            self.on_failover(self.previous_target, self.active_target)

        # Notificar conexões ativas (enviar mensagem via SSH banner se possível)
        self._notify_connections_of_failover()

    def _trigger_failover_to_gpu(self):
        """Dispara failover de volta para GPU"""
        if not self.gpu_target or not self.gpu_target.healthy:
            return

        logger.info("=" * 60)
        logger.info("RECOVERY: GPU disponível novamente! Redirecionando...")
        logger.info("=" * 60)

        self.previous_target = self.active_target
        self.active_target = self.gpu_target

        if self.on_failover:
            self.on_failover(self.previous_target, self.active_target)

        self._notify_connections_of_failover()

    def _notify_connections_of_failover(self):
        """
        Notifica conexões ativas sobre o failover.

        Para conexões SSH existentes, não há como notificar diretamente.
        Novas conexões receberão a mensagem no banner.
        Conexões existentes precisarão reconectar quando a antiga máquina cair.
        """
        from_type = self.previous_target.type.value if self.previous_target else "unknown"
        to_type = self.active_target.type.value if self.active_target else "unknown"

        logger.info(f"Failover: {from_type.upper()} → {to_type.upper()}")
        logger.info(f"Novo endpoint: {self.active_target.host}:{self.active_target.port}")

        # Salvar estado para o frontend/CLI poderem ler
        self._save_failover_state()

    def _save_failover_state(self):
        """Salva estado do failover em arquivo para outros processos lerem"""
        state_file = os.path.expanduser("~/.dumont/failover_state.json")
        os.makedirs(os.path.dirname(state_file), exist_ok=True)

        state = {
            "machine_id": self.machine_id,
            "active_target": {
                "type": self.active_target.type.value if self.active_target else None,
                "host": self.active_target.host if self.active_target else None,
                "port": self.active_target.port if self.active_target else None,
            },
            "previous_target": {
                "type": self.previous_target.type.value if self.previous_target else None,
                "host": self.previous_target.host if self.previous_target else None,
                "port": self.previous_target.port if self.previous_target else None,
            },
            "timestamp": time.time(),
            "failover_count": getattr(self, '_failover_count', 0) + 1,
        }

        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)

        logger.debug(f"Failover state saved to {state_file}")

    def _handle_connection(self, client_socket: socket.socket, client_addr: Tuple[str, int]):
        """Lida com uma conexão de cliente"""
        if not self.active_target:
            logger.error("No active target available")
            client_socket.close()
            return

        target = self.active_target
        logger.info(
            f"New connection from {client_addr[0]}:{client_addr[1]} → "
            f"{target.type.value.upper()} ({target.host}:{target.port})"
        )

        try:
            # Conectar ao target
            remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_socket.settimeout(30)
            remote_socket.connect((target.host, target.port))
            remote_socket.settimeout(None)

            # Armazenar conexão
            conn_info = {
                'client': client_socket,
                'remote': remote_socket,
                'target': target,
                'started': time.time()
            }
            self._connections.append(conn_info)

            # Proxy bidirecional
            self._proxy_data(client_socket, remote_socket)

        except socket.timeout:
            logger.error(f"Timeout connecting to {target.host}:{target.port}")
        except ConnectionRefusedError:
            logger.error(f"Connection refused by {target.host}:{target.port}")
        except Exception as e:
            logger.error(f"Connection error: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass

    def _proxy_data(self, client_socket: socket.socket, remote_socket: socket.socket):
        """Proxy bidirecional de dados entre cliente e servidor"""
        sockets = [client_socket, remote_socket]

        try:
            while self._running:
                readable, _, exceptional = select.select(sockets, [], sockets, 1)

                if exceptional:
                    break

                for sock in readable:
                    if sock is client_socket:
                        # Dados do cliente para o servidor
                        data = client_socket.recv(65536)
                        if not data:
                            return
                        remote_socket.sendall(data)
                    else:
                        # Dados do servidor para o cliente
                        data = remote_socket.recv(65536)
                        if not data:
                            return
                        client_socket.sendall(data)

        except (ConnectionResetError, BrokenPipeError):
            pass
        except Exception as e:
            logger.debug(f"Proxy error: {e}")
        finally:
            try:
                remote_socket.close()
            except:
                pass

    def start(self):
        """Inicia o proxy"""
        logger.info("=" * 60)
        logger.info("SSH Failover Proxy - Dumont Cloud")
        logger.info("=" * 60)

        # Buscar informações da máquina
        if not self._fetch_machine_info():
            logger.error("Failed to fetch machine info. Retrying...")
            # Tentar novamente com configuração manual se disponível

        if not self.active_target:
            logger.warning("No active target found. Will retry on connection.")
        else:
            logger.info(f"Active target: {self.active_target.type.value.upper()} "
                       f"({self.active_target.host}:{self.active_target.port})")

        self._running = True

        # Iniciar health check
        self._health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self._health_thread.start()

        # Criar socket do servidor
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind(('0.0.0.0', self.local_port))
        self._server_socket.listen(5)

        logger.info(f"Listening on port {self.local_port}")
        logger.info(f"Configure VS Code SSH to connect to: ssh -p {self.local_port} root@localhost")
        logger.info("-" * 60)

        try:
            while self._running:
                try:
                    client_socket, client_addr = self._server_socket.accept()

                    # Buscar info atualizada se não temos target
                    if not self.active_target:
                        self._fetch_machine_info()

                    # Handler em thread separada
                    thread = threading.Thread(
                        target=self._handle_connection,
                        args=(client_socket, client_addr),
                        daemon=True
                    )
                    thread.start()

                except socket.timeout:
                    continue

        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.stop()

    def stop(self):
        """Para o proxy"""
        self._running = False

        if self._server_socket:
            self._server_socket.close()

        if self._health_thread:
            self._health_thread.join(timeout=5)

        # Fechar conexões
        for conn in self._connections:
            try:
                conn['client'].close()
            except:
                pass
            try:
                conn['remote'].close()
            except:
                pass

        logger.info("Proxy stopped")

    def get_status(self) -> Dict[str, Any]:
        """Retorna status do proxy"""
        return {
            "running": self._running,
            "local_port": self.local_port,
            "machine_id": self.machine_id,
            "active_target": {
                "type": self.active_target.type.value if self.active_target else None,
                "host": self.active_target.host if self.active_target else None,
                "port": self.active_target.port if self.active_target else None,
                "healthy": self.active_target.healthy if self.active_target else False,
            } if self.active_target else None,
            "gpu_target": {
                "host": self.gpu_target.host if self.gpu_target else None,
                "port": self.gpu_target.port if self.gpu_target else None,
                "healthy": self.gpu_target.healthy if self.gpu_target else False,
            } if self.gpu_target else None,
            "cpu_target": {
                "host": self.cpu_target.host if self.cpu_target else None,
                "port": self.cpu_target.port if self.cpu_target else None,
                "healthy": self.cpu_target.healthy if self.cpu_target else False,
            } if self.cpu_target else None,
            "connections_count": len(self._connections),
            "failed_checks": self._failed_checks,
        }


def main():
    parser = argparse.ArgumentParser(
        description="SSH Failover Proxy para VS Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Conectar a uma máquina do Dumont Cloud
  python3 ssh_failover_proxy.py --machine-id 12345

  # Configurar targets manualmente
  python3 ssh_failover_proxy.py --gpu-host ssh4.vast.ai --gpu-port 38784 \\
                                  --cpu-host 35.240.1.1 --cpu-port 22

  # No VS Code, configure Remote SSH para:
  ssh -p 2222 root@localhost
"""
    )

    parser.add_argument(
        '--machine-id',
        type=int,
        help='ID da máquina no Dumont Cloud'
    )
    parser.add_argument(
        '--gpu-host',
        help='Host SSH da GPU (ex: ssh4.vast.ai)'
    )
    parser.add_argument(
        '--gpu-port',
        type=int,
        default=22,
        help='Porta SSH da GPU'
    )
    parser.add_argument(
        '--cpu-host',
        help='Host SSH da CPU Standby (ex: 35.240.1.1)'
    )
    parser.add_argument(
        '--cpu-port',
        type=int,
        default=22,
        help='Porta SSH da CPU Standby'
    )
    parser.add_argument(
        '--local-port',
        type=int,
        default=2222,
        help='Porta local para escutar (default: 2222)'
    )
    parser.add_argument(
        '--api-url',
        default='http://localhost:8000',
        help='URL da API Dumont Cloud'
    )
    parser.add_argument(
        '--health-interval',
        type=int,
        default=5,
        help='Intervalo de health check em segundos'
    )
    parser.add_argument(
        '--failover-threshold',
        type=int,
        default=3,
        help='Número de falhas antes de failover'
    )

    args = parser.parse_args()

    # Criar proxy
    proxy = SSHFailoverProxy(
        machine_id=args.machine_id or 0,
        local_port=args.local_port,
        api_base_url=args.api_url,
        health_check_interval=args.health_interval,
        failover_threshold=args.failover_threshold,
    )

    # Configurar targets manuais se fornecidos
    if args.gpu_host:
        proxy.gpu_target = Target(
            type=TargetType.GPU,
            host=args.gpu_host,
            port=args.gpu_port,
            healthy=True
        )
        proxy.active_target = proxy.gpu_target
        logger.info(f"GPU target configured: {args.gpu_host}:{args.gpu_port}")

    if args.cpu_host:
        proxy.cpu_target = Target(
            type=TargetType.CPU,
            host=args.cpu_host,
            port=args.cpu_port,
            healthy=True
        )
        logger.info(f"CPU target configured: {args.cpu_host}:{args.cpu_port}")

    # Callback de failover
    def on_failover(from_target, to_target):
        from_str = f"{from_target.type.value.upper()}" if from_target else "N/A"
        to_str = f"{to_target.type.value.upper()}" if to_target else "N/A"

        print("\n" + "=" * 60)
        print(f"  FAILOVER: {from_str} → {to_str}")
        if to_target:
            print(f"  Novo endpoint: {to_target.host}:{to_target.port}")
        print("  Reconecte no VS Code se necessário.")
        print("=" * 60 + "\n")

    proxy.on_failover = on_failover

    # Iniciar
    proxy.start()


if __name__ == '__main__':
    main()
