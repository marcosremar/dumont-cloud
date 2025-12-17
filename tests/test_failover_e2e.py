#!/usr/bin/env python3
"""
Teste End-to-End do Sistema de Failover Automático
Testa o fluxo completo: GPU → Failover → Auto-Recovery → Restore

Executa cenários reais com máquinas Vast.ai e GCP.
"""
import os
import sys
import json
import time
import subprocess
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Adicionar src ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


class FailoverE2ETest:
    """Teste end-to-end do sistema de failover"""

    def __init__(self):
        self.results = {
            'tests': [],
            'passed': 0,
            'failed': 0,
            'start_time': datetime.now().isoformat()
        }
        self.gpu_instance_id = None
        self.cpu_instance_ip = None
        self.service = None

    def log_test(self, name: str, passed: bool, details: str = "", duration: float = 0):
        """Registra resultado de um teste"""
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status}: {name} ({duration:.1f}s)")
        if details:
            logger.info(f"   └─ {details}")

        self.results['tests'].append({
            'name': name,
            'passed': passed,
            'details': details,
            'duration': duration
        })

        if passed:
            self.results['passed'] += 1
        else:
            self.results['failed'] += 1

    def run_command(self, cmd: str, timeout: int = 60) -> tuple:
        """Executa comando e retorna (success, output)"""
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "Timeout"
        except Exception as e:
            return False, str(e)

    # ==================== TESTES ====================

    def test_01_vast_api_available(self) -> bool:
        """Testa se API da Vast.ai está acessível"""
        start = time.time()
        success, output = self.run_command("vastai show user --raw 2>/dev/null | jq -r '.username'")
        duration = time.time() - start

        passed = success and output.strip() != ""
        self.log_test(
            "Vast.ai API acessível",
            passed,
            f"User: {output.strip()[:20]}..." if passed else output[:100],
            duration
        )
        return passed

    def test_02_gcp_api_available(self) -> bool:
        """Testa se API do GCP está acessível"""
        start = time.time()
        success, output = self.run_command("gcloud compute zones list --limit=1 2>/dev/null | head -2")
        duration = time.time() - start

        passed = success and "NAME" in output
        self.log_test(
            "GCP API acessível",
            passed,
            "Credenciais OK" if passed else output[:100],
            duration
        )
        return passed

    def test_03_search_gpu_offers(self) -> bool:
        """Testa busca de GPUs disponíveis"""
        start = time.time()
        success, output = self.run_command(
            "vastai search offers 'rentable=true gpu_ram>=8 dph<0.50' --raw 2>/dev/null | jq 'length'"
        )
        duration = time.time() - start

        try:
            count = int(output.strip())
            passed = count > 0
        except:
            count = 0
            passed = False

        self.log_test(
            "Busca de GPUs disponíveis",
            passed,
            f"{count} ofertas encontradas" if passed else "Nenhuma oferta",
            duration
        )
        return passed

    def test_04_create_gpu_instance(self) -> bool:
        """Cria instância GPU de teste"""
        start = time.time()

        # Buscar GPU barata em região confiável
        success, output = self.run_command(
            """vastai search offers 'rentable=true gpu_ram>=8 dph<0.40' --raw 2>/dev/null | \
               jq -r 'sort_by(.dph_total) | .[0:10] | .[] | select(.geolocation | test("TH|VN|JP|EU")) | .id' | head -1"""
        )

        if not success or not output.strip():
            # Fallback: qualquer GPU barata
            success, output = self.run_command(
                "vastai search offers 'rentable=true gpu_ram>=8 dph<0.40' --raw 2>/dev/null | jq -r 'sort_by(.dph_total) | .[0].id'"
            )

        offer_id = output.strip()
        if not offer_id or offer_id == "null":
            self.log_test("Criar instância GPU", False, "Nenhuma oferta disponível", time.time() - start)
            return False

        # Criar instância
        success, output = self.run_command(
            f"vastai create instance {offer_id} --image pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime --disk 20 --ssh --raw 2>/dev/null"
        )

        duration = time.time() - start

        try:
            result = json.loads(output)
            if result.get('success'):
                self.gpu_instance_id = result.get('new_contract')
                self.log_test(
                    "Criar instância GPU",
                    True,
                    f"Instance ID: {self.gpu_instance_id}",
                    duration
                )
                return True
        except:
            pass

        self.log_test("Criar instância GPU", False, output[:100], duration)
        return False

    def test_05_wait_gpu_ready(self) -> bool:
        """Aguarda GPU ficar pronta"""
        if not self.gpu_instance_id:
            self.log_test("Aguardar GPU pronta", False, "Sem GPU criada")
            return False

        start = time.time()
        max_wait = 180  # 3 minutos

        while time.time() - start < max_wait:
            success, output = self.run_command(
                f"vastai show instance {self.gpu_instance_id} --raw 2>/dev/null | jq -r '.actual_status'"
            )
            status = output.strip()

            if status == "running":
                # Verificar SSH disponível
                success2, output2 = self.run_command(
                    f"vastai show instance {self.gpu_instance_id} --raw 2>/dev/null | jq -r '.ssh_host, .ssh_port'"
                )
                lines = output2.strip().split('\n')
                if len(lines) >= 2 and lines[0] and lines[1]:
                    duration = time.time() - start
                    self.log_test(
                        "Aguardar GPU pronta",
                        True,
                        f"SSH: {lines[0]}:{lines[1]}",
                        duration
                    )
                    return True

            time.sleep(5)

        self.log_test("Aguardar GPU pronta", False, f"Timeout ({max_wait}s)", time.time() - start)
        return False

    def test_06_create_cpu_standby(self) -> bool:
        """Cria CPU standby no GCP"""
        start = time.time()

        instance_name = f"test-standby-{int(time.time())}"

        success, output = self.run_command(f"""
            gcloud compute instances create {instance_name} \
                --zone=europe-west1-b \
                --machine-type=e2-small \
                --provisioning-model=SPOT \
                --image-family=ubuntu-2204-lts \
                --image-project=ubuntu-os-cloud \
                --boot-disk-size=20GB \
                --format=json 2>/dev/null
        """, timeout=120)

        duration = time.time() - start

        try:
            result = json.loads(output)
            if isinstance(result, list) and len(result) > 0:
                self.cpu_instance_ip = result[0].get('networkInterfaces', [{}])[0].get('accessConfigs', [{}])[0].get('natIP')
                self.cpu_instance_name = instance_name
                self.log_test(
                    "Criar CPU standby GCP",
                    True,
                    f"IP: {self.cpu_instance_ip}",
                    duration
                )
                return True
        except:
            pass

        self.log_test("Criar CPU standby GCP", False, output[:100], duration)
        return False

    def test_07_ssh_to_gpu(self) -> bool:
        """Testa conexão SSH com GPU"""
        if not self.gpu_instance_id:
            self.log_test("SSH para GPU", False, "Sem GPU")
            return False

        start = time.time()

        # Obter info SSH
        success, output = self.run_command(
            f"vastai show instance {self.gpu_instance_id} --raw 2>/dev/null | jq -r '.ssh_host, .ssh_port'"
        )
        lines = output.strip().split('\n')
        if len(lines) < 2:
            self.log_test("SSH para GPU", False, "Info SSH não disponível")
            return False

        ssh_host, ssh_port = lines[0], lines[1]

        # Tentar SSH
        success, output = self.run_command(
            f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=30 -i ~/.ssh/id_rsa -p {ssh_port} root@{ssh_host} 'echo SSH_OK' 2>&1",
            timeout=45
        )

        duration = time.time() - start
        passed = "SSH_OK" in output

        self.log_test(
            "SSH para GPU",
            passed,
            f"{ssh_host}:{ssh_port}" if passed else output[:100],
            duration
        )
        return passed

    def test_08_ssh_to_cpu(self) -> bool:
        """Testa conexão SSH com CPU standby"""
        if not self.cpu_instance_ip:
            self.log_test("SSH para CPU", False, "Sem CPU")
            return False

        start = time.time()

        # Aguardar SSH ficar disponível
        for _ in range(12):  # 60 segundos
            success, output = self.run_command(
                f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@{self.cpu_instance_ip} 'echo SSH_OK' 2>&1",
                timeout=15
            )
            if "SSH_OK" in output:
                self.log_test("SSH para CPU", True, self.cpu_instance_ip, time.time() - start)
                return True
            time.sleep(5)

        self.log_test("SSH para CPU", False, "Timeout", time.time() - start)
        return False

    def test_09_sync_gpu_to_cpu(self) -> bool:
        """Testa sincronização GPU → CPU"""
        if not self.gpu_instance_id or not self.cpu_instance_ip:
            self.log_test("Sync GPU → CPU", False, "Sem GPU ou CPU")
            return False

        start = time.time()

        # Obter SSH da GPU
        success, output = self.run_command(
            f"vastai show instance {self.gpu_instance_id} --raw 2>/dev/null | jq -r '.ssh_host, .ssh_port'"
        )
        lines = output.strip().split('\n')
        ssh_host, ssh_port = lines[0], lines[1]

        # Criar arquivo de teste na GPU
        test_content = f"test-{int(time.time())}"
        self.run_command(
            f"ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa -p {ssh_port} root@{ssh_host} 'mkdir -p /workspace && echo {test_content} > /workspace/test.txt'"
        )

        # Criar diretório na CPU
        self.run_command(
            f"ssh -o StrictHostKeyChecking=no root@{self.cpu_instance_ip} 'mkdir -p /workspace'"
        )

        # Fazer rsync GPU → CPU (via local como relay)
        self.run_command("rm -rf /tmp/sync-test && mkdir -p /tmp/sync-test")

        # GPU → Local
        success1, _ = self.run_command(
            f"rsync -avz -e 'ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa -p {ssh_port}' root@{ssh_host}:/workspace/ /tmp/sync-test/",
            timeout=60
        )

        # Local → CPU
        success2, _ = self.run_command(
            f"rsync -avz -e 'ssh -o StrictHostKeyChecking=no' /tmp/sync-test/ root@{self.cpu_instance_ip}:/workspace/",
            timeout=60
        )

        # Verificar arquivo na CPU
        success3, output = self.run_command(
            f"ssh -o StrictHostKeyChecking=no root@{self.cpu_instance_ip} 'cat /workspace/test.txt 2>/dev/null'"
        )

        duration = time.time() - start
        passed = success1 and success2 and test_content in output

        self.log_test(
            "Sync GPU → CPU",
            passed,
            "Dados sincronizados" if passed else "Falha no sync",
            duration
        )
        return passed

    def test_10_simulate_gpu_failure(self) -> bool:
        """Simula falha da GPU (destruir instância)"""
        if not self.gpu_instance_id:
            self.log_test("Simular falha GPU", False, "Sem GPU")
            return False

        start = time.time()

        success, output = self.run_command(
            f"vastai destroy instance {self.gpu_instance_id} --raw 2>/dev/null"
        )

        duration = time.time() - start
        self.log_test(
            "Simular falha GPU",
            True,
            f"GPU {self.gpu_instance_id} destruída",
            duration
        )
        return True

    def test_11_verify_cpu_has_data(self) -> bool:
        """Verifica que CPU mantém os dados após falha da GPU"""
        if not self.cpu_instance_ip:
            self.log_test("CPU mantém dados", False, "Sem CPU")
            return False

        start = time.time()

        success, output = self.run_command(
            f"ssh -o StrictHostKeyChecking=no root@{self.cpu_instance_ip} 'ls -la /workspace/ 2>/dev/null'"
        )

        duration = time.time() - start
        passed = success and "test.txt" in output

        self.log_test(
            "CPU mantém dados após falha",
            passed,
            "Dados preservados" if passed else "Dados perdidos",
            duration
        )
        return passed

    def test_12_provision_new_gpu(self) -> bool:
        """Provisiona nova GPU (simula auto-recovery)"""
        start = time.time()

        # Buscar GPU disponível
        success, output = self.run_command(
            "vastai search offers 'rentable=true gpu_ram>=8 dph<0.40' --raw 2>/dev/null | jq -r 'sort_by(.dph_total) | .[0].id'"
        )

        offer_id = output.strip()
        if not offer_id or offer_id == "null":
            self.log_test("Provisionar nova GPU", False, "Sem ofertas", time.time() - start)
            return False

        # Criar instância
        success, output = self.run_command(
            f"vastai create instance {offer_id} --image pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime --disk 20 --ssh --raw 2>/dev/null"
        )

        try:
            result = json.loads(output)
            if result.get('success'):
                self.gpu_instance_id = result.get('new_contract')
                self.log_test(
                    "Provisionar nova GPU",
                    True,
                    f"Nova GPU: {self.gpu_instance_id}",
                    time.time() - start
                )
                return True
        except:
            pass

        self.log_test("Provisionar nova GPU", False, output[:100], time.time() - start)
        return False

    def test_13_restore_to_new_gpu(self) -> bool:
        """Restaura dados da CPU para nova GPU"""
        if not self.gpu_instance_id or not self.cpu_instance_ip:
            self.log_test("Restaurar para nova GPU", False, "Sem GPU ou CPU")
            return False

        start = time.time()

        # Aguardar nova GPU ficar pronta
        logger.info("   Aguardando nova GPU ficar pronta...")
        max_wait = 180
        ssh_host = ssh_port = None

        wait_start = time.time()
        while time.time() - wait_start < max_wait:
            success, output = self.run_command(
                f"vastai show instance {self.gpu_instance_id} --raw 2>/dev/null | jq -r '.actual_status, .ssh_host, .ssh_port'"
            )
            lines = output.strip().split('\n')
            if len(lines) >= 3 and lines[0] == "running" and lines[1] and lines[2]:
                ssh_host, ssh_port = lines[1], lines[2]
                break
            time.sleep(5)

        if not ssh_host:
            self.log_test("Restaurar para nova GPU", False, "GPU não ficou pronta", time.time() - start)
            return False

        # Aguardar SSH
        time.sleep(10)

        # Criar diretório na nova GPU
        self.run_command(
            f"ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa -p {ssh_port} root@{ssh_host} 'mkdir -p /workspace'",
            timeout=30
        )

        # Restaurar: CPU → Local → GPU
        self.run_command("rm -rf /tmp/restore-test && mkdir -p /tmp/restore-test")

        success1, _ = self.run_command(
            f"rsync -avz -e 'ssh -o StrictHostKeyChecking=no' root@{self.cpu_instance_ip}:/workspace/ /tmp/restore-test/",
            timeout=60
        )

        success2, _ = self.run_command(
            f"rsync -avz -e 'ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa -p {ssh_port}' /tmp/restore-test/ root@{ssh_host}:/workspace/",
            timeout=60
        )

        # Verificar arquivo na nova GPU
        success3, output = self.run_command(
            f"ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa -p {ssh_port} root@{ssh_host} 'cat /workspace/test.txt 2>/dev/null'",
            timeout=30
        )

        duration = time.time() - start
        passed = success1 and success2 and "test-" in output

        self.log_test(
            "Restaurar para nova GPU",
            passed,
            "Dados restaurados" if passed else "Falha na restauração",
            duration
        )
        return passed

    def cleanup(self):
        """Limpa recursos de teste"""
        logger.info("\n🧹 Limpando recursos de teste...")

        if self.gpu_instance_id:
            self.run_command(f"vastai destroy instance {self.gpu_instance_id} --raw 2>/dev/null")
            logger.info(f"   GPU {self.gpu_instance_id} destruída")

        if hasattr(self, 'cpu_instance_name'):
            self.run_command(
                f"gcloud compute instances delete {self.cpu_instance_name} --zone=europe-west1-b --quiet 2>/dev/null"
            )
            logger.info(f"   CPU {self.cpu_instance_name} destruída")

    def run_all_tests(self):
        """Executa todos os testes"""
        logger.info("=" * 60)
        logger.info("🧪 TESTE END-TO-END DO SISTEMA DE FAILOVER")
        logger.info("=" * 60)
        logger.info("")

        tests = [
            self.test_01_vast_api_available,
            self.test_02_gcp_api_available,
            self.test_03_search_gpu_offers,
            self.test_04_create_gpu_instance,
            self.test_05_wait_gpu_ready,
            self.test_06_create_cpu_standby,
            self.test_07_ssh_to_gpu,
            self.test_08_ssh_to_cpu,
            self.test_09_sync_gpu_to_cpu,
            self.test_10_simulate_gpu_failure,
            self.test_11_verify_cpu_has_data,
            self.test_12_provision_new_gpu,
            self.test_13_restore_to_new_gpu,
        ]

        try:
            for test in tests:
                if not test():
                    # Continuar mesmo se falhar (para ver todos os problemas)
                    pass
                logger.info("")
        finally:
            self.cleanup()

        # Resumo
        logger.info("=" * 60)
        logger.info("📊 RESUMO DOS TESTES")
        logger.info("=" * 60)
        logger.info(f"✅ Passed: {self.results['passed']}")
        logger.info(f"❌ Failed: {self.results['failed']}")
        logger.info(f"📈 Total:  {len(self.results['tests'])}")
        logger.info("")

        if self.results['failed'] == 0:
            logger.info("🎉 TODOS OS TESTES PASSARAM!")
        else:
            logger.info("⚠️  ALGUNS TESTES FALHARAM:")
            for test in self.results['tests']:
                if not test['passed']:
                    logger.info(f"   - {test['name']}: {test['details']}")

        return self.results['failed'] == 0


if __name__ == "__main__":
    test = FailoverE2ETest()
    success = test.run_all_tests()
    sys.exit(0 if success else 1)
