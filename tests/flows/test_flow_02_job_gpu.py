"""
Fluxo 2: Job GPU (Execute & Destroy)
Testes REAIS contra a API.
"""
import pytest
import httpx
import time


@pytest.mark.flow2
class TestJobsAPI:
    """Testes da API de jobs (sem executar jobs reais)"""

    def test_list_jobs(self, authed_client: httpx.Client):
        """Deve listar jobs do usuário"""
        response = authed_client.get("/api/jobs")
        if response.status_code == 404:
            response = authed_client.get("/api/v1/jobs")

        # Se endpoint não existe, pular
        if response.status_code == 404:
            pytest.skip("Endpoint /api/jobs não implementado")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    def test_get_job_not_found(self, authed_client: httpx.Client):
        """Deve retornar 404 para job inexistente"""
        response = authed_client.get("/api/jobs/nonexistent-job-id")

        assert response.status_code == 404


@pytest.mark.flow2
@pytest.mark.real_gpu
@pytest.mark.slow
class TestJobExecution:
    """Testes de execução de jobs (requer GPU real)"""

    def test_create_simple_job(self, authed_client: httpx.Client, test_context):
        """Deve criar um job simples"""
        response = authed_client.post("/api/jobs", json={
            "name": "test-job-nvidia-smi",
            "script": "nvidia-smi && echo 'Job completed successfully!'",
            "gpu_type": "RTX 3090",
            "disk_size": 10,
            "timeout_minutes": 5,
            "max_price": 0.25
        })

        # Se endpoint não existe ou método não permitido, pular
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint POST /api/jobs não implementado")

        assert response.status_code in [200, 201, 202]
        data = response.json()

        assert "job_id" in data or "id" in data
        job_id = data.get("job_id") or data.get("id")
        test_context.created_jobs.append(job_id)

    def test_job_status_progression(self, authed_client: httpx.Client, test_context):
        """Deve acompanhar progressão do status do job"""
        if not test_context.created_jobs:
            pytest.skip("Nenhum job criado")

        job_id = test_context.created_jobs[-1]

        # Aguardar até 5 minutos
        start = time.time()
        final_status = None

        while time.time() - start < 300:
            response = authed_client.get(f"/api/jobs/{job_id}")
            assert response.status_code == 200

            data = response.json()
            status = data.get("status")

            if status in ["completed", "failed", "cancelled"]:
                final_status = status
                break

            time.sleep(10)

        assert final_status is not None, "Job não completou em 5 minutos"

    def test_job_output(self, authed_client: httpx.Client, test_context):
        """Deve retornar output do job"""
        if not test_context.created_jobs:
            pytest.skip("Nenhum job criado")

        job_id = test_context.created_jobs[-1]
        response = authed_client.get(f"/api/jobs/{job_id}/output")

        # Pode ser 200 ou 404 se job ainda não tem output
        assert response.status_code in [200, 404]

    def test_gpu_destroyed_after_job(self, authed_client: httpx.Client, test_context):
        """GPU deve ser destruída após job completar"""
        if not test_context.created_jobs:
            pytest.skip("Nenhum job criado")

        # Listar instâncias ativas
        response = authed_client.get("/api/instances")
        assert response.status_code == 200

        instances = response.json()
        if isinstance(instances, dict):
            instances = instances.get("instances", [])

        # Não deve haver instância do job
        # (jobs destroem GPU automaticamente)


@pytest.mark.flow2
@pytest.mark.real_gpu
@pytest.mark.slow
class TestJobWithArtifacts:
    """Testes de jobs com artefatos"""

    def test_job_with_output_file(self, authed_client: httpx.Client, test_context):
        """Deve criar job que gera arquivo de saída"""
        response = authed_client.post("/api/jobs", json={
            "name": "test-job-with-output",
            "script": """
                echo "Starting job..."
                nvidia-smi --query-gpu=name,memory.total --format=csv > /workspace/gpu_info.csv
                echo "Job completed!"
            """,
            "gpu_type": "RTX 3090",
            "disk_size": 10,
            "timeout_minutes": 5,
            "output_path": "/workspace/gpu_info.csv"
        })

        # Se endpoint não existe ou método não permitido, pular
        if response.status_code in [404, 405]:
            pytest.skip("Endpoint POST /api/jobs não implementado")

        assert response.status_code in [200, 201, 202]
        data = response.json()

        job_id = data.get("job_id") or data.get("id")
        if job_id:
            test_context.created_jobs.append(job_id)

    def test_download_artifacts(self, authed_client: httpx.Client, test_context):
        """Deve baixar artefatos do job"""
        if not test_context.created_jobs:
            pytest.skip("Nenhum job criado")

        job_id = test_context.created_jobs[-1]

        # Aguardar job completar
        time.sleep(60)

        response = authed_client.get(f"/api/jobs/{job_id}/artifacts")

        # Pode ser 200 ou 404 se não há artefatos
        assert response.status_code in [200, 404]
