#!/usr/bin/env python3
"""
Deploy dois modelos leves para Chat Arena do Dumont Cloud
- Provisiona 2 instâncias REAIS na VAST.ai
- Instala Ollama + modelos leves (3B-7B)
- Retorna endpoints prontos para uso

ATENÇÃO: GASTA CRÉDITOS REAIS!
"""
import os
import sys
import time
import json
import subprocess
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

# Configuração dos modelos
MODELS = [
    {
        "name": "Llama 3.2 3B",
        "ollama_model": "llama3.2:3b",
        "preferred_gpu": ["RTX 3080", "RTX 3090", "RTX 4070"],
    },
    {
        "name": "Qwen 2.5 3B",
        "ollama_model": "qwen2.5:3b",
        "preferred_gpu": ["RTX 3060", "RTX 3070", "RTX 4060"],
    },
]

# Timeouts
INSTANCE_CREATE_TIMEOUT = 300  # 5 min
INSTANCE_READY_TIMEOUT = 600   # 10 min
SSH_READY_TIMEOUT = 300        # 5 min
MODEL_INSTALL_TIMEOUT = 900    # 15 min


class ChatArenaDeployer:
    """Deployer para modelos do Chat Arena"""

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
        print(f"\n🔍 Buscando GPUs: {preferred_gpus}")

        for gpu_name in preferred_gpus:
            offers = self.vast.search_offers(
                gpu_name=gpu_name,
                num_gpus=1,
                min_disk=50,
                max_price=0.50,  # Máximo $0.50/hora
                min_reliability=0.85,
                limit=10,
                machine_type="interruptible",  # Spot instances
            )

            if offers:
                print(f"✅ Encontradas {len(offers)} ofertas de {gpu_name}")
                # Retornar a mais barata
                return offers[0]

        # Fallback: qualquer GPU barata
        print("⚠️  Nenhuma GPU preferida disponível, buscando alternativas...")
        offers = self.vast.search_offers(
            num_gpus=1,
            min_disk=50,
            max_price=0.50,
            min_reliability=0.80,
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
                    print(f"✅ SSH disponível em {time.time() - start:.1f}s")
                    return True
            except Exception as e:
                pass

            time.sleep(5)

        print(f"❌ Timeout aguardando SSH ({timeout}s)")
        return False

    def install_ollama_and_model(
        self,
        ssh_host: str,
        ssh_port: int,
        model_name: str,
        timeout: int = MODEL_INSTALL_TIMEOUT
    ) -> Tuple[bool, str]:
        """Instala Ollama e faz pull do modelo"""
        print(f"\n📦 Instalando Ollama + {model_name}...")

        # Script de instalação
        install_script = f"""#!/bin/bash
set -e

# Instalar Ollama
echo "Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

# Iniciar Ollama em background
echo "Starting Ollama..."
nohup ollama serve > /tmp/ollama.log 2>&1 &
sleep 5

# Pull do modelo
echo "Pulling model {model_name}..."
ollama pull {model_name}

# Testar modelo
echo "Testing model..."
ollama run {model_name} "Say 'Hello from {model_name}!' in one sentence." --verbose

echo "✅ Installation complete!"
"""

        try:
            # Transferir script
            script_path = "/tmp/install_ollama.sh"
            result = subprocess.run(
                [
                    "ssh",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-p", str(ssh_port),
                    f"root@{ssh_host}",
                    f"cat > {script_path}"
                ],
                input=install_script.encode(),
                capture_output=True,
                timeout=30,
            )

            if result.returncode != 0:
                return False, f"Failed to upload script: {result.stderr.decode()}"

            # Executar instalação
            result = subprocess.run(
                [
                    "ssh",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-p", str(ssh_port),
                    f"root@{ssh_host}",
                    f"bash {script_path}"
                ],
                capture_output=True,
                timeout=timeout,
            )

            if result.returncode == 0:
                output = result.stdout.decode()
                print(f"✅ Modelo {model_name} instalado com sucesso!")
                return True, output
            else:
                error = result.stderr.decode()
                print(f"❌ Falha ao instalar modelo: {error}")
                return False, error

        except subprocess.TimeoutExpired:
            return False, f"Timeout installing model (>{timeout}s)"
        except Exception as e:
            return False, f"Exception: {e}"

    def test_model_inference(
        self,
        ssh_host: str,
        ssh_port: int,
        model_name: str
    ) -> Tuple[bool, str]:
        """Testa inferência do modelo"""
        print(f"🧪 Testando inferência de {model_name}...")

        try:
            result = subprocess.run(
                [
                    "ssh",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-p", str(ssh_port),
                    f"root@{ssh_host}",
                    f"ollama run {model_name} 'What is 2+2? Answer in one word.'"
                ],
                capture_output=True,
                timeout=60,
            )

            if result.returncode == 0:
                response = result.stdout.decode().strip()
                print(f"✅ Modelo respondeu: {response[:100]}")
                return True, response
            else:
                return False, result.stderr.decode()

        except Exception as e:
            return False, str(e)

    def deploy_model(self, model_config: Dict) -> Optional[Dict]:
        """Deploy completo de um modelo"""
        model_name = model_config["name"]
        ollama_model = model_config["ollama_model"]
        preferred_gpus = model_config["preferred_gpu"]

        print(f"\n{'='*60}")
        print(f"🚀 DEPLOYING: {model_name}")
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

        # 2. Criar instância
        print(f"\n⏳ Criando instância...")
        start_create = time.time()

        instance_id = self.vast.create_instance(
            offer_id=offer_dict["id"],
            disk=50,
            label=f"chat-arena-{ollama_model}",
            ports=[11434, 8080, 22],  # Ollama + extra
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

        while time.time() - start_wait < INSTANCE_READY_TIMEOUT:
            status = self.vast.get_instance_status(instance_id)

            if status.get("status") == "error":
                print(f"❌ Instância em estado de erro")
                return None

            if status.get("actual_status") == "running":
                ssh_host = status.get("ssh_host")
                ssh_port = status.get("ssh_port")

                if ssh_host and ssh_port:
                    wait_time = time.time() - start_wait
                    print(f"✅ Instância running ({wait_time:.1f}s)")
                    print(f"   SSH: {ssh_host}:{ssh_port}")
                    break

            time.sleep(10)
        else:
            print(f"❌ Timeout aguardando instância ficar running")
            return None

        # 4. Aguardar SSH
        if not self.wait_for_ssh(ssh_host, ssh_port):
            return None

        # 5. Instalar Ollama + modelo
        start_install = time.time()
        success, output = self.install_ollama_and_model(ssh_host, ssh_port, ollama_model)
        install_time = time.time() - start_install

        if not success:
            print(f"❌ Falha na instalação: {output}")
            return None

        print(f"✅ Instalação completa ({install_time:.1f}s)")

        # 6. Testar inferência
        test_success, test_output = self.test_model_inference(ssh_host, ssh_port, ollama_model)

        return {
            "instance_id": instance_id,
            "model_name": model_name,
            "ollama_model": ollama_model,
            "gpu_name": offer_dict["gpu_name"],
            "dph_total": offer_dict["dph_total"],
            "ssh_host": ssh_host,
            "ssh_port": ssh_port,
            "ollama_endpoint": f"http://{ssh_host}:11434",
            "create_time": create_time,
            "ready_time": wait_time,
            "install_time": install_time,
            "test_success": test_success,
            "test_output": test_output[:200] if test_output else None,
        }

    def run(self) -> List[Dict]:
        """Executa deploy de todos os modelos"""
        print("="*60)
        print("🚀 DUMONT CLOUD - CHAT ARENA DEPLOYMENT")
        print("="*60)
        print(f"Data: {datetime.now().isoformat()}")
        print(f"Modelos: {len(MODELS)}")
        print()

        # Verificar saldo
        balance = self.vast.get_balance()
        credit = balance.get("credit", 0)
        print(f"💰 Saldo VAST.ai: ${credit:.2f}")

        if credit < 1.0:
            print("⚠️  AVISO: Saldo baixo! Recomendado > $1.00")
            response = input("Continuar? [y/N]: ")
            if response.lower() != "y":
                print("❌ Deploy cancelado")
                return []

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
                print(f"\n✅ {len(results)}/{len(MODELS)} modelos deployados com sucesso!")
                print(f"💰 Custo total: ${total_cost:.4f}/hora")
                print(f"💰 Custo estimado (1h): ${total_cost:.4f}")
                print(f"💰 Custo estimado (24h): ${total_cost * 24:.2f}")

                print("\n📋 INSTÂNCIAS DEPLOYADAS:")
                for r in results:
                    print(f"\n🔹 {r['model_name']}")
                    print(f"   ID: {r['instance_id']}")
                    print(f"   GPU: {r['gpu_name']}")
                    print(f"   SSH: {r['ssh_host']}:{r['ssh_port']}")
                    print(f"   Ollama: {r['ollama_endpoint']}")
                    print(f"   Custo: ${r['dph_total']:.4f}/hora")
                    print(f"   Tempo total: {r['create_time'] + r['ready_time'] + r['install_time']:.1f}s")
                    print(f"   Teste: {'✅ OK' if r['test_success'] else '❌ FALHOU'}")

                # Salvar resultados
                output_file = "chat_arena_deployment.json"
                with open(output_file, "w") as f:
                    json.dump({
                        "timestamp": datetime.now().isoformat(),
                        "total_cost_per_hour": total_cost,
                        "instances": results,
                    }, f, indent=2)
                print(f"\n💾 Resultados salvos em: {output_file}")

                print("\n🎮 CHAT ARENA PRONTO PARA USO!")
                print("\nPara testar os modelos:")
                for r in results:
                    print(f"\n# {r['model_name']}")
                    print(f"ssh -p {r['ssh_port']} root@{r['ssh_host']}")
                    print(f"ollama run {r['ollama_model']}")

                print("\n⚠️  IMPORTANTE: Para destruir as instâncias e parar custos:")
                print(f"python {__file__} --cleanup")
                for r in results:
                    print(f"# Ou manualmente: vast destroy instance {r['instance_id']}")

            else:
                print("\n❌ Nenhum modelo foi deployado com sucesso")

            return results

        except KeyboardInterrupt:
            print("\n\n⚠️  Deploy interrompido pelo usuário!")
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
        deployer = ChatArenaDeployer(VAST_API_KEY)
        deployer.run()
