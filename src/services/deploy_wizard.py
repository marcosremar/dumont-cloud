"""
DeployWizard Service - Gerenciamento inteligente de deploy de maquinas GPU

Estrategia OTIMIZADA v2:
1. Usa ollama/ollama (imagem LEVE, ja tem Ollama pronto)
2. Instala SSH rapidamente via onstart script
3. Configura chave RSA do usuario
4. Cria maquinas em paralelo (batch de 5)
5. Verificacao paralela do status (ThreadPool)
6. CHECK_INTERVAL de 2s para resposta mais rapida
"""
import time
import uuid
import threading
import subprocess
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.services.gpu.vast import VastService
from src.services.codeserver_service import CodeServerService, CodeServerConfig


# Configuracoes do Wizard
SPEED_TIERS = {
    "slow": {"min": 100, "max": 500, "name": "Lenta"},
    "medium": {"min": 500, "max": 2000, "name": "Media"},
    "fast": {"min": 2000, "max": 4000, "name": "Rapida"},
    "ultra": {"min": 4000, "max": 99999, "name": "Ultra"},
}

GPU_OPTIONS = [
    "RTX 5090", "RTX 4090", "RTX 4080", "RTX 3090", "RTX 3080",
    "RTX A6000", "RTX A5000", "RTX A4000", "A100", "H100", "L40S"
]

REGIONS = {
    "global": [],
    "US": ["US", "United States", "CA", "Canada"],
    "EU": ["ES", "DE", "FR", "NL", "IT", "PL", "CZ", "BG", "UK", "GB",
           "Spain", "Germany", "France", "Netherlands", "Poland",
           "Czechia", "Bulgaria", "Sweden", "Norway", "Finland"],
    "ASIA": ["JP", "Japan", "KR", "Korea", "SG", "Singapore", "TW", "Taiwan"],
}

# Configuracoes de timeout e batches - OTIMIZADO
BATCH_TIMEOUT = 60   # 60s timeout (ollama/ollama e leve!)
CHECK_INTERVAL = 2   # 2s para resposta mais rapida
BATCH_SIZE = 5       # maquinas por batch
MAX_BATCHES = 3      # maximo de batches (15 maquinas total)

# Imagens Docker disponiveis (ordenadas por velocidade de carregamento)
# Baseado em pesquisa: https://mveg.es/posts/optimizing-pytorch-docker-images-cut-size-by-60percent/
DOCKER_IMAGES = {
    # ULTRA RAPIDAS (< 30s) - Sem PyTorch
    "cuda-base": "nvidia/cuda:12.1.0-base-ubuntu22.04",          # ~200MB, mais leve
    "cuda-runtime": "nvidia/cuda:12.1.0-runtime-ubuntu22.04",    # ~1.5GB
    "ollama": "ollama/ollama",                                    # ~2GB, Ollama pronto
    
    # RAPIDAS (30-60s) - Com PyTorch otimizado
    "pytorch": "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",  # ~3GB, PyTorch oficial
    "pytorch-slim": "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",  # ~3GB (alias)
    
    # MEDIAS (60-120s) - PyTorch + SSH pronto
    "vastai-pytorch": "vastai/pytorch",                          # ~4-5GB, PyTorch+SSH
    
    # LENTAS (>120s) - Pesadas mas completas
    "vastai": "vastai/base-image",                               # ~8GB, SSH pronto
    "base": "nvidia/cuda:12.1.0-runtime-ubuntu22.04",            # Alias para base
}

