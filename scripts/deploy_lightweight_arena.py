#!/usr/bin/env python3
"""
Deploy DOIS modelos ULTRA-LEVES para Chat Arena do Dumont Cloud
- Modelos: qwen2.5:0.5b e qwen2.5:1.5b (316MB e 934MB)
- Ollama exposto PUBLICAMENTE na porta 11434
- OLLAMA_HOST=0.0.0.0 para aceitar conexões externas
- Testes via HTTP (não SSH)

IMPORTANTE: GASTA CRÉDITOS REAIS NA VAST.AI!
"""
import os
import sys
import time
import json
import subprocess
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.gpu.vast import VastService
from dotenv import load_dotenv

load_dotenv()

VAST_API_KEY = os.getenv("VAST_API_KEY")
if not VAST_API_KEY:
    print("❌ VAST_API_KEY não encontrado no .env")
    sys.exit(1)

# MODELOS ULTRA-LEVES (< 2GB)
MODELS = [
    {
        "name": "Qwen 2.5 0.5B",
        "ollama_model": "qwen2.5:0.5b",
        "size_mb": 316,
        "preferred_gpu": ["RTX 3060", "RTX 3070", "GTX 1660"],
    },
    {
        "name": "Qwen 2.5 1.5B",
        "ollama_model": "qwen2.5:1.5b",
        "size_mb": 934,
        "preferred_gpu": ["RTX 3060", "RTX 3070", "RTX 4060"],
    },
]

# Timeouts
INSTANCE_CREATE_TIMEOUT = 300
INSTANCE_READY_TIMEOUT = 600
SSH_READY_TIMEOUT = 300
MODEL_INSTALL_TIMEOUT = 600  # Modelos leves instalam mais rápido


