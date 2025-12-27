"""
Helpers compartilhados para testes E2E.
Funções resilientes com retry e sem skips.
"""
import pytest
import time
import socket
from typing import Optional

# GPUs caras que NUNCA devem ser usadas em testes
EXPENSIVE_GPUS = ["H100", "A100", "A40", "L40", "H200"]

# Preços progressivos para fallback
PRICE_TIERS = [0.15, 0.25, 0.35, 0.50, 0.75, 1.00]


def get_offer_with_retry(client, max_price: float = 0.50, min_vram: int = 0, gpu_filter: str = None, max_retries: int = 3):
    """
    Busca oferta de GPU com retry e fallback progressivo de preço.
    NUNCA retorna None - falha o teste se não encontrar.
    """
    for attempt in range(max_retries):
        response = client.get("/api/instances/offers")
        if response.status_code != 200:
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            pytest.fail(f"Falha ao buscar ofertas: {response.status_code}")

        offers = response.json()
        if isinstance(offers, dict):
            offers = offers.get("offers", [])

        if not offers:
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            pytest.fail("Nenhuma oferta disponível no mercado")

        # Tentar preços progressivos
        for price_limit in PRICE_TIERS:
            if price_limit > max_price:
                break

            valid = [o for o in offers
                     if (o.get("dph_total") or 999) <= price_limit
                     and not any(exp in o.get("gpu_name", "") for exp in EXPENSIVE_GPUS)]

            # Filtro de VRAM se especificado
            if min_vram > 0:
                valid = [o for o in valid if (o.get("gpu_ram") or 0) >= min_vram * 1024]

            # Filtro de GPU específica
            if gpu_filter:
                filtered = [o for o in valid if gpu_filter.lower() in o.get("gpu_name", "").lower()]
                if filtered:
                    valid = filtered

            if valid:
                # Retorna a mais barata
                return min(valid, key=lambda x: x.get("dph_total", 999))

        # Se não encontrou com filtros, tenta sem filtros (exceto GPUs caras)
        valid = [o for o in offers
                 if (o.get("dph_total") or 999) <= max_price
                 and not any(exp in o.get("gpu_name", "") for exp in EXPENSIVE_GPUS)]

        if valid:
            return min(valid, key=lambda x: x.get("dph_total", 999))

        if attempt < max_retries - 1:
            print(f"  ⏳ Nenhuma oferta encontrada, retry {attempt + 1}/{max_retries}...")
            time.sleep(10 * (attempt + 1))

    pytest.fail(f"Nenhuma oferta disponível após {max_retries} tentativas (max_price=${max_price})")


def create_instance_resilient(client, offer: dict, gpu_cleanup: list, image: str = "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime", disk_size: int = 20, onstart_cmd: str = None, max_retries: int = 3):
    """
    Cria instância com retry automático.
    NUNCA faz skip - falha o teste se não conseguir criar.
    """
    json_data = {
        "offer_id": offer.get("id"),
        "image": image,
        "disk_size": disk_size,
        "skip_validation": True
    }
    if onstart_cmd:
        json_data["onstart_cmd"] = onstart_cmd

    for attempt in range(max_retries):
        response = client.post("/api/instances", json=json_data)

        if response.status_code in [200, 201, 202]:
            instance_id = response.json().get("instance_id") or response.json().get("id")
            gpu_cleanup.append(instance_id)
            return instance_id

        if response.status_code in [429, 500, 502, 503, 504]:
            # Rate limit ou erro temporário - tentar novamente
            if attempt < max_retries - 1:
                wait_time = 10 * (attempt + 1)
                print(f"  ⏳ Erro {response.status_code}, retry {attempt + 1}/{max_retries} em {wait_time}s...")
                time.sleep(wait_time)
                continue

        # Outros erros - falha
        pytest.fail(f"Falha ao criar instância: {response.status_code} - {response.text}")

    pytest.fail(f"Falha ao criar instância após {max_retries} tentativas")


def wait_for_status_resilient(client, instance_id: int, target_statuses: list, timeout: int = 300, interval: int = 5):
    """
    Aguarda instância atingir status desejado.
    NUNCA faz skip - falha o teste se timeout.
    """
    start = time.time()

    while time.time() - start < timeout:
        response = client.get(f"/api/instances/{instance_id}")
        if response.status_code == 200:
            data = response.json()
            status = data.get("status") or data.get("actual_status")

            if status in target_statuses:
                return True, status

            if status in ["failed", "error", "terminated", "destroyed"]:
                pytest.fail(f"Instância {instance_id} entrou em estado de erro: {status}")

        time.sleep(interval)

    current_status = "unknown"
    try:
        response = client.get(f"/api/instances/{instance_id}")
        if response.status_code == 200:
            data = response.json()
            current_status = data.get("status") or data.get("actual_status")
    except:
        pass

    pytest.fail(f"Timeout ({timeout}s) aguardando instância {instance_id} atingir {target_statuses}. Status atual: {current_status}")


def wait_for_ssh(ssh_host: str, ssh_port: int, timeout: int = 120) -> bool:
    """Aguarda SSH ficar disponível"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((ssh_host, int(ssh_port)))
            sock.close()
            if result == 0:
                return True
        except:
            pass
        time.sleep(2)
    return False


def get_cheap_offer(client, max_price: float = 0.50, gpu_filter: str = None):
    """Alias para get_offer_with_retry para compatibilidade"""
    return get_offer_with_retry(client, max_price=max_price, gpu_filter=gpu_filter)
