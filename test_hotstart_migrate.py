#!/usr/bin/env python3
"""
SnapGPU Hot Start + Migrate Integration Test
Teste do fluxo completo de inicializacao otimizada

ESTRATEGIA HOT START + MIGRATE:
1. Buscar 2 ofertas do MESMO tipo de GPU:
   - Oferta RAPIDA (internet alta, preco maior)
   - Oferta BARATA (internet baixa, preco menor)
2. Criar AMBAS as instancias simultaneamente
3. A RAPIDA inicia primeiro (internet mais rapida = boot mais rapido)
4. Restaurar snapshot na RAPIDA
5. Usuario comeca a trabalhar na RAPIDA
6. Quando a BARATA estiver pronta, migrar dados
7. Destruir a RAPIDA, manter a BARATA

ATENCAO: Este teste CUSTA DINHEIRO (2 maquinas)!
Estimativa: ~$0.50-1.00 por execucao completa

Uso:
    python test_hotstart_migrate.py              # Executa teste completo
    python test_hotstart_migrate.py --dry-run    # Apenas simula
    python test_hotstart_migrate.py --gpu "RTX 3090"  # GPU especifica
"""

import requests
import json
import sys
import time
import threading
from datetime import datetime

# Configuracao
BASE_URL = "http://vps-a84d392b.vps.ovh.net:8765"
USERNAME = "marcoslogin"
PASSWORD = "marcos123"

# Cores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    WHITE = '\033[97m'
    END = '\033[0m'
    BOLD = '\033[1m'

def log_success(msg):
    print(f"{Colors.GREEN}[OK]{Colors.END} {msg}")

def log_fail(msg):
    print(f"{Colors.RED}[FAIL]{Colors.END} {msg}")

def log_info(msg):
    print(f"{Colors.BLUE}[INFO]{Colors.END} {msg}")

def log_warn(msg):
    print(f"{Colors.YELLOW}[WARN]{Colors.END} {msg}")

def log_step(step, msg):
    print(f"\n{Colors.CYAN}[STEP {step}]{Colors.END} {Colors.BOLD}{msg}{Colors.END}")

def log_money(msg):
    print(f"{Colors.MAGENTA}[$$$]{Colors.END} {msg}")

def log_fast(msg):
    print(f"{Colors.WHITE}[FAST]{Colors.END} {msg}")

def log_slow(msg):
    print(f"{Colors.YELLOW}[SLOW]{Colors.END} {msg}")


