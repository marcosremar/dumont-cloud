#!/usr/bin/env python3
"""
Teste REAL do Sistema de Failover Automático
Usa os serviços reais do Dumont Cloud (não CLI)
"""
import os
import sys
import json
import time
import subprocess
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Carregar credenciais
CREDS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials', 'gcp-service-account.json')
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')


def load_vast_api_key():
    """Carrega API key do Vast.ai do config"""
    try:
        with open(CONFIG_PATH) as f:
            config = json.load(f)
        for user_data in config.get('users', {}).values():
            key = user_data.get('vast_api_key')
            if key:
                return key
    except:
        pass
    return os.getenv('VAST_API_KEY')


def load_gcp_credentials():
    """Carrega credenciais GCP"""
    with open(CREDS_PATH) as f:
        return json.load(f)


def run_cmd(cmd, timeout=60):
    """Executa comando bash"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


class RealFailoverTest:
    def __init__(self):
        self.vast_api_key = load_vast_api_key()
        self.gcp_credentials = load_gcp_credentials()
        self.gpu_instance_id = None
        self.cpu_instance = None
        self.service = None
        self.results = {'passed': 0, 'failed': 0, 'tests': []}

    def log_result(self, test_name, passed, detail="", duration=0):
        icon = "✅" if passed else "❌"
        logger.info(f"{icon} {test_name} ({duration:.1f}s)")
        if detail:
            logger.info(f"   └─ {detail}")
        self.results['tests'].append({'name': test_name, 'passed': passed, 'detail': detail})
        if passed:
            self.results['passed'] += 1
        else:
            self.results['failed'] += 1
        return passed

    def test_01_init_service(self):
        """Inicializa CPUStandbyService"""
        start = time.time()
        try:
            from src.services.cpu_standby_service import CPUStandbyService, CPUStandbyConfig

            config = CPUStandbyConfig(
                gcp_zone='europe-west1-b',
                gcp_machine_type='e2-small',
                gcp_disk_size=20,
                gcp_spot=True,
                sync_interval_seconds=30,
                health_check_interval=10,
                failover_threshold=3,
                auto_failover=True,
                auto_recovery=True,
                gpu_min_ram=8,
                gpu_max_price=0.50,
            )

            self.service = CPUStandbyService(
                vast_api_key=self.vast_api_key,
                gcp_credentials=self.gcp_credentials,
                config=config
            )

            return self.log_result(
                "Inicializar CPUStandbyService",
                True,
                f"Config: zone={config.gcp_zone}, auto_failover={config.auto_failover}",
                time.time() - start
            )
        except Exception as e:
            return self.log_result("Inicializar CPUStandbyService", False, str(e), time.time() - start)

    def test_02_provision_cpu_standby(self):
        """Provisiona CPU standby no GCP"""
        if not self.service:
            return self.log_result("Provisionar CPU standby", False, "Sem serviço")

        start = time.time()
        try:
            instance_id = self.service.provision_cpu_standby("test")

            if instance_id and self.service.cpu_instance:
                self.cpu_instance = self.service.cpu_instance
                return self.log_result(
                    "Provisionar CPU standby",
                    True,
                    f"IP: {self.cpu_instance.get('external_ip')} | Nome: {self.cpu_instance.get('name')}",
                    time.time() - start
                )
            else:
                return self.log_result("Provisionar CPU standby", False, "Falha ao criar VM", time.time() - start)
        except Exception as e:
            return self.log_result("Provisionar CPU standby", False, str(e)[:100], time.time() - start)

    def test_03_create_gpu(self):
        """Cria instância GPU no Vast.ai"""
        start = time.time()
        try:
            # Buscar GPU barata
            success, output = run_cmd(
                "vastai search offers 'rentable=true gpu_ram>=8 dph<0.40' --raw 2>/dev/null | "
                "jq -r '[.[] | select(.geolocation | test(\"TH|VN|JP\"))] | sort_by(.dph_total) | .[0].id // empty'"
            )

            offer_id = output.strip()
            if not offer_id:
                # Fallback
                success, output = run_cmd(
                    "vastai search offers 'rentable=true gpu_ram>=8 dph<0.40' --raw 2>/dev/null | jq -r 'sort_by(.dph_total) | .[0].id'"
                )
                offer_id = output.strip()

            if not offer_id or offer_id == "null":
                return self.log_result("Criar GPU", False, "Nenhuma oferta", time.time() - start)

            # Criar
            success, output = run_cmd(
                f"vastai create instance {offer_id} --image pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime --disk 20 --ssh --raw"
            )

            result = json.loads(output)
            if result.get('success'):
                self.gpu_instance_id = result.get('new_contract')
                return self.log_result("Criar GPU", True, f"ID: {self.gpu_instance_id}", time.time() - start)

            return self.log_result("Criar GPU", False, output[:100], time.time() - start)
        except Exception as e:
            return self.log_result("Criar GPU", False, str(e)[:100], time.time() - start)

    def test_04_wait_gpu_ready(self):
        """Aguarda GPU ficar pronta"""
        if not self.gpu_instance_id:
            return self.log_result("Aguardar GPU", False, "Sem GPU")

        start = time.time()
        max_wait = 180

        while time.time() - start < max_wait:
            success, output = run_cmd(
                f"vastai show instance {self.gpu_instance_id} --raw 2>/dev/null | jq -r '.actual_status, .ssh_host, .ssh_port'"
            )
            lines = output.strip().split('\n')

            if len(lines) >= 3 and lines[0] == "running" and lines[1] and lines[2]:
                # Aguardar mais um pouco para SSH
                time.sleep(15)
                return self.log_result(
                    "Aguardar GPU",
                    True,
                    f"SSH: {lines[1]}:{lines[2]}",
                    time.time() - start
                )
            time.sleep(5)

        return self.log_result("Aguardar GPU", False, "Timeout", time.time() - start)

    def test_05_register_gpu(self):
        """Registra GPU no serviço"""
        if not self.service or not self.gpu_instance_id:
            return self.log_result("Registrar GPU", False, "Sem serviço ou GPU")

        start = time.time()
        try:
            success = self.service.register_gpu_instance(self.gpu_instance_id)
            return self.log_result(
                "Registrar GPU",
                success,
                f"SSH: {self.service.gpu_ssh_host}:{self.service.gpu_ssh_port}" if success else "Falha",
                time.time() - start
            )
        except Exception as e:
            return self.log_result("Registrar GPU", False, str(e)[:100], time.time() - start)

    def test_06_start_sync(self):
        """Inicia sincronização"""
        if not self.service:
            return self.log_result("Iniciar sync", False, "Sem serviço")

        start = time.time()
        try:
            success = self.service.start_sync()
            time.sleep(5)  # Dar tempo para primeira sync
            return self.log_result(
                "Iniciar sync",
                success,
                f"Estado: {self.service.state.value}" if success else "Falha",
                time.time() - start
            )
        except Exception as e:
            return self.log_result("Iniciar sync", False, str(e)[:100], time.time() - start)

    def test_07_verify_sync_running(self):
        """Verifica que sync está funcionando"""
        if not self.service:
            return self.log_result("Verificar sync", False, "Sem serviço")

        start = time.time()
        try:
            # Aguardar pelo menos uma sync
            time.sleep(35)  # Intervalo de sync é 30s

            status = self.service.get_status()
            sync_count = status.get('sync', {}).get('count', 0)
            last_sync = status.get('sync', {}).get('last_sync')

            passed = sync_count > 0 and last_sync is not None
            return self.log_result(
                "Verificar sync rodando",
                passed,
                f"Syncs: {sync_count}, Last: {last_sync}" if passed else "Nenhum sync realizado",
                time.time() - start
            )
        except Exception as e:
            return self.log_result("Verificar sync rodando", False, str(e)[:100], time.time() - start)

    def test_08_create_test_file(self):
        """Cria arquivo de teste na GPU"""
        if not self.service:
            return self.log_result("Criar arquivo teste", False, "Sem serviço")

        start = time.time()
        try:
            test_content = f"FAILOVER_TEST_{int(time.time())}"
            ssh_cmd = f"ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa -p {self.service.gpu_ssh_port} root@{self.service.gpu_ssh_host}"

            success, output = run_cmd(
                f"{ssh_cmd} 'mkdir -p /workspace && echo {test_content} > /workspace/failover_test.txt && cat /workspace/failover_test.txt'"
            )

            passed = test_content in output
            self.test_content = test_content if passed else None
            return self.log_result(
                "Criar arquivo teste na GPU",
                passed,
                f"Conteúdo: {test_content}" if passed else output[:100],
                time.time() - start
            )
        except Exception as e:
            return self.log_result("Criar arquivo teste na GPU", False, str(e)[:100], time.time() - start)

    def test_09_wait_sync(self):
        """Aguarda sync do arquivo"""
        if not self.service or not hasattr(self, 'test_content'):
            return self.log_result("Aguardar sync arquivo", False, "Sem serviço ou arquivo")

        start = time.time()
        try:
            # Aguardar próximo ciclo de sync
            time.sleep(35)

            # Verificar na CPU
            cpu_ip = self.cpu_instance.get('external_ip')
            success, output = run_cmd(
                f"ssh -o StrictHostKeyChecking=no root@{cpu_ip} 'cat /workspace/failover_test.txt 2>/dev/null'"
            )

            passed = self.test_content in output
            return self.log_result(
                "Aguardar sync do arquivo",
                passed,
                "Arquivo sincronizado para CPU" if passed else f"Não encontrado na CPU: {output[:50]}",
                time.time() - start
            )
        except Exception as e:
            return self.log_result("Aguardar sync arquivo", False, str(e)[:100], time.time() - start)

    def test_10_simulate_failure(self):
        """Simula falha da GPU"""
        if not self.gpu_instance_id:
            return self.log_result("Simular falha", False, "Sem GPU")

        start = time.time()
        try:
            success, _ = run_cmd(f"vastai destroy instance {self.gpu_instance_id} --raw")
            logger.info("   ⚠️  GPU DESTRUÍDA - Sistema deve detectar e fazer failover")
            return self.log_result("Simular falha GPU", True, f"GPU {self.gpu_instance_id} destruída", time.time() - start)
        except Exception as e:
            return self.log_result("Simular falha GPU", False, str(e), time.time() - start)

    def test_11_wait_failover_detection(self):
        """Aguarda detecção de failover"""
        if not self.service:
            return self.log_result("Detectar failover", False, "Sem serviço")

        start = time.time()
        try:
            # Health check a cada 10s, threshold 3 = ~30-40s para detectar
            max_wait = 60

            while time.time() - start < max_wait:
                status = self.service.get_status()
                failed_checks = status.get('failover', {}).get('failed_checks', 0)
                state = status.get('state')

                logger.info(f"   ... Estado: {state}, Falhas: {failed_checks}/3")

                if state in ['failover_active', 'recovering']:
                    return self.log_result(
                        "Detectar failover",
                        True,
                        f"Failover ativado! Estado: {state}",
                        time.time() - start
                    )

                time.sleep(5)

            return self.log_result("Detectar failover", False, "Timeout - failover não detectado", time.time() - start)
        except Exception as e:
            return self.log_result("Detectar failover", False, str(e)[:100], time.time() - start)

    def test_12_verify_cpu_has_data(self):
        """Verifica que CPU tem os dados"""
        if not self.cpu_instance or not hasattr(self, 'test_content'):
            return self.log_result("Verificar dados CPU", False, "Sem CPU ou arquivo")

        start = time.time()
        try:
            cpu_ip = self.cpu_instance.get('external_ip')
            success, output = run_cmd(
                f"ssh -o StrictHostKeyChecking=no root@{cpu_ip} 'cat /workspace/failover_test.txt'"
            )

            passed = self.test_content in output
            return self.log_result(
                "Verificar dados na CPU",
                passed,
                "✅ DADOS PRESERVADOS!" if passed else "Dados perdidos!",
                time.time() - start
            )
        except Exception as e:
            return self.log_result("Verificar dados CPU", False, str(e)[:100], time.time() - start)

    def test_13_check_auto_recovery(self):
        """Verifica se auto-recovery foi iniciado"""
        if not self.service:
            return self.log_result("Auto-recovery", False, "Sem serviço")

        start = time.time()
        try:
            # Auto-recovery roda em background, aguardar um pouco
            time.sleep(10)

            status = self.service.get_status()
            state = status.get('state')

            if state == 'recovering':
                return self.log_result(
                    "Auto-recovery iniciado",
                    True,
                    "Sistema buscando nova GPU automaticamente",
                    time.time() - start
                )
            elif state == 'syncing':
                return self.log_result(
                    "Auto-recovery completo",
                    True,
                    "Nova GPU já provisionada e sincronizando!",
                    time.time() - start
                )
            else:
                return self.log_result(
                    "Auto-recovery",
                    state in ['failover_active', 'recovering'],
                    f"Estado: {state}",
                    time.time() - start
                )
        except Exception as e:
            return self.log_result("Auto-recovery", False, str(e)[:100], time.time() - start)

    def cleanup(self):
        """Limpa recursos"""
        logger.info("\n🧹 Limpando recursos...")

        # Parar sync
        if self.service:
            try:
                self.service.stop_sync()
                self.service.cleanup()
                logger.info("   Serviço parado")
            except:
                pass

        # Destruir GPU se existir
        if self.gpu_instance_id:
            run_cmd(f"vastai destroy instance {self.gpu_instance_id} --raw 2>/dev/null")
            logger.info(f"   GPU {self.gpu_instance_id} destruída")

        # Destruir nova GPU do auto-recovery
        if self.service and self.service.gpu_instance_id:
            run_cmd(f"vastai destroy instance {self.service.gpu_instance_id} --raw 2>/dev/null")
            logger.info(f"   GPU {self.service.gpu_instance_id} destruída")

    def run(self):
        """Executa todos os testes"""
        logger.info("=" * 60)
        logger.info("🧪 TESTE REAL DO SISTEMA DE FAILOVER AUTOMÁTICO")
        logger.info("=" * 60)
        logger.info("")

        tests = [
            self.test_01_init_service,
            self.test_02_provision_cpu_standby,
            self.test_03_create_gpu,
            self.test_04_wait_gpu_ready,
            self.test_05_register_gpu,
            self.test_06_start_sync,
            self.test_07_verify_sync_running,
            self.test_08_create_test_file,
            self.test_09_wait_sync,
            self.test_10_simulate_failure,
            self.test_11_wait_failover_detection,
            self.test_12_verify_cpu_has_data,
            self.test_13_check_auto_recovery,
        ]

        try:
            for test in tests:
                result = test()
                logger.info("")
                # Se teste crítico falhar, parar
                if not result and test.__name__ in ['test_01_init_service', 'test_02_provision_cpu_standby', 'test_03_create_gpu']:
                    logger.error("Teste crítico falhou, abortando...")
                    break
        finally:
            self.cleanup()

        # Resumo
        logger.info("=" * 60)
        logger.info("📊 RESULTADO FINAL")
        logger.info("=" * 60)
        logger.info(f"✅ Passou: {self.results['passed']}")
        logger.info(f"❌ Falhou: {self.results['failed']}")

        if self.results['failed'] == 0:
            logger.info("\n🎉 SISTEMA DE FAILOVER FUNCIONANDO CORRETAMENTE!")
        else:
            logger.info("\n⚠️  Testes com falha:")
            for t in self.results['tests']:
                if not t['passed']:
                    logger.info(f"   - {t['name']}: {t['detail']}")

        return self.results['failed'] == 0


if __name__ == "__main__":
    test = RealFailoverTest()
    success = test.run()
    sys.exit(0 if success else 1)
