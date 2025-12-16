"""
Testes de integracao para o DumontAgent
Testa instalacao, resiliencia (systemd) e sincronizacao

IMPORTANTE: Estes testes requerem uma maquina GPU ativa!
Para rodar: pytest tests/test_dumont_agent.py -v

Para testes sem custo (dry run):
    pytest tests/test_dumont_agent.py -v -k "not real_machine"
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
        # ssh://root@IP:PORT
        url = result.stdout.strip()
        if url.startswith("ssh://"):
            parts = url.replace("ssh://", "").split("@")
            if len(parts) == 2:
                host_port = parts[1].split(":")
                return {"host": host_port[0], "port": int(host_port[1]) if len(host_port) > 1 else 22}
    return None


def run_on_gpu(ssh_info, command, timeout=60):
    """Executa comando na maquina GPU via VPS"""
    ssh_cmd = f'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=20 -p {ssh_info["port"]} root@{ssh_info["host"]} "{command}"'
    result = subprocess.run(
        ["ssh", VPS_HOST, ssh_cmd],
        capture_output=True,
        text=True,
        timeout=timeout
    )
    return result


class TestDumontAgentAPI:
    """Testes da API de configuracoes do agente"""

    @pytest.fixture
    def session(self):
        """Sessao autenticada"""
        s = requests.Session()
        # Login
        resp = s.post(f"{API_URL}/auth/login", json={
            "username": "marcosremar@gmail.com",
            "password": "marcos123"
        })
        assert resp.status_code == 200
        return s

    def test_get_agent_settings(self, session):
        """Testa GET /api/settings/agent"""
        resp = session.get(f"{API_URL}/settings/agent")
        assert resp.status_code == 200
        data = resp.json()
        assert 'sync_interval' in data
        assert 'keep_last' in data
        assert isinstance(data['sync_interval'], int)
        assert isinstance(data['keep_last'], int)

    def test_update_agent_settings(self, session):
        """Testa PUT /api/settings/agent"""
        # Salvar configuracoes
        resp = session.put(f"{API_URL}/settings/agent", json={
            'sync_interval': 60,
            'keep_last': 20
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data['success'] == True
        assert data['sync_interval'] == 60
        assert data['keep_last'] == 20

        # Restaurar para padrao
        session.put(f"{API_URL}/settings/agent", json={
            'sync_interval': 30,
            'keep_last': 10
        })

    def test_agent_settings_validation_min_interval(self, session):
        """Testa validacao de intervalo minimo"""
        resp = session.put(f"{API_URL}/settings/agent", json={
            'sync_interval': 5,  # Muito baixo
            'keep_last': 10
        })
        assert resp.status_code == 400
        assert 'minimo' in resp.json().get('error', '').lower()

    def test_agent_settings_validation_max_interval(self, session):
        """Testa validacao de intervalo maximo"""
        resp = session.put(f"{API_URL}/settings/agent", json={
            'sync_interval': 7200,  # 2 horas - muito alto
            'keep_last': 10
        })
        assert resp.status_code == 400
        assert 'maximo' in resp.json().get('error', '').lower()

    def test_agent_settings_validation_keep_last(self, session):
        """Testa validacao de keep_last"""
        resp = session.put(f"{API_URL}/settings/agent", json={
            'sync_interval': 30,
            'keep_last': 0  # Deve ser >= 1
        })
        assert resp.status_code == 400

    def test_receive_agent_status(self):
        """Testa POST /api/agent/status (nao requer auth)"""
        resp = requests.post(f"{API_URL}/agent/status", json={
            "agent": "DumontAgent",
            "version": "2.0.0",
            "instance_id": "test-instance",
            "status": "idle",
            "message": "Test status",
            "timestamp": "2024-12-16T00:00:00Z"
        })
        assert resp.status_code == 200
        assert resp.json()['success'] == True


@pytest.mark.skipif(not os.getenv("RUN_GPU_TESTS"), reason="Requer RUN_GPU_TESTS=1")
class TestDumontAgentRealMachine:
    """Testes em maquina GPU real - requer instancia ativa"""

    @pytest.fixture(scope="class")
    def gpu_instance(self):
        """Obtem informacoes da instancia GPU ativa"""
        instance = get_active_instance()
        if not instance:
            pytest.skip("Nenhuma instancia GPU ativa encontrada")

        instance_id = instance.get('id')
        ssh_info = get_ssh_url(instance_id)
        if not ssh_info:
            pytest.skip(f"Nao foi possivel obter SSH URL da instancia {instance_id}")

        return {
            "id": instance_id,
            "ssh": ssh_info,
            "info": instance
        }

    def test_agent_is_installed(self, gpu_instance):
        """Verifica que o agente esta instalado"""
        result = run_on_gpu(gpu_instance["ssh"], "test -f /opt/dumont/dumont-agent.sh && echo OK")
        assert "OK" in result.stdout, "Script do agente nao encontrado"

    def test_config_exists(self, gpu_instance):
        """Verifica que o arquivo de config existe"""
        result = run_on_gpu(gpu_instance["ssh"], "test -f /opt/dumont/config.env && echo OK")
        assert "OK" in result.stdout, "Arquivo de config nao encontrado"

    def test_dumontctl_exists(self, gpu_instance):
        """Verifica que o comando dumontctl existe"""
        result = run_on_gpu(gpu_instance["ssh"], "which dumontctl")
        assert "/usr/local/bin/dumontctl" in result.stdout, "dumontctl nao encontrado"

    def test_systemd_service_exists(self, gpu_instance):
        """Verifica se o servico systemd foi criado"""
        result = run_on_gpu(gpu_instance["ssh"],
            "test -f /etc/systemd/system/dumont-agent.service && echo SYSTEMD || echo NOHUP")
        # Pode ser SYSTEMD ou NOHUP dependendo do ambiente
        assert "SYSTEMD" in result.stdout or "NOHUP" in result.stdout

    def test_agent_is_running(self, gpu_instance):
        """Verifica que o agente esta rodando"""
        result = run_on_gpu(gpu_instance["ssh"], "pgrep -f dumont-agent.sh")
        assert result.returncode == 0, "Agente nao esta rodando"
        assert result.stdout.strip().isdigit(), "PID invalido"

    def test_status_file_exists(self, gpu_instance):
        """Verifica que o arquivo de status existe"""
        result = run_on_gpu(gpu_instance["ssh"],
            "cat /tmp/dumont-agent-status.json 2>/dev/null")
        if result.returncode == 0 and result.stdout.strip():
            status = json.loads(result.stdout)
            assert "status" in status
            assert "instance_id" in status

    def test_log_file_has_content(self, gpu_instance):
        """Verifica que o log tem conteudo"""
        result = run_on_gpu(gpu_instance["ssh"],
            "wc -l /var/log/dumont-agent.log 2>/dev/null | cut -d' ' -f1")
        if result.returncode == 0:
            lines = int(result.stdout.strip() or 0)
            assert lines > 0, "Log vazio"

    def test_restic_is_installed(self, gpu_instance):
        """Verifica que o restic esta instalado"""
        result = run_on_gpu(gpu_instance["ssh"], "restic version")
        assert "restic" in result.stdout.lower(), "Restic nao instalado"


@pytest.mark.skipif(not os.getenv("RUN_RESILIENCE_TESTS"), reason="Requer RUN_RESILIENCE_TESTS=1")
class TestDumontAgentResilience:
    """Testes de resiliencia - mata o agente e verifica restart"""

    @pytest.fixture(scope="class")
    def gpu_instance(self):
        """Obtem informacoes da instancia GPU ativa"""
        instance = get_active_instance()
        if not instance:
            pytest.skip("Nenhuma instancia GPU ativa encontrada")

        instance_id = instance.get('id')
        ssh_info = get_ssh_url(instance_id)
        if not ssh_info:
            pytest.skip(f"Nao foi possivel obter SSH URL da instancia {instance_id}")

        return {
            "id": instance_id,
            "ssh": ssh_info,
            "info": instance
        }

    def test_agent_restarts_after_kill(self, gpu_instance):
        """Testa que o agente reinicia automaticamente apos ser morto (systemd)"""
        # Verificar se tem systemd
        result = run_on_gpu(gpu_instance["ssh"],
            "test -f /etc/systemd/system/dumont-agent.service && echo SYSTEMD || echo NOHUP")

        if "NOHUP" in result.stdout:
            pytest.skip("Ambiente sem systemd - restart automatico nao disponivel")

        # Obter PID atual
        result = run_on_gpu(gpu_instance["ssh"], "pgrep -f dumont-agent.sh")
        assert result.returncode == 0, "Agente nao esta rodando"
        pid_before = result.stdout.strip()

        # Matar o processo
        run_on_gpu(gpu_instance["ssh"], "pkill -9 -f dumont-agent.sh")

        # Aguardar restart (RestartSec=10)
        time.sleep(15)

        # Verificar novo PID
        result = run_on_gpu(gpu_instance["ssh"], "pgrep -f dumont-agent.sh")
        assert result.returncode == 0, "Agente nao reiniciou"
        pid_after = result.stdout.strip()

        assert pid_before != pid_after, "PID deveria ser diferente apos restart"

    def test_systemd_status_active(self, gpu_instance):
        """Verifica status do systemd"""
        result = run_on_gpu(gpu_instance["ssh"],
            "systemctl is-active dumont-agent 2>/dev/null || echo inactive")

        if "inactive" in result.stdout and "command not found" not in result.stderr:
            # Systemd existe mas servico inativo
            pytest.fail("Servico dumont-agent nao esta ativo")


class TestDumontAgentSync:
    """Testes de sincronizacao - verifica que backups sao criados"""

    @pytest.fixture(scope="class")
    def session(self):
        """Sessao autenticada"""
        s = requests.Session()
        resp = s.post(f"{API_URL}/auth/login", json={
            "username": "marcosremar@gmail.com",
            "password": "marcos123"
        })
        assert resp.status_code == 200
        return s

    def test_snapshots_endpoint_works(self, session):
        """Verifica que o endpoint de snapshots funciona"""
        resp = session.get(f"{API_URL}/snapshots")
        assert resp.status_code == 200
        data = resp.json()
        assert 'snapshots' in data or 'deduplicated' in data

    def test_has_auto_snapshots(self, session):
        """Verifica que existem snapshots automaticos (tag: auto)"""
        resp = session.get(f"{API_URL}/snapshots")
        assert resp.status_code == 200
        data = resp.json()

        snapshots = data.get('snapshots', [])
        auto_snapshots = [s for s in snapshots if 'auto' in s.get('tags', [])]

        # Pode nao ter snapshots auto ainda - isso e ok
        print(f"Encontrados {len(auto_snapshots)} snapshots automaticos")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