class HotStartMigrateTester:
    def __init__(self, base_url, dry_run=False, target_gpu=None):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.dry_run = dry_run
        self.target_gpu = target_gpu

        # Instancias criadas
        self.fast_instance_id = None
        self.slow_instance_id = None

        # Ofertas selecionadas
        self.fast_offer = None
        self.slow_offer = None

        # Timings
        self.fast_ready_time = None
        self.slow_ready_time = None
        self.start_time = None

        # Custos
        self.total_cost = 0.0

    def login(self):
        """Faz login e obtem cookie de sessao"""
        try:
            resp = self.session.post(
                f"{self.base_url}/login",
                data={"username": USERNAME, "password": PASSWORD},
                allow_redirects=False
            )
            if resp.status_code in [200, 302]:
                log_success(f"Login OK como '{USERNAME}'")
                return True
            else:
                log_fail(f"Login falhou (status={resp.status_code})")
                return False
        except Exception as e:
            log_fail(f"Login erro: {e}")
            return False

    def get_offers_by_speed(self, gpu_filter=None):
        """
        Busca ofertas e separa por velocidade de internet
        Retorna: (fast_offer, slow_offer) do MESMO tipo de GPU
        """
        try:
            resp = self.session.get(f"{self.base_url}/api/offers", timeout=30)
            if resp.status_code != 200:
                log_fail(f"Erro ao buscar ofertas: {resp.status_code}")
                return None, None

            data = resp.json()
            offers = data.get("offers", [])

            if not offers:
                log_fail("Nenhuma oferta disponivel")
                return None, None

            log_info(f"Total de ofertas: {len(offers)}")

            # Agrupar por tipo de GPU
            gpu_groups = {}
            for o in offers:
                gpu = o.get("gpu_name", "Unknown")
                if gpu not in gpu_groups:
                    gpu_groups[gpu] = []
                gpu_groups[gpu].append(o)

            # Mostrar GPUs disponiveis
            log_info(f"GPUs disponiveis:")
            for gpu, gpu_offers in sorted(gpu_groups.items(), key=lambda x: -len(x[1])):
                speeds = [o.get("inet_down", 0) for o in gpu_offers]
                log_info(f"  {gpu}: {len(gpu_offers)} ofertas (internet: {min(speeds):.0f}-{max(speeds):.0f} Mbps)")

            # Filtrar por GPU se especificado
            if gpu_filter:
                matching_gpus = [g for g in gpu_groups.keys() if gpu_filter.lower() in g.lower()]
                if matching_gpus:
                    selected_gpu = matching_gpus[0]
                    offers = gpu_groups[selected_gpu]
                    log_info(f"Selecionada GPU: {selected_gpu} ({len(offers)} ofertas)")
                else:
                    log_warn(f"GPU '{gpu_filter}' nao encontrada, usando a com mais ofertas")
                    gpu_filter = None

            # Se nao especificou GPU ou nao encontrou, usar a que tem mais ofertas com variedade de internet
            if not gpu_filter:
                # Encontrar GPU com maior variedade de velocidades de internet
                best_gpu = None
                best_variety = 0
                for gpu, gpu_offers in gpu_groups.items():
                    if len(gpu_offers) >= 2:
                        speeds = [o.get("inet_down", 0) for o in gpu_offers]
                        variety = max(speeds) - min(speeds)
                        if variety > best_variety:
                            best_variety = variety
                            best_gpu = gpu

                if not best_gpu:
                    # Fallback: GPU com mais ofertas
                    best_gpu = max(gpu_groups.keys(), key=lambda g: len(gpu_groups[g]))

                offers = gpu_groups[best_gpu]
                log_info(f"Auto-selecionada GPU: {best_gpu} ({len(offers)} ofertas, variedade: {best_variety:.0f} Mbps)")

            if len(offers) < 2:
                log_fail(f"Precisamos de pelo menos 2 ofertas da mesma GPU, encontradas: {len(offers)}")
                return None, None

            # Ordenar por velocidade de internet (inet_down)
            offers_sorted = sorted(offers, key=lambda x: float(x.get("inet_down", 0)), reverse=True)

            # Pegar a mais rapida e a mais lenta
            fast_offer = offers_sorted[0]
            slow_offer = offers_sorted[-1]

            # Garantir que sao diferentes
            if fast_offer.get("id") == slow_offer.get("id"):
                if len(offers_sorted) > 1:
                    slow_offer = offers_sorted[1]
                else:
                    log_fail("Apenas uma oferta disponivel")
                    return None, None

            # Verificar que a diferenca de internet e significativa
            fast_speed = float(fast_offer.get("inet_down", 0))
            slow_speed = float(slow_offer.get("inet_down", 0))
            if fast_speed <= slow_speed:
                log_warn("FAST nao e mais rapida que SLOW - trocando")
                fast_offer, slow_offer = slow_offer, fast_offer

            return fast_offer, slow_offer

        except Exception as e:
            log_fail(f"Erro ao buscar ofertas: {e}")
            return None, None

    def create_instance(self, offer_id, label=""):
        """Cria uma instancia vast.ai"""
        if self.dry_run:
            log_warn(f"DRY RUN - Nao criando instancia {label}")
            return {"success": True, "instance_id": f"DRY_RUN_{label}", "dry_run": True}

        try:
            resp = self.session.post(
                f"{self.base_url}/api/create-instance",
                json={
                    "offer_id": offer_id,
                    "snapshot_id": "latest",
                    "image": "pytorch/pytorch:2.0.1-cuda11.7-cudnn8-devel",
                    "disk": 50
                },
                timeout=60
            )

            data = resp.json()

            if data.get("success"):
                instance_id = data.get("instance_id")
                log_success(f"Instancia {label} criada: ID {instance_id}")
                return data
            else:
                log_fail(f"Falha ao criar instancia {label}: {data.get('error', 'Erro desconhecido')}")
                return None
        except Exception as e:
            log_fail(f"Erro ao criar instancia {label}: {e}")
            return None

    def wait_for_instance(self, instance_id, label="", timeout=300, interval=10):
        """Aguarda instancia ficar pronta"""
        if self.dry_run:
            log_warn(f"DRY RUN - Simulando espera {label}...")
            time.sleep(2)
            return {"status": "running", "ssh_host": f"dry.run.{label}", "ssh_port": 22}

        start_time = time.time()
        last_status = None

        while time.time() - start_time < timeout:
            try:
                resp = self.session.get(
                    f"{self.base_url}/api/instance-status/{instance_id}",
                    timeout=30
                )

                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status", "unknown")

                    if status != last_status:
                        elapsed = int(time.time() - start_time)
                        if label == "FAST":
                            log_fast(f"Status: {status} ({elapsed}s)")
                        else:
                            log_slow(f"Status: {status} ({elapsed}s)")
                        last_status = status

                    if status == "running":
                        ssh_host = data.get("ssh_host", "")
                        ssh_port = data.get("ssh_port", "")
                        elapsed = time.time() - start_time
                        if label == "FAST":
                            log_fast(f"PRONTA em {elapsed:.0f}s! SSH: {ssh_host}:{ssh_port}")
                        else:
                            log_slow(f"PRONTA em {elapsed:.0f}s! SSH: {ssh_host}:{ssh_port}")
                        return data
                    elif status in ["exited", "error", "destroyed"]:
                        log_fail(f"Instancia {label} falhou: {status}")
                        return None

                time.sleep(interval)
            except Exception as e:
                log_warn(f"Erro ao verificar status {label}: {e}")
                time.sleep(interval)

        log_fail(f"Timeout ({timeout}s) aguardando instancia {label}")
        return None

    def simulate_restore(self, instance_id, label=""):
        """Simula restauracao de snapshot (ou chama API real)"""
        if self.dry_run:
            log_warn(f"DRY RUN - Simulando restore em {label}")
            time.sleep(1)
            return True

        # Em producao, chamaria /api/restore-snapshot
        log_info(f"Restaurando snapshot em {label}...")
        # Por enquanto apenas simula
        time.sleep(2)
        log_success(f"Restore simulado em {label}")
        return True

    def simulate_migrate(self, source_id, target_id):
        """Simula migracao de dados entre instancias"""
        if self.dry_run:
            log_warn("DRY RUN - Simulando migracao")
            time.sleep(1)
            return True

        # Em producao, chamaria /api/migrate
        log_info(f"Migrando dados de {source_id} para {target_id}...")
        # Por enquanto apenas simula
        time.sleep(3)
        log_success("Migracao simulada com sucesso")
        return True

    def destroy_instance(self, instance_id, label=""):
        """Destroi uma instancia"""
        if self.dry_run:
            log_warn(f"DRY RUN - Nao destruindo instancia {label}")
            return True

        try:
            resp = self.session.delete(
                f"{self.base_url}/api/destroy-instance/{instance_id}",
                timeout=30
            )

            data = resp.json()

            if data.get("success"):
                log_success(f"Instancia {label} ({instance_id}) destruida")
                return True
            else:
                log_fail(f"Falha ao destruir {label}: {data.get('error', 'Erro desconhecido')}")
                return False
        except Exception as e:
            log_fail(f"Erro ao destruir instancia {label}: {e}")
            return False

    def cleanup(self):
        """Limpa todas as instancias criadas"""
        log_warn("Limpando instancias...")
        if self.fast_instance_id and not self.dry_run:
            self.destroy_instance(self.fast_instance_id, "FAST")
        if self.slow_instance_id and not self.dry_run:
            self.destroy_instance(self.slow_instance_id, "SLOW")

    def run_hotstart_migrate_test(self):
        """
        Executa o teste completo de Hot Start + Migrate

        Fluxo:
        1. Buscar ofertas FAST e SLOW do mesmo tipo de GPU
        2. Criar AMBAS as instancias simultaneamente
        3. Aguardar FAST ficar pronta (deve ser mais rapida)
        4. Restaurar dados na FAST
        5. Aguardar SLOW ficar pronta
        6. Migrar dados da FAST para SLOW
        7. Destruir FAST, manter SLOW rodando
        8. Verificar que SLOW esta funcionando
        """
        print(f"\n{'='*70}")
        print(f"{Colors.BOLD}SnapGPU Hot Start + Migrate Test{Colors.END}")
        print(f"{'='*70}")
        print(f"URL: {self.base_url}")
        print(f"Dry Run: {self.dry_run}")
        print(f"GPU Filter: {self.target_gpu or 'Auto'}")
        print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")

        self.start_time = time.time()
        success = True

        try:
            # Step 1: Login
            log_step(1, "Autenticacao")
            if not self.login():
                return False

            # Step 2: Buscar ofertas FAST e SLOW
            log_step(2, "Buscando ofertas FAST e SLOW do mesmo tipo de GPU")
            self.fast_offer, self.slow_offer = self.get_offers_by_speed(self.target_gpu)

            if not self.fast_offer or not self.slow_offer:
                return False

            # Mostrar comparacao
            print(f"\n{Colors.BOLD}Comparacao de Ofertas:{Colors.END}")
            print(f"{'─'*60}")
            print(f"{'':15} {'FAST (internet alta)':20} {'SLOW (internet baixa)':20}")
            print(f"{'─'*60}")
            print(f"{'GPU:':<15} {self.fast_offer.get('gpu_name', '?'):<20} {self.slow_offer.get('gpu_name', '?'):<20}")
            print(f"{'Preco/h:':<15} ${self.fast_offer.get('dph_total', 0):<19.4f} ${self.slow_offer.get('dph_total', 0):<19.4f}")
            print(f"{'Download:':<15} {self.fast_offer.get('inet_down', 0):<20.0f} {self.slow_offer.get('inet_down', 0):<20.0f} Mbps")
            print(f"{'Upload:':<15} {self.fast_offer.get('inet_up', 0):<20.0f} {self.slow_offer.get('inet_up', 0):<20.0f} Mbps")
            print(f"{'VRAM:':<15} {self.fast_offer.get('gpu_ram', 0)/1024:<20.0f} {self.slow_offer.get('gpu_ram', 0)/1024:<20.0f} GB")
            print(f"{'─'*60}")

            fast_price = float(self.fast_offer.get('dph_total', 0))
            slow_price = float(self.slow_offer.get('dph_total', 0))
            savings = fast_price - slow_price
            log_money(f"Economia apos migracao: ${savings:.4f}/hora ({savings/fast_price*100:.1f}%)")

            # Step 3: Criar AMBAS as instancias simultaneamente
            log_step(3, "Criando AMBAS as instancias simultaneamente")

            # Criar FAST
            fast_result = self.create_instance(self.fast_offer["id"], "FAST")
            if not fast_result:
                return False
            self.fast_instance_id = fast_result.get("instance_id")

            # Criar SLOW
            slow_result = self.create_instance(self.slow_offer["id"], "SLOW")
            if not slow_result:
                self.cleanup()
                return False
            self.slow_instance_id = slow_result.get("instance_id")

            log_success(f"Duas instancias criadas: FAST={self.fast_instance_id}, SLOW={self.slow_instance_id}")

            # Step 4: Aguardar FAST ficar pronta (em paralelo com SLOW)
            log_step(4, "Aguardando FAST ficar pronta (internet mais rapida = boot mais rapido)")

            # Iniciar threads para monitorar ambas
            fast_info = [None]
            slow_info = [None]

            def wait_fast():
                fast_info[0] = self.wait_for_instance(self.fast_instance_id, "FAST", timeout=300)
                if fast_info[0]:
                    self.fast_ready_time = time.time() - self.start_time

            def wait_slow():
                slow_info[0] = self.wait_for_instance(self.slow_instance_id, "SLOW", timeout=400)
                if slow_info[0]:
                    self.slow_ready_time = time.time() - self.start_time

            fast_thread = threading.Thread(target=wait_fast)
            slow_thread = threading.Thread(target=wait_slow)

            fast_thread.start()
            slow_thread.start()

            # Aguardar FAST primeiro
            fast_thread.join()

            if not fast_info[0]:
                log_fail("FAST nao ficou pronta")
                slow_thread.join()
                self.cleanup()
                return False

            # Step 5: Restaurar dados na FAST
            log_step(5, "Restaurando snapshot na FAST (usuario pode comecar a trabalhar)")
            self.simulate_restore(self.fast_instance_id, "FAST")
            log_success("Usuario pode comecar a trabalhar na FAST!")

            # Step 6: Aguardar SLOW ficar pronta
            log_step(6, "Aguardando SLOW ficar pronta (em background)")
            slow_thread.join()

            if not slow_info[0]:
                log_warn("SLOW nao ficou pronta - usuario continua na FAST")
                # Nao falha o teste, apenas nao migra
            else:
                # Step 7: Migrar dados da FAST para SLOW
                log_step(7, "Migrando dados da FAST para SLOW")
                self.simulate_migrate(self.fast_instance_id, self.slow_instance_id)

                # Step 8: Destruir FAST
                log_step(8, "Destruindo FAST (mais cara)")
                self.destroy_instance(self.fast_instance_id, "FAST")
                self.fast_instance_id = None  # Ja destruida

                log_success(f"Usuario agora usa SLOW (economia de ${savings:.4f}/hora)!")

            # Step 9: Verificar estado final
            log_step(9, "Verificando estado final")
            if not self.dry_run and self.slow_instance_id:
                resp = self.session.get(f"{self.base_url}/api/instance-status/{self.slow_instance_id}", timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    log_info(f"SLOW status: {data.get('status', '?')}")
                    if data.get("ssh_host"):
                        log_info(f"SSH: ssh -p {data.get('ssh_port')} root@{data.get('ssh_host')}")

            # Step 10: Destruir SLOW (cleanup do teste)
            log_step(10, "Limpeza - Destruindo SLOW")
            if self.slow_instance_id:
                self.destroy_instance(self.slow_instance_id, "SLOW")
                self.slow_instance_id = None

        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Interrompido pelo usuario!{Colors.END}")
            self.cleanup()
            success = False

        except Exception as e:
            log_fail(f"Erro inesperado: {e}")
            self.cleanup()
            success = False

        # Resumo
        total_time = time.time() - self.start_time
        print(f"\n{'='*70}")
        print(f"{Colors.BOLD}RESUMO DO TESTE HOT START + MIGRATE{Colors.END}")
        print(f"{'='*70}")
        print(f"Tempo total: {total_time:.0f}s")

        if self.fast_ready_time:
            print(f"FAST pronta em: {self.fast_ready_time:.0f}s")
        if self.slow_ready_time:
            print(f"SLOW pronta em: {self.slow_ready_time:.0f}s")

        if self.fast_ready_time and self.slow_ready_time:
            time_saved = self.slow_ready_time - self.fast_ready_time
            print(f"{Colors.GREEN}Tempo economizado para usuario: {time_saved:.0f}s{Colors.END}")

        if success:
            print(f"\n{Colors.GREEN}{Colors.BOLD}TESTE PASSOU!{Colors.END}")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}TESTE FALHOU!{Colors.END}")

        return success


