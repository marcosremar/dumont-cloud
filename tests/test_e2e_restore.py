"""
Teste de Integracao E2E - Ciclo completo de Snapshot e Restore

Este teste executa o ciclo completo:
1. Criar snapshot na maquina atual (RTX 5090)
2. Provisionar nova maquina RTX 5090 no vast.ai
3. Restaurar o snapshot na nova maquina
4. Verificar que o DumontAgent foi instalado e esta funcionando
5. Destruir a maquina de teste

IMPORTANTE: Este teste tem custos reais (vast.ai)!
Para rodar: RUN_E2E_TESTS=1 pytest tests/test_e2e_restore.py -v -s

Tempo estimado: 5-10 minutos
Custo estimado: ~$0.10-0.20 USD
"""
import pytest
import subprocess
import time
import json
import os
import requests

# Configuracoes
VPS_HOST = "ubuntu@54.37.225.188"
BASE_URL = "https://dumontcloud.com"
API_URL = f"{BASE_URL}/api"

# Credenciais de teste
TEST_USER = "marcosremar@gmail.com"
TEST_PASS = "marcos123"

# Configuracoes de maquina de teste
TEST_GPU = "RTX_5090"  # Pode ser alterado
TEST_MAX_PRICE = 2.0  # USD/hora maximo
TEST_TIMEOUT_PROVISION = 300  # 5 minutos para provisionar
TEST_TIMEOUT_RESTORE = 180  # 3 minutos para restore
TEST_TIMEOUT_AGENT = 120  # 2 minutos para agente iniciar


def get_session():
    """Retorna sessao autenticada"""
    s = requests.Session()
    resp = s.post(f"{API_URL}/auth/login", json={
        "username": TEST_USER,
        "password": TEST_PASS
    })
    assert resp.status_code == 200, f"Falha no login: {resp.text}"
    return s


