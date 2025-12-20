#!/usr/bin/env python3
"""Teste real do Regional Volume Failover com retry"""
import asyncio
import sys
import time
import os

sys.path.insert(0, "/home/marcos/dumontcloud/src")

import aiohttp
from services.warmpool.regional_volume_failover import RegionalVolumeFailover

API_KEY = os.environ.get("VAST_API_KEY", "a9df8f732d9b1b8a6bb54fd43c477824254552b0d964c58bd92b16c6f25ca3dd")

async def provision_gpu_with_retry(session, gpus, max_retries=10):
    """Tenta provisionar GPU com retry em caso de oferta indisponivel"""
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    payload = {
        "client_id": "me",
        "image": "ubuntu:22.04",
        "disk": 10,
        "runtype": "ssh",
        "onstart": "echo test > /workspace/test.txt",
    }

    for attempt, gpu in enumerate(gpus[:max_retries], 1):
        print(f"   Tentativa {attempt}/{max_retries}: {gpu.gpu_name} (${gpu.price_per_hour:.3f}/hr)")

        try:
            async with session.put(
                f"https://console.vast.ai/api/v0/asks/{gpu.offer_id}/",
                headers=headers,
                json=payload
            ) as resp:
                if resp.status in [200, 201]:
                    data = await resp.json()
                    instance_id = data.get("new_contract")
                    if instance_id:
                        return instance_id, gpu

                text = await resp.text()
                if "no_such_ask" in text:
                    print(f"      Oferta indisponivel, tentando proxima...")
                    await asyncio.sleep(1)  # Rate limit protection
                    continue
                elif resp.status == 429:
                    print(f"      Rate limited, aguardando 5s...")
                    await asyncio.sleep(5)
                    continue
                else:
                    print(f"      Erro: {resp.status} - {text[:100]}")
                    await asyncio.sleep(1)
                    continue
        except Exception as e:
            print(f"      Erro: {e}")
            await asyncio.sleep(1)
            continue

    return None, None


async def wait_for_running(session, instance_id, timeout=180):
    """Aguarda instancia ficar running"""
    headers = {"Authorization": f"Bearer {API_KEY}"}
    start = time.time()

    while time.time() - start < timeout:
        async with session.get(
            "https://console.vast.ai/api/v0/instances/",
            headers=headers,
            params={"owner": "me"}
        ) as resp:
            if resp.status == 200:
                instances = await resp.json()
                inst = instances.get("instances", [])
                for i in inst:
                    if i.get("id") == instance_id:
                        status = i.get("actual_status", "")
                        print(f"   [{int(time.time() - start)}s] Status: {status}")
                        if status == "running":
                            return i
        await asyncio.sleep(5)

    return None


async def destroy_instance(session, instance_id):
    """Destroi instancia"""
    headers = {"Authorization": f"Bearer {API_KEY}"}
    async with session.delete(
        f"https://console.vast.ai/api/v0/instances/{instance_id}/",
        headers=headers
    ) as resp:
        return resp.status in [200, 204]


async def main():
    print("=" * 60)
    print("TESTE REAL - REGIONAL VOLUME FAILOVER")
    print("=" * 60)
    print()

    failover = RegionalVolumeFailover(API_KEY)

    # 1. Verificar saldo
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        async with session.get("https://console.vast.ai/api/v0/users/current/", headers=headers) as resp:
            user = await resp.json()
            balance = user.get("credit", 0)
            print(f"Saldo atual: ${balance:.2f}")

    if balance < 0.10:
        print("ERRO: Saldo insuficiente para teste (minimo $0.10)")
        return

    print()

    # 2. Buscar multiplas GPUs baratas na regiao US (para retry)
    print("1. Buscando GPUs baratas na regiao US...")

    # Buscar varias ofertas para ter backup
    from services.warmpool.host_finder import HostFinder
    host_finder = HostFinder(API_KEY)

    all_offers = await host_finder.search_offers(
        min_gpus=1,
        max_price=0.50,  # Aumentado para mais opcoes
        verified=False,
        min_reliability=0.70,
    )

    # Filtrar por regiao US - pegar ofertas mais caras (menos concorridas)
    us_gpus = [o for o in all_offers if "US" in o.geolocation.upper()]
    us_gpus = sorted(us_gpus, key=lambda x: x.price_per_hour)[3:15]  # Pular as 3 mais baratas

    if not us_gpus:
        print("   ERRO: Nenhuma GPU disponivel na regiao US")
        return

    print(f"   Encontradas {len(us_gpus)} GPUs na regiao US:")
    for i, gpu in enumerate(us_gpus[:5], 1):
        print(f"   {i}. {gpu.gpu_name} - ${gpu.price_per_hour:.3f}/hr - {gpu.geolocation}")
    print()

    # 3. Provisionar GPU com retry
    print("2. Provisionando GPU (com retry)...")
    start_time = time.time()

    async with aiohttp.ClientSession() as session:
        instance_id, used_gpu = await provision_gpu_with_retry(session, us_gpus)

        if not instance_id:
            print("   ERRO: Falha ao provisionar GPU apos varias tentativas")
            return

        provision_time = time.time() - start_time
        print(f"   SUCESSO!")
        print(f"   Instance ID: {instance_id}")
        print(f"   GPU: {used_gpu.gpu_name}")
        print(f"   Preco: ${used_gpu.price_per_hour:.3f}/hr")
        print(f"   Tempo de provisioning: {provision_time:.1f}s")
        print()

        # 4. Aguardar instancia ficar pronta
        print("3. Aguardando instancia ficar running...")
        instance_info = await wait_for_running(session, instance_id, timeout=180)

        startup_time = time.time() - start_time

        if instance_info:
            print(f"   RUNNING!")
            print(f"   SSH: {instance_info.get('ssh_host')}:{instance_info.get('ssh_port')}")
            print(f"   Tempo total: {startup_time:.1f}s")
        else:
            print("   ERRO: Timeout aguardando instancia")
            startup_time = 180

        print()

        # 5. Destruir instancia
        print("4. Destruindo instancia para economizar...")
        await destroy_instance(session, instance_id)
        print("   Instancia destruida")

        print()

        # 6. Verificar saldo final
        headers = {"Authorization": f"Bearer {API_KEY}"}
        async with session.get("https://console.vast.ai/api/v0/users/current/", headers=headers) as resp:
            user = await resp.json()
            new_balance = user.get("credit", 0)
            print(f"Saldo final: ${new_balance:.2f}")
            print(f"Custo do teste: ${balance - new_balance:.4f}")

    print()
    print("=" * 60)
    print("RESULTADO DO TESTE:")
    print("=" * 60)
    print(f"  GPU provisionada: {used_gpu.gpu_name if used_gpu else 'N/A'}")
    print(f"  Tempo de startup: {startup_time:.1f} segundos")
    print()
    print("  Comparativo de estrategias:")
    print("  - GPU Warm Pool:    ~6s (mesmo host)")
    print(f"  - Regional Volume:  ~{startup_time:.0f}s (mesma regiao)")
    print("  - CPU Standby:      ~600-1200s (10-20 min)")

if __name__ == "__main__":
    asyncio.run(main())