# Chave publica SSH do usuario (configurada para acesso)
SSH_PUBLIC_KEY = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDI5VNl7OpRdO8MdavBMFI4DPDKpXGKu/UwpJxbGJf3stWKLvv/7q0Z8Jza/ugpNfdYOYK7/Ovg2Mzr838hG4meixuECgcNLGPQWuuA7YObPlelzER65z805L21bv9HCStN1bqlviOrKgNHX+DwttLRNo8d/4MVtbrTtDPrOIoO2pcZyYbm16U3GeJYZgwPnuAufiSErdBpB/R2k+hFRD1b6+BGeHRw7ttT2LiyOvq1507VwSrWfc4mzcb91DhwT54wQYts98+7g552uFpPeZmxisEGh2/yWcn8+T45zYMG0wo0vdgLih0qXVM+mtlMJ9r++K3O1mz9Uit/nPZzRhXDw0rCpzkBTi8EFYg/uoBZYG5pURKlIO1c2GlqBLglIc42ZgwwEoExv+Ktt1Z2eV29Q4Ji1/V9QzuSUxPkhpXUQrLcLkqDVwbzJBY44DDwGUdWVxu0LQAZLK+AMO6sAT25fT2eRXGFZKYPaI840UWvJo6m9sVe2QSzBSvJ13i3BKKIed82/D5cQrgpqRAT8PldWhYsjRlxWhV3HTDT8lQptIRLPfth0miYymDf9ebstbHf4YxTvR7FfJe0T3mnV3oCz/GdxiW1mlm5AtfwnKbfw4TedDnsMVOyh/VPVDNhJ3BLnTsIjlsVVa3En90CNPmpzqKd+bzi801FYMaldSk2Lw== marcosremar@gmail.com"

# Script para instalar SSH rapidamente no container ollama/ollama
# Este script instala openssh-server, configura chave publica e inicia sshd
SSH_INSTALL_SCRIPT = f"""
apt-get update && apt-get install -y --no-install-recommends openssh-server && \
mkdir -p /var/run/sshd /root/.ssh && \
echo "{SSH_PUBLIC_KEY}" > /root/.ssh/authorized_keys && \
chmod 700 /root/.ssh && chmod 600 /root/.ssh/authorized_keys && \
echo "PermitRootLogin yes" >> /etc/ssh/sshd_config && \
echo "PubkeyAuthentication yes" >> /etc/ssh/sshd_config && \
/usr/sbin/sshd
"""


@dataclass
class DeployConfig:
    """Configuracao de deploy do wizard"""
    speed_tier: str = "fast"
    gpu_name: Optional[str] = None
    region: str = "global"
    disk_space: int = 50
    max_price: float = 2.0
    snapshot_id: Optional[str] = None
    target_path: str = "/workspace"
    hot_start: bool = False
    docker_options: Optional[str] = None
    setup_codeserver: bool = False  # OTIMIZADO: desabilitado por padrao
    use_ollama_image: bool = True   # usar ollama/ollama + SSH install
    image: Optional[str] = None     # imagem customizada


class DeployJob:
    """Representa um job de deploy em andamento"""

    def __init__(self, job_id: str, config: DeployConfig):
        self.id = job_id
        self.config = config
        self.status = "starting"
        self.message = "Iniciando deploy..."
        self.created_at = time.time()

        # Progresso
        self.batch = 0
        self.machines_tried = 0
        self.machines_created = []
        self.machines_destroyed = []
        self.offers_found = 0

        # Resultado
        self.result = None
        self.error = None
        self.setup_result = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "status": self.status,
            "message": self.message,
            "created_at": self.created_at,
            "config": {
                "speed_tier": self.config.speed_tier,
                "gpu_name": self.config.gpu_name,
                "region": self.config.region,
                "disk_space": self.config.disk_space,
                "max_price": self.config.max_price,
                "setup_codeserver": self.config.setup_codeserver,
                "use_ollama_image": self.config.use_ollama_image,
            },
            "progress": {
                "batch": self.batch,
                "machines_tried": self.machines_tried,
                "machines_created": len(self.machines_created),
                "machines_destroyed": len(self.machines_destroyed),
                "offers_found": self.offers_found,
            },
            "result": self.result,
            "error": self.error,
            "setup_result": self.setup_result,
        }


