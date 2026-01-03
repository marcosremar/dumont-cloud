#!/usr/bin/env python3
"""
Deploy TINY models for Chat Arena testing
- Uses the smallest/cheapest models available
- Minimizes cost while still providing real comparisons

ATENÇÃO: GASTA CRÉDITOS REAIS (mas mínimos)!
"""
import os
import sys
import time
import json
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.gpu.vast import VastService
from dotenv import load_dotenv

load_dotenv()

VAST_API_KEY = os.getenv("VAST_API_KEY")
if not VAST_API_KEY:
    print("❌ VAST_API_KEY não encontrado no .env")
    sys.exit(1)

# Smallest models for testing
TINY_MODELS = [
    {
        "name": "TinyLlama 1.1B",
        "ollama_model": "tinyllama",  # ~600MB, very fast
        "preferred_gpu": ["RTX 3060", "RTX 3070", "RTX 3080"],
    },
    {
        "name": "Qwen2 0.5B",
        "ollama_model": "qwen2:0.5b",  # ~350MB, fastest
        "preferred_gpu": ["RTX 3060", "RTX 3070", "RTX 3080"],
    },
]

class TinyArenaDeployer:
    """Deploys minimal models for Chat Arena testing"""

    def __init__(self, vast_api_key: str):
        self.vast = VastService(vast_api_key)
        self.deployed = []

    def find_cheapest_gpu(self) -> Optional[Dict]:
        """Find the cheapest available GPU"""
        print("🔍 Buscando GPU mais barata disponível...")

        # Search for very cheap offers
        offers = self.vast.search_offers(
            num_gpus=1,
            min_disk=30,
            max_price=0.20,  # Max $0.20/hour
            min_reliability=0.80,
            limit=20,
            machine_type="interruptible",
        )

        if offers:
            offer = offers[0]
            offer_dict = offer if isinstance(offer, dict) else {
                "id": offer.id,
                "gpu_name": offer.gpu_name,
                "dph_total": offer.dph_total,
            }
            print(f"✅ Encontrada: {offer_dict['gpu_name']} - ${offer_dict['dph_total']:.4f}/hr")
            return offer_dict

        print("❌ Nenhuma GPU barata disponível")
        return None

    def deploy_model(self, model_config: Dict, offer: Dict) -> Optional[Dict]:
        """Deploy a single model"""
        model_name = model_config["name"]
        ollama_model = model_config["ollama_model"]

        print(f"\n📦 Deploying {model_name}...")

        try:
            # Create instance
            instance_id = self.vast.create_instance(
                offer_id=offer["id"],
                disk=30,
                label=f"arena-{ollama_model}",
                ports=[11434],
                use_template=False,
                image="ollama/ollama",  # Use official Ollama image
            )

            if not instance_id:
                print(f"❌ Falha ao criar instância")
                return None

            self.deployed.append(instance_id)
            print(f"✅ Instância criada: {instance_id}")

            # Wait for running
            print("⏳ Aguardando instância...")
            for _ in range(60):  # 5 min timeout
                status = self.vast.get_instance_status(instance_id)
                if status.get("actual_status") == "running":
                    ip = status.get("public_ipaddr")
                    ports = status.get("ports", {})

                    # Get Ollama port
                    ollama_port = None
                    if ports and "11434/tcp" in ports:
                        mappings = ports["11434/tcp"]
                        if mappings:
                            ollama_port = mappings[0].get("HostPort")

                    if ip and ollama_port:
                        print(f"✅ Running: {ip}:{ollama_port}")

                        return {
                            "instance_id": instance_id,
                            "model_name": model_name,
                            "ollama_model": ollama_model,
                            "gpu_name": offer["gpu_name"],
                            "price_per_hour": offer["dph_total"],
                            "ip": ip,
                            "port": ollama_port,
                            "ollama_url": f"http://{ip}:{ollama_port}",
                        }

                time.sleep(5)

            print("❌ Timeout aguardando instância")
            return None

        except Exception as e:
            print(f"❌ Erro: {e}")
            return None

    def pull_model(self, result: Dict) -> bool:
        """Pull model to the instance via Ollama API"""
        import requests

        ollama_url = result["ollama_url"]
        model = result["ollama_model"]

        print(f"📥 Pulling {model}...")

        try:
            # Wait for Ollama to be ready
            for _ in range(30):
                try:
                    r = requests.get(f"{ollama_url}/api/tags", timeout=5)
                    if r.ok:
                        break
                except:
                    time.sleep(2)
            else:
                print("❌ Ollama não respondeu")
                return False

            # Pull model
            r = requests.post(
                f"{ollama_url}/api/pull",
                json={"name": model},
                timeout=600,  # 10 min for download
                stream=True,
            )

            if r.ok:
                # Stream the progress
                for line in r.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            status = data.get("status", "")
                            if "pulling" in status or "downloading" in status:
                                print(f"  {status}", end='\r')
                            elif "success" in status:
                                print(f"\n✅ {model} baixado!")
                                return True
                        except:
                            pass

            return False

        except Exception as e:
            print(f"❌ Erro no pull: {e}")
            return False

    def test_model(self, result: Dict) -> bool:
        """Test model inference"""
        import requests

        ollama_url = result["ollama_url"]
        model = result["ollama_model"]

        print(f"🧪 Testando {model}...")

        try:
            r = requests.post(
                f"{ollama_url}/api/chat",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Say hello in 5 words"}],
                    "stream": False,
                },
                timeout=60,
            )

            if r.ok:
                data = r.json()
                response = data.get("message", {}).get("content", "")
                print(f"✅ Resposta: {response[:50]}")
                return True
            else:
                print(f"❌ Erro: {r.status_code}")
                return False

        except Exception as e:
            print(f"❌ Erro: {e}")
            return False

    def run(self) -> List[Dict]:
        """Deploy all models"""
        print("="*60)
        print("🚀 TINY ARENA MODELS DEPLOYMENT")
        print("="*60)
        print(f"Data: {datetime.now().isoformat()}")
        print(f"Modelos: {len(TINY_MODELS)}")
        print()

        # Check balance
        balance = self.vast.get_balance()
        credit = balance.get("credit", 0)
        print(f"💰 Saldo: ${credit:.2f}")

        if credit < 0.50:
            print("⚠️ Saldo muito baixo!")
            return []

        results = []

        # Find one cheap GPU (we'll reuse for multiple models if possible)
        offer = self.find_cheapest_gpu()
        if not offer:
            return []

        # Deploy each model
        for model_config in TINY_MODELS:
            result = self.deploy_model(model_config, offer)
            if result:
                # Pull the model
                if self.pull_model(result):
                    # Test it
                    result["test_passed"] = self.test_model(result)
                    results.append(result)
                else:
                    print(f"⚠️ Falha no pull de {model_config['name']}")

        # Summary
        print("\n" + "="*60)
        print("📊 DEPLOYMENT SUMMARY")
        print("="*60)

        if results:
            total_cost = sum(r["price_per_hour"] for r in results)
            print(f"\n✅ {len(results)}/{len(TINY_MODELS)} modelos deployados!")
            print(f"💰 Custo: ${total_cost:.4f}/hora")

            print("\n📋 MODELOS PRONTOS:")
            for r in results:
                print(f"\n  {r['model_name']}")
                print(f"    URL: {r['ollama_url']}")
                print(f"    Modelo: {r['ollama_model']}")
                print(f"    GPU: {r['gpu_name']}")
                print(f"    Teste: {'✅' if r.get('test_passed') else '❌'}")

            # Save results
            output = {
                "timestamp": datetime.now().isoformat(),
                "models": results,
                "total_cost_per_hour": total_cost,
            }

            with open("tiny_arena_deployment.json", "w") as f:
                json.dump(output, f, indent=2)

            print("\n💾 Salvo em: tiny_arena_deployment.json")
            print("\n🎮 Chat Arena pronto para uso!")

        else:
            print("\n❌ Nenhum modelo deployado")

        return results

    def cleanup(self):
        """Clean up all deployed instances"""
        print("\n🧹 Limpando instâncias...")
        for inst_id in self.deployed:
            try:
                self.vast.destroy_instance(inst_id)
                print(f"✅ {inst_id} deletada")
            except Exception as e:
                print(f"⚠️ Erro: {e}")


def cleanup_from_file():
    """Cleanup instances from previous deployment"""
    if not os.path.exists("tiny_arena_deployment.json"):
        print("❌ Arquivo não encontrado")
        return

    with open("tiny_arena_deployment.json") as f:
        data = json.load(f)

    vast = VastService(VAST_API_KEY)

    for model in data.get("models", []):
        inst_id = model.get("instance_id")
        if inst_id:
            try:
                vast.destroy_instance(inst_id)
                print(f"✅ {inst_id} deletada")
            except Exception as e:
                print(f"⚠️ {inst_id}: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cleanup":
        cleanup_from_file()
    else:
        deployer = TinyArenaDeployer(VAST_API_KEY)
        try:
            deployer.run()
        except KeyboardInterrupt:
            print("\n\n⚠️ Interrompido!")
            deployer.cleanup()
