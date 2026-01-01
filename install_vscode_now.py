#!/usr/bin/env python3
"""
Script para instalar code-server em uma máquina Vast.ai existente
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.infrastructure.providers.vast_provider import VastProvider
from src.services.machine_setup_service import MachineSetupService, MachineSetupConfig
from src.core.config import settings

def main():
    print("🔍 Buscando máquinas rodando...")

    # Initialize VastProvider
    vast_api_key = settings.vast.api_key
    if not vast_api_key:
        print("❌ VAST_API_KEY não configurada no .env")
        return 1

    provider = VastProvider(vast_api_key)

    # Get all instances
    instances = provider.list_instances()

    # Filter running instances
    running = [i for i in instances if i.actual_status == "running"]

    if not running:
        print("❌ Nenhuma máquina rodando encontrada")
        print("\nPor favor, crie uma nova máquina no dashboard:")
        print("   http://dumontcloud.orb.local:4890/")
        return 1

    print(f"✅ Encontradas {len(running)} máquina(s) rodando\n")

    # Use the first running machine
    machine = running[0]

    print(f"📦 Instalando VS Code (code-server) na máquina:")
    print(f"   ID: {machine.id}")
    print(f"   GPU: {machine.gpu_name}")
    print(f"   SSH: {machine.ssh_host}:{machine.ssh_port}")
    print()

    # Setup code-server
    try:
        setup_service = MachineSetupService(
            ssh_host=machine.ssh_host,
            ssh_port=machine.ssh_port,
            ssh_user="root"
        )

        config = MachineSetupConfig(
            workspace="/workspace",
            setup_codeserver=True,
            codeserver_port=8080,
            codeserver_auth="none",
            setup_agent=False,  # Don't setup agent, just VS Code
        )

        print("⏳ Instalando code-server (isso pode demorar 1-2 minutos)...\n")

        # Just setup code-server
        result = setup_service.setup_codeserver(config)

        if result.get("success"):
            print(f"\n✅ VS Code instalado com sucesso!")
            print(f"\n🌐 Acesse agora:")
            print(f"   http://{machine.ssh_host}:{config.codeserver_port}/")
            print(f"\n💡 Ou clique no botão 'VS Code > Online (Web)' no dashboard")
            return 0
        else:
            print(f"\n❌ Falha ao instalar: {result.get('error', 'Unknown error')}")
            return 1

    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