class DeployWizardService:
    """
    Servico centralizado de deploy com estrategia de multi-start OTIMIZADA v2.

    Otimizacoes implementadas:
    - Usa ollama/ollama (imagem LEVE, ~2GB vs ~8GB do vastai/base-image)
    - Instala SSH rapidamente via onstart script
    - Configura chave RSA do usuario automaticamente
    - CHECK_INTERVAL de 2s para resposta rapida
    - BATCH_TIMEOUT de 60s (imagem leve carrega rapido)
    """

    def __init__(self, api_key: str):
        self.vast = VastService(api_key)
        self.jobs: Dict[str, DeployJob] = {}

    def get_offers(self, config: DeployConfig) -> List[dict]:
        """Busca ofertas baseado na configuracao do wizard"""
        tier = SPEED_TIERS.get(config.speed_tier, SPEED_TIERS["fast"])

        offers = self.vast.search_offers(
            gpu_name=config.gpu_name,
            min_inet_down=tier["min"],
            max_price=config.max_price,
            min_disk=config.disk_space,
            region=config.region if config.region != "global" else None,
            limit=BATCH_SIZE * MAX_BATCHES * 2
        )

        # Filtrar por velocidade maxima do tier (exceto ultra)
        if config.speed_tier != "ultra":
            offers = [o for o in offers if o.get("inet_down", 0) < tier["max"]]

        # Ordenar por velocidade de internet (mais rapido primeiro)
        offers.sort(key=lambda o: o.get("inet_down", 0), reverse=True)

        return offers

    def get_offers_preview(self, config: DeployConfig) -> dict:
        """Preview de ofertas por tier de velocidade"""
        offers = self.vast.search_offers(
            gpu_name=config.gpu_name,
            min_inet_down=100,
            max_price=config.max_price,
            min_disk=config.disk_space,
            region=config.region if config.region != "global" else None,
            limit=200
        )

        tiers_summary = {}
        for tier_name, tier_config in SPEED_TIERS.items():
            tier_offers = [
                o for o in offers
                if tier_config["min"] <= o.get("inet_down", 0) < tier_config["max"]
            ]

            if tier_offers:
                prices = [o["dph_total"] for o in tier_offers]
                speeds = [o["inet_down"] for o in tier_offers]
                tiers_summary[tier_name] = {
                    "count": len(tier_offers),
                    "min_price": min(prices),
                    "max_price": max(prices),
                    "avg_speed": sum(speeds) / len(speeds),
                    "gpus": list(set(o["gpu_name"] for o in tier_offers))[:5]
                }
            else:
                tiers_summary[tier_name] = {
                    "count": 0, "min_price": None, "max_price": None,
                    "avg_speed": None, "gpus": []
                }

        return {
            "total_offers": len(offers),
            "tiers": tiers_summary,
            "gpu_options": GPU_OPTIONS,
            "regions": list(REGIONS.keys()),
        }

    def _test_ssh_connection(self, ssh_host: str, ssh_port: int, timeout: int = 5) -> bool:
        """Testa se a conexao SSH esta disponivel"""
        try:
            result = subprocess.run(
                ["ssh", "-i", "/home/marcos/.ssh/id_rsa", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=3",
                 "-o", "BatchMode=yes", "-p", str(ssh_port), f"root@{ssh_host}", "echo ok"],
                capture_output=True, timeout=timeout, text=True
            )
            return result.returncode == 0 and "ok" in result.stdout
        except Exception:
            return False

    def _check_instance_status(self, instance_id: int) -> Optional[dict]:
        """
        Verifica status de uma instancia.

        Considera a maquina pronta quando:
        - Status e "running"
        - Tem ssh_host e ssh_port validos
        - Conexao SSH responde (teste rapido)
        """
        try:
            status = self.vast.get_instance_status(instance_id)
            actual_status = status.get("status")

            ssh_host = status.get("ssh_host")
            ssh_port = status.get("ssh_port")
            print(f"[DEBUG] Instance {instance_id}: status={actual_status}, ssh_host={ssh_host}, ssh_port={ssh_port}", flush=True)

            # Aceita "running" se tem SSH
            if actual_status == "running":
                if ssh_host and ssh_port:
                    # Testa conexao SSH rapidamente
                    if self._test_ssh_connection(ssh_host, int(ssh_port)):
                        print(f"[DEBUG] Instance {instance_id} is READY! SSH OK at {ssh_host}:{ssh_port}", flush=True)
                        return {
                            "instance_id": instance_id,
                            "public_ip": ssh_host,
                            "ssh_port": int(ssh_port),
                            "gpu_name": status.get("gpu_name"),
                        }
                    else:
                        print(f"[DEBUG] Instance {instance_id}: SSH not yet available", flush=True)
            return None
        except Exception as e:
            print(f"[DEBUG] Instance {instance_id} error: {e}", flush=True)
            return None

    def _check_instances_parallel(self, instances: List[tuple], destroyed: List[int]) -> Optional[dict]:
        """
        Verifica status de multiplas instancias em PARALELO.
        """
        active_instances = [(id, offer) for id, offer in instances if id not in destroyed]
        
        if not active_instances:
            return None
        
        with ThreadPoolExecutor(max_workers=len(active_instances)) as executor:
            future_to_instance = {
                executor.submit(self._check_instance_status, instance_id): (instance_id, offer)
                for instance_id, offer in active_instances
            }
            
            for future in as_completed(future_to_instance, timeout=10):
                try:
                    result = future.result()
                    if result:
                        instance_id, offer = future_to_instance[future]
                        result["offer_id"] = offer["id"]
                        result["inet_down"] = offer.get("inet_down", 0)
                        result["dph_total"] = offer.get("dph_total", 0)
                        return result
                except Exception:
                    pass
        
        return None

    def _create_instance(self, offer: dict, config: DeployConfig) -> Optional[int]:
        """Cria uma instancia e retorna o ID"""
        try:
            # Selecionar imagem
            if config.image:
                image = config.image
                onstart_cmd = None
            elif config.use_ollama_image:
                # ollama/ollama e LEVE! Instalar SSH via script
                image = DOCKER_IMAGES["ollama"]
                onstart_cmd = SSH_INSTALL_SCRIPT
            else:
                # Usar vastai/base-image (pesada, mas tem SSH)
                image = DOCKER_IMAGES["vastai"]
                onstart_cmd = "curl -fsSL https://ollama.com/install.sh | sh && nohup ollama serve > /var/log/ollama.log 2>&1 &"
            
            instance_id = self.vast.create_instance(
                offer_id=offer["id"],
                image=image,
                disk=config.disk_space,
                docker_options=config.docker_options,
                onstart_cmd=onstart_cmd,
                use_template=False,  # Nao usar template, usar imagem diretamente
            )
            return instance_id
        except Exception as e:
            print(f"[DEBUG] Failed to create instance: {e}", flush=True)
            return None

    def _setup_codeserver(self, ssh_host: str, ssh_port: int, workspace: str = "/workspace") -> dict:
        """Instala e configura code-server na instancia."""
        try:
            config = CodeServerConfig(
                port=8080,
                workspace=workspace,
                theme="Default Dark+",
                trust_enabled=False,
                user="root",
            )

            codeserver = CodeServerService(ssh_host, ssh_port, "root")
            result = codeserver.setup_full(config)

            return {
                "success": result.get("success", False),
                "port": config.port,
                "message": result.get("message", ""),
                "steps": result.get("steps", [])
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _run_deploy(self, job: DeployJob):
        """
        Executa o deploy em background com estrategia multi-start OTIMIZADA v2.
        """
        try:
            job.status = "searching"
            job.message = "Buscando ofertas..."

            # Buscar ofertas
            offers = self.get_offers(job.config)
            job.offers_found = len(offers)

            if not offers:
                job.status = "failed"
                job.error = "Nenhuma oferta disponivel com os filtros especificados"
                return

            winner = None
            all_created = []
            deploy_start = time.time()

            # Mostrar imagem sendo usada
            if job.config.use_ollama_image:
                print(f"[INFO] Usando imagem LEVE: {DOCKER_IMAGES["ollama"]} + SSH install script", flush=True)
            else:
                print(f"[INFO] Usando imagem pesada: {DOCKER_IMAGES["vastai"]}", flush=True)

            # Multi-start em batches
            for batch_num in range(MAX_BATCHES):
                if winner:
                    break

                job.batch = batch_num + 1
                start_idx = batch_num * BATCH_SIZE
                batch_offers = offers[start_idx:start_idx + BATCH_SIZE]

                if not batch_offers:
                    break

                # Criar maquinas em paralelo
                job.status = "creating"
                job.message = f"Batch {batch_num + 1}: Criando {len(batch_offers)} maquinas..."

                with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
                    create_futures = {
                        executor.submit(self._create_instance, offer, job.config): offer
                        for offer in batch_offers
                    }

                    for future in as_completed(create_futures, timeout=30):
                        try:
                            instance_id = future.result()
                            offer = create_futures[future]
                            job.machines_tried += 1

                            if instance_id:
                                all_created.append((instance_id, offer))
                                job.machines_created.append(instance_id)
                                job.message = f"Criada maquina {instance_id}"
                        except Exception:
                            pass

                # Monitorar todas as maquinas do batch
                job.status = "waiting"
                batch_start = time.time()

                while time.time() - batch_start < BATCH_TIMEOUT:
                    elapsed = int(time.time() - deploy_start)
                    job.message = f"Aguardando maquinas... ({elapsed}s, {len(all_created)} criadas)"

                    # Verificacao paralela de todas as instancias
                    result = self._check_instances_parallel(all_created, job.machines_destroyed)
                    
                    if result:
                        winner = result
                        winner["ready_time"] = time.time() - deploy_start
                        job.status = "ready"
                        job.message = f"Maquina {result["instance_id"]} pronta em {winner["ready_time"]:.1f}s!"
                        break

                    time.sleep(CHECK_INTERVAL)

                if not winner:
                    job.message = f"Batch {batch_num + 1}: Nenhuma maquina ficou pronta em {BATCH_TIMEOUT}s"

            # Cleanup - destruir todas as maquinas nao utilizadas
            print(f"[CLEANUP] winner={winner}", flush=True)
            job.status = "cleanup"
            job.message = "Destruindo maquinas nao utilizadas..."

            for instance_id, offer in all_created:
                winner_id = winner.get("instance_id") if winner else None
                if not winner or instance_id != winner_id:
                    if instance_id not in job.machines_destroyed:
                        try:
                            print(f"[CLEANUP] Destroying instance {instance_id}", flush=True)
                            self.vast.destroy_instance(instance_id)
                            job.machines_destroyed.append(instance_id)
                        except:
                            pass
                else:
                    print(f"[CLEANUP] KEEPING winner instance {instance_id}", flush=True)

            if not winner:
                job.status = "failed"
                job.error = f"Nenhuma maquina ficou pronta em {BATCH_TIMEOUT}s apos {job.machines_tried} tentativas"
                return

            # Setup code-server se habilitado
            if job.config.setup_codeserver:
                job.status = "setting_up"
                job.message = "Instalando code-server..."

                setup_result = self._setup_codeserver(
                    ssh_host=winner["public_ip"],
                    ssh_port=winner["ssh_port"],
                    workspace=job.config.target_path
                )
                job.setup_result = setup_result

                if setup_result.get("success"):
                    job.message = f"code-server instalado na porta {setup_result.get(port)}"
                else:
                    job.message = f"code-server falhou: {setup_result.get('error', 'erro desconhecido')}"

            # Sucesso!
            job.status = "completed"
            job.message = "Deploy concluido!"
            job.result = {
                "success": True,
                "instance_id": winner["instance_id"],
                "public_ip": winner["public_ip"],
                "ssh_port": winner["ssh_port"],
                "ssh_command": f"ssh -p {winner["ssh_port"]} root@{winner["public_ip"]}",
                "gpu_name": winner.get("gpu_name"),
                "inet_down": winner.get("inet_down"),
                "dph_total": winner.get("dph_total"),
                "ready_time": winner.get("ready_time"),
                "total_time": time.time() - job.created_at,
                "codeserver_port": 8080 if job.config.setup_codeserver else None,
                "ollama_ready": job.config.use_ollama_image,
            }

        except Exception as e:
            job.status = "failed"
            job.error = str(e)

            # Cleanup em caso de erro
            for instance_id, offer in getattr(job, "_all_created", []):
                if instance_id not in job.machines_destroyed:
                    try:
                        self.vast.destroy_instance(instance_id)
                    except:
                        pass

    def start_deploy(self, config: DeployConfig) -> DeployJob:
        """Inicia um novo deploy em background"""
        job_id = str(uuid.uuid4())[:8]
        job = DeployJob(job_id, config)
        self.jobs[job_id] = job

        thread = threading.Thread(
            target=self._run_deploy,
            args=(job,),
            daemon=True
        )
        thread.start()

        return job

    def get_job(self, job_id: str) -> Optional[DeployJob]:
        """Retorna um job pelo ID"""
        return self.jobs.get(job_id)

    def list_jobs(self, limit: int = 20) -> List[DeployJob]:
        """Lista os ultimos jobs"""
        jobs = list(self.jobs.values())
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs[:limit]


# Singleton para armazenar jobs entre requests
_wizard_jobs: Dict[str, DeployJob] = {}


def get_wizard_service(api_key: str) -> DeployWizardService:
    """Factory para criar o servico do wizard"""
    service = DeployWizardService(api_key)
    service.jobs = _wizard_jobs
    return service