def main():
    global BASE_URL

    dry_run = "--dry-run" in sys.argv
    target_gpu = None

    # Parse argumentos
    if "--gpu" in sys.argv:
        idx = sys.argv.index("--gpu")
        if idx + 1 < len(sys.argv):
            target_gpu = sys.argv[idx + 1]

    if "--url" in sys.argv:
        idx = sys.argv.index("--url")
        if idx + 1 < len(sys.argv):
            BASE_URL = sys.argv[idx + 1]

    if "--local" in sys.argv:
        BASE_URL = "http://localhost:8765"

    # Confirmacao antes de gastar dinheiro
    if not dry_run:
        print(f"\n{Colors.RED}{Colors.BOLD}ATENCAO: Este teste VAI CUSTAR DINHEIRO!{Colors.END}")
        print("DUAS instancias vast.ai serao criadas.")
        print("Estimativa de custo: $0.50-1.00")
        print("Use --dry-run para testar sem criar recursos.\n")

        confirm = input("Deseja continuar? (s/N): ").strip().lower()
        if confirm != 's':
            print("Cancelado.")
            sys.exit(0)

    tester = HotStartMigrateTester(BASE_URL, dry_run=dry_run, target_gpu=target_gpu)
    success = tester.run_hotstart_migrate_test()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