class LightweightArenaDeployer:
    """Deployer otimizado para modelos ultra-leves"""

    def __init__(self, vast_api_key: str):
        self.vast = VastService(vast_api_key)
        self.deployed_instances = []

    def cleanup_all(self):
        """Limpa todas as instâncias criadas"""
        print("\n🧹 Limpando instâncias criadas...")
        for inst_id in self.deployed_instances:
            try:
                success = self.vast.destroy_instance(inst_id)
                if success:
                    print(f"✅ Instância {inst_id} deletada")
                else:
                    print(f"⚠️  Falha ao deletar instância {inst_id}")
            except Exception as e:
                print(f"❌ Erro ao deletar {inst_id}: {e}")

    def find_cheap_gpu(self, preferred_gpus: List[str]) -> Optional[Dict]:
        """Busca GPU mais barata das preferidas"""
        print(f"\n🔍 Buscando GPUs baratas: {preferred_gpus}")

        # Tentar GPUs preferidas
        for gpu_name in preferred_gpus:
            offers = self.vast.search_offers(
                gpu_name=gpu_name,
                num_gpus=1,
                min_disk=40,
                max_price=0.30,  # Máximo $0.30/hora
                min_reliability=0.80,
                limit=10,
                machine_type="interruptible",
            )

            if offers:
                print(f"✅ Encontradas {len(offers)} ofertas de {gpu_name}")
                return offers[0]

        # Fallback: qualquer GPU barata
        print("⚠️  Nenhuma GPU preferida disponível, buscando alternativas...")
        offers = self.vast.search_offers(
            num_gpus=1,
            min_disk=40,
            max_price=0.30,
            min_reliability=0.75,
            limit=20,
            machine_type="interruptible",
        )

        return offers[0] if offers else None

    def wait_for_ssh(self, ssh_host: str, ssh_port: int, timeout: int = SSH_READY_TIMEOUT) -> bool:
        """Aguarda SSH ficar disponível"""
        print(f"⏳ Aguardando SSH em {ssh_host}:{ssh_port}...")

        start = time.time()
        while time.time() - start < timeout:
            try:
                result = subprocess.run(
                    [
                        "ssh",
                        "-o", "StrictHostKeyChecking=no",
                        "-o", "UserKnownHostsFile=/dev/null",
                        "-o", "ConnectTimeout=5",
                        "-p", str(ssh_port),
                        f"root@{ssh_host}",
                        "echo READY"
                    ],
                    capture_output=True,
                    timeout=10,
                )

                if result.returncode == 0 and b"READY" in result.stdout:
                    elapsed = time.time() - start
                    print(f"✅ SSH disponível em {elapsed:.1f}s")
                    return True
            except Exception:
                pass

            time.sleep(5)

        print(f"❌ Timeout aguardando SSH ({timeout}s)")
        return False

    def install_ollama_public(
        self,
        ssh_host: str,
        ssh_port: int,
        model_name: str,
        timeout: int = MODEL_INSTALL_TIMEOUT
    ) -> Tuple[bool, str]:
        """
        Instala Ollama + modelo com exposição PÚBLICA
        IMPORTANTE: Configura OLLAMA_HOST=0.0.0.0 para aceitar conexões externas
        """
        print(f"\n📦 Instalando Ollama (PÚBLICO) + {model_name}...")

        # Script de instalação com exposição pública
        install_script = f"""#!/bin/bash
set -e

echo "=== Installing Ollama ==="
curl -fsSL https://ollama.com/install.sh | sh

echo "=== Configuring Ollama for PUBLIC access ==="
# CRÍTICO: Expor na porta 0.0.0.0 (não apenas localhost)
export OLLAMA_HOST=0.0.0.0:11434

# Criar serviço systemd para Ollama
cat > /etc/systemd/system/ollama.service <<'EOF'
[Unit]
Description=Ollama Service
After=network.target

[Service]
Type=simple
User=root
Environment="OLLAMA_HOST=0.0.0.0:11434"
ExecStart=/usr/local/bin/ollama serve
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

echo "=== Starting Ollama service ==="
systemctl daemon-reload
systemctl enable ollama
systemctl start ollama

# Aguardar Ollama ficar pronto
echo "=== Waiting for Ollama to be ready ==="
for i in {{1..30}}; do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "Ollama is ready!"
        break
    fi
    echo "Waiting... ($i/30)"
    sleep 2
done

echo "=== Pulling model {model_name} ==="
ollama pull {model_name}

echo "=== Testing model ==="
ollama run {model_name} "What is 2+2? Answer in one word." --verbose

echo "=== Verifying public access ==="
curl -s http://localhost:11434/api/tags || echo "Warning: HTTP test failed"

echo "✅ Installation complete!"
echo "Model: {model_name}"
echo "Endpoint: http://{ssh_host}:11434"
"""

        try:
            # Transferir e executar script
            result = subprocess.run(
                [
                    "ssh",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-p", str(ssh_port),
                    f"root@{ssh_host}",
                    "bash -s"
                ],
                input=install_script.encode(),
                capture_output=True,
                timeout=timeout,
            )

            if result.returncode == 0:
                output = result.stdout.decode()
                print(f"✅ Modelo {model_name} instalado e exposto publicamente!")
                return True, output
            else:
                error = result.stderr.decode()
                print(f"❌ Falha ao instalar modelo: {error}")
                return False, error

        except subprocess.TimeoutExpired:
            return False, f"Timeout installing model (>{timeout}s)"
        except Exception as e:
            return False, f"Exception: {e}"

    def test_http_endpoint(self, endpoint: str) -> Tuple[bool, str]:
        """
        Testa endpoint HTTP do Ollama (não via SSH)
        IMPORTANTE: Valida que a porta está exposta publicamente
        """
        print(f"\n🧪 Testando endpoint HTTP: {endpoint}")

        try:
            # Testar /api/tags
            response = requests.get(f"{endpoint}/api/tags", timeout=10)

            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                print(f"✅ Endpoint HTTP funcionando! Modelos: {len(models)}")
                return True, json.dumps(data, indent=2)
            else:
                return False, f"HTTP {response.status_code}: {response.text}"

        except requests.exceptions.RequestException as e:
            print(f"❌ Falha ao conectar via HTTP: {e}")
            return False, str(e)

    def test_model_generation(self, endpoint: str, model_name: str) -> Tuple[bool, str]:
        """Testa geração de texto via HTTP"""
        print(f"🧪 Testando geração com {model_name}...")

        try:
            response = requests.post(
                f"{endpoint}/api/generate",
                json={
                    "model": model_name,
                    "prompt": "What is 2+2? Answer in one word.",
                    "stream": False
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                answer = data.get("response", "")
                print(f"✅ Modelo respondeu: {answer[:100]}")
                return True, answer
            else:
                return False, f"HTTP {response.status_code}"

        except Exception as e:
            return False, str(e)

    def deploy_model(self, model_config: Dict) -> Optional[Dict]:
        """Deploy completo de um modelo LEVE"""
        model_name = model_config["name"]
        ollama_model = model_config["ollama_model"]
        preferred_gpus = model_config["preferred_gpu"]
        size_mb = model_config["size_mb"]

        print(f"\n{'='*60}")
        print(f"🚀 DEPLOYING: {model_name} ({size_mb}MB)")
        print(f"{'='*60}")

        # 1. Buscar oferta
        offer = self.find_cheap_gpu(preferred_gpus)
        if not offer:
            print(f"❌ Nenhuma oferta disponível para {model_name}")
            return None

        offer_dict = offer if isinstance(offer, dict) else {
            "id": offer.id,
            "gpu_name": offer.gpu_name,
            "dph_total": offer.dph_total,
            "geolocation": offer.geolocation,
        }

        print(f"✅ Oferta selecionada:")
        print(f"   GPU: {offer_dict['gpu_name']}")
        print(f"   Preço: ${offer_dict['dph_total']:.4f}/hora")
        print(f"   Localização: {offer_dict.get('geolocation', 'N/A')}")

        # 2. Criar instância com porta 11434 EXPOSTA
        print(f"\n⏳ Criando instância com porta 11434 exposta...")
        start_create = time.time()

        instance_id = self.vast.create_instance(
            offer_id=offer_dict["id"],
            disk=40,
            label=f"arena-{ollama_model.replace(':', '-')}",
            ports=[11434],  # Apenas Ollama
            use_template=False,
            image="nvidia/cuda:12.1.0-base-ubuntu22.04",
        )

        if not instance_id:
            print(f"❌ Falha ao criar instância")
            return None

        self.deployed_instances.append(instance_id)
        create_time = time.time() - start_create
        print(f"✅ Instância criada: {instance_id} ({create_time:.1f}s)")

        # 3. Aguardar instância ficar running
        print(f"⏳ Aguardando instância ficar running...")
        start_wait = time.time()

        ssh_host = None
        ssh_port = None
        ollama_port = None

        while time.time() - start_wait < INSTANCE_READY_TIMEOUT:
            status = self.vast.get_instance_status(instance_id)

            if status.get("actual_status") == "running":
                ssh_host = status.get("ssh_host")
                ssh_port = status.get("ssh_port")

                # Buscar porta mapeada para 11434
                ports = status.get("ports", {})
                ollama_port = ports.get("11434/tcp")

                if ssh_host and ssh_port:
                    wait_time = time.time() - start_wait
                    print(f"✅ Instância running ({wait_time:.1f}s)")
                    print(f"   SSH: {ssh_host}:{ssh_port}")
                    print(f"   Ollama Port: {ollama_port or 'TBD'}")
                    break

            time.sleep(10)
        else:
            print(f"❌ Timeout aguardando instância ficar running")
            return None

        # 4. Aguardar SSH
        if not self.wait_for_ssh(ssh_host, ssh_port):
            return None

        # 5. Instalar Ollama + modelo (com exposição pública)
        start_install = time.time()
        success, output = self.install_ollama_public(ssh_host, ssh_port, ollama_model)
        install_time = time.time() - start_install

        if not success:
            print(f"❌ Falha na instalação: {output}")
            return None

        print(f"✅ Instalação completa ({install_time:.1f}s)")

        # 6. Determinar endpoint HTTP público
        # VAST.ai mapeia a porta 11434 para uma porta pública
        endpoint = f"http://{ssh_host}:11434"

        # 7. Testar endpoint HTTP (não SSH!)
        print(f"\n⏳ Aguardando endpoint HTTP ficar disponível...")
        time.sleep(10)  # Dar tempo para Ollama iniciar

        http_success, http_output = self.test_http_endpoint(endpoint)

        # 8. Testar geração de texto
        gen_success = False
        gen_output = ""
        if http_success:
            gen_success, gen_output = self.test_model_generation(endpoint, ollama_model)

        return {
            "instance_id": instance_id,
            "model_name": model_name,
            "ollama_model": ollama_model,
            "size_mb": size_mb,
            "gpu_name": offer_dict["gpu_name"],
            "dph_total": offer_dict["dph_total"],
            "ssh_host": ssh_host,
            "ssh_port": ssh_port,
            "ollama_endpoint": endpoint,
            "ollama_port": ollama_port,
            "create_time": create_time,
            "ready_time": wait_time,
            "install_time": install_time,
            "http_test_success": http_success,
            "generation_test_success": gen_success,
            "test_output": gen_output[:200] if gen_output else None,
        }

    def run(self, force: bool = False) -> List[Dict]:
        """Executa deploy de todos os modelos"""
        print("="*60)
        print("🚀 DUMONT CLOUD - LIGHTWEIGHT ARENA DEPLOYMENT")
        print("="*60)
        print(f"Data: {datetime.now().isoformat()}")
        print(f"Modelos: {len(MODELS)}")
        print()

        # Verificar saldo
        balance = self.vast.get_balance()
        credit = balance.get("credit", 0)
        print(f"💰 Saldo VAST.ai: ${credit:.2f}")

        if credit < 0.50 and not force:
            print("⚠️  AVISO: Saldo baixo! Recomendado > $0.50")
            print("❌ Deploy cancelado (use --force para continuar)")
            return []
        elif credit < 0.50:
            print("⚠️  AVISO: Saldo baixo! Continuando com --force...")

        results = []

        try:
            for model_config in MODELS:
                result = self.deploy_model(model_config)
                if result:
                    results.append(result)
                else:
                    print(f"⚠️  Falha no deploy de {model_config['name']}")

                # Delay entre deployments
                if len(results) < len(MODELS):
                    print("\n⏸️  Aguardando 10s antes do próximo deploy...")
                    time.sleep(10)

            # Relatório final
            print("\n" + "="*60)
            print("📊 RELATÓRIO FINAL")
            print("="*60)

            if results:
                total_cost = sum(r["dph_total"] for r in results)
                print(f"\n✅ {len(results)}/{len(MODELS)} modelos deployados!")
                print(f"💰 Custo total: ${total_cost:.4f}/hora")
                print(f"💰 Custo estimado (1h): ${total_cost:.4f}")
                print(f"💰 Custo estimado (24h): ${total_cost * 24:.2f}")

                print("\n📋 ENDPOINTS HTTP PÚBLICOS:")
                for r in results:
                    print(f"\n🔹 {r['model_name']} ({r['size_mb']}MB)")
                    print(f"   ID: {r['instance_id']}")
                    print(f"   GPU: {r['gpu_name']}")
                    print(f"   Endpoint: {r['ollama_endpoint']}")
                    print(f"   Custo: ${r['dph_total']:.4f}/hora")
                    print(f"   HTTP Test: {'✅ OK' if r['http_test_success'] else '❌ FALHOU'}")
                    print(f"   Generation: {'✅ OK' if r['generation_test_success'] else '❌ FALHOU'}")

                print("\n🧪 TESTAR VIA HTTP:")
                for r in results:
                    print(f"\n# {r['model_name']}")
                    print(f"curl {r['ollama_endpoint']}/api/tags")
                    print(f"curl {r['ollama_endpoint']}/api/generate -d '{{\"model\": \"{r['ollama_model']}\", \"prompt\": \"Hello!\", \"stream\": false}}'")

                # Salvar resultados
                output_file = "chat_arena_deployment.json"
                with open(output_file, "w") as f:
                    json.dump({
                        "timestamp": datetime.now().isoformat(),
                        "total_cost_per_hour": total_cost,
                        "instances": results,
                    }, f, indent=2)
                print(f"\n💾 Resultados salvos em: {output_file}")

                print("\n⚠️  IMPORTANTE: Para destruir as instâncias:")
                print(f"python {__file__} --cleanup")

            else:
                print("\n❌ Nenhum modelo foi deployado com sucesso")

            return results

        except KeyboardInterrupt:
            print("\n\n⚠️  Deploy interrompido!")
            self.cleanup_all()
            return results
        except Exception as e:
            print(f"\n❌ Erro durante deploy: {e}")
            import traceback
            traceback.print_exc()
            self.cleanup_all()
            return results


def cleanup_from_file(file_path: str = "chat_arena_deployment.json"):
    """Limpa instâncias de um arquivo de deployment anterior"""
    if not os.path.exists(file_path):
        print(f"❌ Arquivo não encontrado: {file_path}")
        return

    with open(file_path) as f:
        data = json.load(f)

    instances = data.get("instances", [])
    if not instances:
        print("❌ Nenhuma instância encontrada no arquivo")
        return

    print(f"🧹 Limpando {len(instances)} instâncias...")

    vast = VastService(VAST_API_KEY)
    for inst in instances:
        inst_id = inst["instance_id"]
        try:
            success = vast.destroy_instance(inst_id)
            if success:
                print(f"✅ Instância {inst_id} ({inst['model_name']}) deletada")
            else:
                print(f"⚠️  Falha ao deletar instância {inst_id}")
        except Exception as e:
            print(f"❌ Erro ao deletar {inst_id}: {e}")

    print("\n✅ Cleanup completo!")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cleanup":
        cleanup_from_file()
    else:
        force = "--force" in sys.argv
        deployer = LightweightArenaDeployer(VAST_API_KEY)
        deployer.run(force=force)