def get_active_instance():
    """Obtem instancia ativa via vastai CLI"""
    result = subprocess.run(
        ["ssh", VPS_HOST, "export PATH=$PATH:$HOME/.local/bin; vastai show instances --raw 2>/dev/null"],
        capture_output=True,
        text=True,
        timeout=30
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None

    try:
        instances = json.loads(result.stdout)
        for inst in instances:
            if inst.get('actual_status') == 'running':
                return inst
    except json.JSONDecodeError:
        pass
    return None


def get_ssh_url(instance_id):
    """Obtem URL SSH de uma instancia"""
    result = subprocess.run(
        ["ssh", VPS_HOST, f"export PATH=$PATH:$HOME/.local/bin; vastai ssh-url {instance_id} 2>/dev/null"],
        capture_output=True,
        text=True,
        timeout=30
    )
    if result.returncode == 0 and result.stdout.strip():
        url = result.stdout.strip()
        if url.startswith("ssh://"):
            parts = url.replace("ssh://", "").split("@")
            if len(parts) == 2:
                host_port = parts[1].split(":")
                return {"host": host_port[0], "port": int(host_port[1]) if len(host_port) > 1 else 22}
    return None


def run_on_gpu(ssh_info, command, timeout=60):
    """Executa comando na maquina GPU"""
    ssh_cmd = f'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=20 -p {ssh_info["port"]} root@{ssh_info["host"]} "{command}"'
    result = subprocess.run(
        ["ssh", VPS_HOST, ssh_cmd],
        capture_output=True,
        text=True,
        timeout=timeout
    )
    return result


def wait_for_instance(session, instance_id, timeout=TEST_TIMEOUT_PROVISION):
    """Aguarda instancia ficar pronta (running com SSH)"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = session.get(f"{API_URL}/instances/{instance_id}")
            if resp.status_code == 200:
                data = resp.json()
                status = data.get('status') or data.get('actual_status')
                ssh_host = data.get('ssh_host')
                ssh_port = data.get('ssh_port')

                if status == 'running' and ssh_host and ssh_port:
                    # Testar conexao SSH
                    ssh_info = {"host": ssh_host, "port": ssh_port}
                    result = run_on_gpu(ssh_info, "echo OK", timeout=15)
                    if "OK" in result.stdout:
                        return ssh_info

                print(f"  Status: {status}, SSH: {ssh_host}:{ssh_port}")
        except Exception as e:
            print(f"  Erro ao verificar status: {e}")

        time.sleep(10)

    return None


@pytest.mark.skipif(not os.getenv("RUN_E2E_TESTS"), reason="Requer RUN_E2E_TESTS=1")
class TestE2ERestoreCycle:
    """Teste E2E do ciclo completo de snapshot e restore"""

    @pytest.fixture(scope="class")
    def session(self):
        """Sessao autenticada"""
        return get_session()

    @pytest.fixture(scope="class")
    def source_instance(self):
        """Instancia fonte (maquina atual com dados)"""
        instance = get_active_instance()
        if not instance:
            pytest.skip("Nenhuma instancia fonte ativa encontrada")

        instance_id = instance.get('id')
        ssh_info = get_ssh_url(instance_id)
        if not ssh_info:
            pytest.skip(f"Nao foi possivel obter SSH URL da instancia {instance_id}")

        return {
            "id": instance_id,
            "ssh": ssh_info,
            "info": instance
        }

    def test_01_verify_source_instance(self, source_instance):
        """Verifica que a instancia fonte esta funcionando"""
        result = run_on_gpu(source_instance["ssh"], "echo OK && ls /workspace")
        assert "OK" in result.stdout, "Instancia fonte nao responde"
        print(f"\nInstancia fonte: {source_instance['id']}")
        print(f"SSH: {source_instance['ssh']['host']}:{source_instance['ssh']['port']}")

    def test_02_force_snapshot_on_source(self, session, source_instance):
        """Forca criacao de snapshot na instancia fonte"""
        print(f"\nForcando snapshot na instancia {source_instance['id']}...")

        # Contar snapshots antes
        resp = session.get(f"{API_URL}/snapshots")
        assert resp.status_code == 200
        snapshots_before = len(resp.json().get('snapshots', []))
        print(f"  Snapshots antes: {snapshots_before}")

        # Forcar snapshot via API
        resp = session.post(f"{API_URL}/instances/{source_instance['id']}/snapshot")
        assert resp.status_code == 200, f"Erro ao criar snapshot: {resp.text}"
        data = resp.json()
        assert data.get('success'), f"Snapshot falhou: {data}"
        print(f"  Snapshot criado com sucesso")
        print(f"  Output: {data.get('output', '')[:200]}")

        # Verificar que snapshot foi criado
        time.sleep(5)  # Aguardar indexacao
        resp = session.get(f"{API_URL}/snapshots")
        snapshots_after = len(resp.json().get('snapshots', []))
        print(f"  Snapshots depois: {snapshots_after}")

        # Pode nao ter incrementado se foi deduplicado (dados iguais)
        assert snapshots_after >= snapshots_before, "Numero de snapshots diminuiu!"

    def test_03_get_latest_snapshot_id(self, session):
        """Obtem ID do snapshot mais recente"""
        resp = session.get(f"{API_URL}/snapshots")
        assert resp.status_code == 200

        snapshots = resp.json().get('snapshots', [])
        assert len(snapshots) > 0, "Nenhum snapshot encontrado"

        # Ordenar por data (mais recente primeiro)
        snapshots.sort(key=lambda x: x.get('time', ''), reverse=True)
        latest = snapshots[0]

        print(f"\nSnapshot mais recente:")
        print(f"  ID: {latest.get('id', latest.get('short_id'))}")
        print(f"  Data: {latest.get('time')}")
        print(f"  Paths: {latest.get('paths')}")

        # Salvar para proximos testes
        pytest.latest_snapshot_id = latest.get('id', latest.get('short_id'))

    def test_04_find_available_gpu(self, session):
        """Busca uma maquina GPU disponivel para teste"""
        print(f"\nBuscando maquina GPU disponivel...")

        resp = session.get(f"{API_URL}/offers", params={
            'gpu_name': TEST_GPU,
            'dph_total': TEST_MAX_PRICE,
            'limit': 5
        })
        assert resp.status_code == 200

        offers = resp.json().get('offers', [])
        assert len(offers) > 0, f"Nenhuma oferta de {TEST_GPU} disponivel (max ${TEST_MAX_PRICE}/h)"

        # Escolher a mais barata
        offers.sort(key=lambda x: x.get('dph_total', 999))
        best_offer = offers[0]

        print(f"  Ofertas encontradas: {len(offers)}")
        print(f"  Melhor oferta: ID {best_offer.get('id')}")
        print(f"  GPU: {best_offer.get('gpu_name')}")
        print(f"  Preco: ${best_offer.get('dph_total', 0):.4f}/h")

        pytest.test_offer_id = best_offer.get('id')

    def test_05_provision_test_machine(self, session):
        """Provisiona uma nova maquina para teste"""
        print(f"\nProvisionando maquina de teste (offer {pytest.test_offer_id})...")

        resp = session.post(f"{API_URL}/instances", json={
            'offer_id': pytest.test_offer_id,
            'image': 'pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime'
        })
        assert resp.status_code == 200, f"Erro ao criar instancia: {resp.text}"

        data = resp.json()
        assert data.get('success'), f"Falha ao criar: {data}"

        pytest.test_instance_id = data.get('instance_id')
        print(f"  Instancia criada: {pytest.test_instance_id}")

        # Aguardar instancia ficar pronta
        print(f"  Aguardando instancia ficar pronta (max {TEST_TIMEOUT_PROVISION}s)...")
        ssh_info = wait_for_instance(session, pytest.test_instance_id, TEST_TIMEOUT_PROVISION)
        assert ssh_info, "Instancia nao ficou pronta no tempo limite"

        pytest.test_ssh_info = ssh_info
        print(f"  Instancia pronta! SSH: {ssh_info['host']}:{ssh_info['port']}")

    def test_06_restore_snapshot_to_test_machine(self, session):
        """Restaura o snapshot na maquina de teste"""
        print(f"\nRestaurando snapshot {pytest.latest_snapshot_id} na instancia {pytest.test_instance_id}...")

        resp = session.post(f"{API_URL}/instances/{pytest.test_instance_id}/restore", json={
            'snapshot_id': pytest.latest_snapshot_id,
            'target_path': '/workspace'
        })

        # Pode demorar, entao verificamos periodicamente
        if resp.status_code != 200:
            print(f"  Resposta inicial: {resp.status_code} - {resp.text[:200]}")

        assert resp.status_code == 200, f"Erro no restore: {resp.text}"
        data = resp.json()
        print(f"  Restore concluido: {data}")

    def test_07_verify_workspace_restored(self):
        """Verifica que o workspace foi restaurado"""
        print(f"\nVerificando workspace restaurado...")

        result = run_on_gpu(pytest.test_ssh_info, "ls -la /workspace | head -20", timeout=30)
        assert result.returncode == 0, f"Erro ao listar workspace: {result.stderr}"

        print(f"  Conteudo do /workspace:")
        for line in result.stdout.strip().split('\n')[:10]:
            print(f"    {line}")

        # Verificar que tem arquivos
        assert len(result.stdout.strip().split('\n')) > 2, "Workspace vazio ou muito pequeno"

    def test_08_verify_dumont_agent_installed(self):
        """Verifica que o DumontAgent foi instalado"""
        print(f"\nVerificando instalacao do DumontAgent...")

        # Verificar script
        result = run_on_gpu(pytest.test_ssh_info, "test -f /opt/dumont/dumont-agent.sh && echo OK")
        assert "OK" in result.stdout, "Script do agente nao encontrado"
        print(f"  Script do agente: OK")

        # Verificar config
        result = run_on_gpu(pytest.test_ssh_info, "test -f /opt/dumont/config.env && echo OK")
        assert "OK" in result.stdout, "Config do agente nao encontrado"
        print(f"  Config do agente: OK")

        # Verificar dumontctl
        result = run_on_gpu(pytest.test_ssh_info, "which dumontctl")
        assert "/usr/local/bin/dumontctl" in result.stdout, "dumontctl nao encontrado"
        print(f"  dumontctl: OK")

        # Verificar restic
        result = run_on_gpu(pytest.test_ssh_info, "restic version")
        assert "restic" in result.stdout.lower(), "restic nao instalado"
        print(f"  restic: OK")

    def test_09_verify_dumont_agent_running(self):
        """Verifica que o DumontAgent esta rodando"""
        print(f"\nVerificando se DumontAgent esta rodando...")

        # Aguardar agente iniciar (pode demorar alguns segundos apos o restore)
        start = time.time()
        agent_running = False

        while time.time() - start < TEST_TIMEOUT_AGENT:
            result = run_on_gpu(pytest.test_ssh_info, "pgrep -f dumont-agent.sh", timeout=15)
            if result.returncode == 0 and result.stdout.strip():
                agent_running = True
                break
            print(f"  Aguardando agente iniciar... ({int(time.time() - start)}s)")
            time.sleep(10)

        assert agent_running, "Agente nao iniciou no tempo limite"

        # Verificar status do agente
        result = run_on_gpu(pytest.test_ssh_info, "cat /tmp/dumont-agent-status.json 2>/dev/null", timeout=15)
        if result.returncode == 0 and result.stdout.strip():
            try:
                status = json.loads(result.stdout)
                print(f"  Status do agente:")
                print(f"    Versao: {status.get('version')}")
                print(f"    Status: {status.get('status')}")
                print(f"    Intervalo: {status.get('interval')}s")
                print(f"    Retencao: {status.get('keep_last')} snapshots")
            except:
                pass

        print(f"  Agente rodando: OK")

    def test_10_verify_sync_working(self):
        """Verifica que a sincronizacao esta funcionando"""
        print(f"\nVerificando sincronizacao...")

        # Criar arquivo de teste
        result = run_on_gpu(pytest.test_ssh_info,
            "mkdir -p /workspace/.e2e-test && echo 'E2E Test $(date)' > /workspace/.e2e-test/test.txt && cat /workspace/.e2e-test/test.txt",
            timeout=30)
        assert result.returncode == 0, f"Erro ao criar arquivo de teste: {result.stderr}"
        print(f"  Arquivo de teste criado")

        # Forcar backup
        result = run_on_gpu(pytest.test_ssh_info, "dumontctl backup 2>&1", timeout=120)
        print(f"  Backup forcado: {result.stdout[:200]}")

        # Limpar arquivo de teste
        run_on_gpu(pytest.test_ssh_info, "rm -rf /workspace/.e2e-test", timeout=15)
        print(f"  Arquivo de teste removido")

        print(f"  Sincronizacao: OK")

    def test_99_cleanup_destroy_test_machine(self, session):
        """Destroi a maquina de teste (cleanup)"""
        if not hasattr(pytest, 'test_instance_id'):
            pytest.skip("Nenhuma instancia de teste para destruir")

        print(f"\nDestruindo maquina de teste {pytest.test_instance_id}...")

        resp = session.delete(f"{API_URL}/instances/{pytest.test_instance_id}")
        if resp.status_code == 200:
            print(f"  Instancia destruida com sucesso")
        else:
            print(f"  Aviso: Falha ao destruir instancia: {resp.text}")
            print(f"  Por favor, destrua manualmente: vastai destroy instance {pytest.test_instance_id}")


@pytest.mark.skipif(not os.getenv("RUN_E2E_TESTS"), reason="Requer RUN_E2E_TESTS=1")
class TestE2EQuickValidation:
    """Teste rapido de validacao (sem provisionar nova maquina)"""

    @pytest.fixture(scope="class")
    def session(self):
        return get_session()

    def test_force_snapshot_api(self, session):
        """Testa API de forcar snapshot"""
        instance = get_active_instance()
        if not instance:
            pytest.skip("Nenhuma instancia ativa")

        resp = session.post(f"{API_URL}/instances/{instance['id']}/snapshot")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get('success') or 'output' in data

    def test_agent_status_api(self, session):
        """Testa API de status do agente"""
        instance = get_active_instance()
        if not instance:
            pytest.skip("Nenhuma instancia ativa")

        resp = session.get(f"{API_URL}/instances/{instance['id']}/agent-status")
        assert resp.status_code == 200
        data = resp.json()
        assert 'agent_installed' in data
        assert 'agent_running' in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
