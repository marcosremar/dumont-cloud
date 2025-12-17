"""
Agente de monitoramento de mercado VAST.ai expandido.

Coleta:
- Todos os tipos de máquinas (on-demand, interruptible, bid)
- Métricas de performance (TFLOPS, DLPerf, bandwidth)
- Dados de confiabilidade de provedores
- Calcula rankings de custo-benefício
"""

import time
import logging
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict

from src.services.agent_manager import Agent
from src.infrastructure.providers.vast_provider import VastProvider
from src.config.database import SessionLocal
from src.models.metrics import (
    MarketSnapshot,
    ProviderReliability,
    CostEfficiencyRanking,
)
from src.domain.models.gpu_offer import GpuOffer

logger = logging.getLogger(__name__)


class MarketMonitorAgent(Agent):
    """
    Agente expandido de monitoramento de mercado VAST.ai.

    Coleta dados de todos os tipos de máquinas e calcula:
    - Estatísticas de mercado agregadas
    - Rankings de confiabilidade de provedores
    - Rankings de custo-benefício
    """

    MACHINE_TYPES = ["on-demand", "interruptible", "bid"]

    DEFAULT_GPUS = [
        # RTX 40 Series
        "RTX 4090", "RTX 4080", "RTX 4080 SUPER", "RTX 4070", "RTX 4070 Ti", "RTX 4070 Ti SUPER",
        # RTX 30 Series
        "RTX 3090", "RTX 3090 Ti", "RTX 3080", "RTX 3080 Ti", "RTX 3070", "RTX 3070 Ti",
        # Data Center
        "A100", "A100 SXM4 80GB", "A100 PCIe", "A100-SXM4-80GB",
        "H100", "H100 PCIe", "H100 SXM5", "H100 NVL",
        "A6000", "A5000", "A4000", "A40",
        "L40S", "L40", "L4",
        # RTX 50 Series (novas)
        "RTX 5090", "RTX 5080",
    ]

    def __init__(
        self,
        vast_api_key: str,
        interval_minutes: int = 15,
        gpus_to_monitor: Optional[List[str]] = None,
        machine_types: Optional[List[str]] = None,
    ):
        """
        Inicializa o agente de monitoramento de mercado.

        Args:
            vast_api_key: API key da VAST.ai
            interval_minutes: Intervalo de monitoramento em minutos (padrão: 15)
            gpus_to_monitor: Lista de GPUs para monitorar (padrão: DEFAULT_GPUS)
            machine_types: Lista de tipos de máquina (padrão: MACHINE_TYPES)
        """
        super().__init__(name="MarketMonitor")
        self.vast_provider = VastProvider(api_key=vast_api_key)
        self.interval_seconds = interval_minutes * 60
        self.gpus_to_monitor = gpus_to_monitor or self.DEFAULT_GPUS
        self.machine_types = machine_types or self.MACHINE_TYPES

        # Cache para detecção de mudanças
        self.last_snapshots: Dict[str, Dict] = {}

    def run(self):
        """Loop principal do agente."""
        logger.info(f"MarketMonitor iniciando: {len(self.gpus_to_monitor)} GPUs, "
                    f"{len(self.machine_types)} tipos, intervalo={self.interval_seconds/60}min")

        while self.running:
            try:
                self._monitor_cycle()
            except Exception as e:
                logger.error(f"Erro no ciclo de monitoramento: {e}", exc_info=True)

            if self.running:
                logger.info(f"Próximo ciclo em {self.interval_seconds/60} minutos...")
                self.sleep(self.interval_seconds)

    def _monitor_cycle(self):
        """Executa um ciclo completo de monitoramento."""
        logger.info("=" * 60)
        logger.info(f"Ciclo de monitoramento - {datetime.utcnow()}")
        logger.info("=" * 60)

        # 1. Coletar dados de mercado
        all_offers = self._collect_market_data()

        if not all_offers:
            logger.warning("Nenhuma oferta coletada neste ciclo")
            return

        # 2. Salvar snapshots agregados
        self._save_market_snapshots(all_offers)

        # 3. Atualizar dados de provedores
        self._update_provider_data(all_offers)

        # 4. Calcular e salvar rankings de eficiência
        self._calculate_efficiency_rankings(all_offers)

        logger.info("Ciclo de monitoramento concluído")

    def _collect_market_data(self) -> Dict[str, List[GpuOffer]]:
        """Coleta dados de todas as GPUs e tipos de máquina."""
        all_offers = {}
        total_collected = 0

        for gpu_name in self.gpus_to_monitor:
            for machine_type in self.machine_types:
                key = f"{gpu_name}:{machine_type}"
                try:
                    offers = self.vast_provider.search_offers_by_type(
                        machine_type=machine_type,
                        gpu_name=gpu_name,
                        max_price=100.0,  # Alto para capturar todas
                        limit=200,
                    )
                    all_offers[key] = offers
                    total_collected += len(offers)

                    if offers:
                        logger.debug(f"{key}: {len(offers)} ofertas, "
                                     f"min=${min(o.dph_total for o in offers):.4f}/h")
                except Exception as e:
                    logger.warning(f"Falha ao coletar {key}: {e}")
                    all_offers[key] = []

        logger.info(f"Total coletado: {total_collected} ofertas em "
                    f"{len([k for k, v in all_offers.items() if v])} combinações")
        return all_offers

    def _save_market_snapshots(self, all_offers: Dict[str, List[GpuOffer]]):
        """Salva snapshots agregados no banco de dados."""
        db = SessionLocal()
        try:
            timestamp = datetime.utcnow()
            snapshots_saved = 0

            for key, offers in all_offers.items():
                if not offers:
                    continue

                gpu_name, machine_type = key.split(":")
                stats = self._calculate_stats(offers)

                snapshot = MarketSnapshot(
                    timestamp=timestamp,
                    gpu_name=gpu_name,
                    machine_type=machine_type,
                    min_price=stats['min_price'],
                    max_price=stats['max_price'],
                    avg_price=stats['avg_price'],
                    median_price=stats['median_price'],
                    percentile_25=stats.get('p25'),
                    percentile_75=stats.get('p75'),
                    total_offers=stats['total_offers'],
                    available_gpus=stats['available_gpus'],
                    verified_offers=stats['verified_offers'],
                    avg_reliability=stats.get('avg_reliability'),
                    avg_total_flops=stats.get('avg_total_flops'),
                    avg_dlperf=stats.get('avg_dlperf'),
                    avg_gpu_mem_bw=stats.get('avg_gpu_mem_bw'),
                    min_cost_per_tflops=stats.get('min_cost_per_tflops'),
                    avg_cost_per_tflops=stats.get('avg_cost_per_tflops'),
                    min_cost_per_gb_vram=stats.get('min_cost_per_gb_vram'),
                    region_distribution=stats.get('region_distribution'),
                )
                db.add(snapshot)
                snapshots_saved += 1

            db.commit()
            logger.info(f"Salvos {snapshots_saved} snapshots de mercado")

        except Exception as e:
            logger.error(f"Erro ao salvar snapshots: {e}")
            db.rollback()
        finally:
            db.close()

    def _calculate_stats(self, offers: List[GpuOffer]) -> Dict:
        """Calcula estatísticas agregadas das ofertas."""
        if not offers:
            return {
                'min_price': 0, 'max_price': 0, 'avg_price': 0,
                'median_price': 0, 'total_offers': 0, 'available_gpus': 0,
                'verified_offers': 0
            }

        # Extrair valores
        prices = [o.dph_total for o in offers if o.dph_total > 0]
        reliabilities = [o.reliability for o in offers if o.reliability and o.reliability > 0]
        flops = [o.total_flops for o in offers if o.total_flops and o.total_flops > 0]
        dlperfs = [o.dlperf for o in offers if o.dlperf and o.dlperf > 0]
        gpu_bws = [o.gpu_mem_bw for o in offers if o.gpu_mem_bw and o.gpu_mem_bw > 0]
        cost_tflops = [o.cost_per_tflops for o in offers if o.cost_per_tflops and o.cost_per_tflops > 0]
        cost_vram = [o.cost_per_gb_vram for o in offers if o.cost_per_gb_vram and o.cost_per_gb_vram > 0]

        # Distribuição por região
        regions = defaultdict(int)
        for o in offers:
            region = self._classify_region(o.geolocation)
            regions[region] += 1

        # Calcular percentis
        sorted_prices = sorted(prices) if prices else []
        n = len(sorted_prices)
        p25 = sorted_prices[n // 4] if n >= 4 else None
        p75 = sorted_prices[3 * n // 4] if n >= 4 else None

        return {
            'min_price': min(prices) if prices else 0,
            'max_price': max(prices) if prices else 0,
            'avg_price': statistics.mean(prices) if prices else 0,
            'median_price': statistics.median(prices) if prices else 0,
            'p25': p25,
            'p75': p75,
            'total_offers': len(offers),
            'available_gpus': sum(o.num_gpus for o in offers),
            'verified_offers': sum(1 for o in offers if o.verified),
            'avg_reliability': statistics.mean(reliabilities) if reliabilities else None,
            'avg_total_flops': statistics.mean(flops) if flops else None,
            'avg_dlperf': statistics.mean(dlperfs) if dlperfs else None,
            'avg_gpu_mem_bw': statistics.mean(gpu_bws) if gpu_bws else None,
            'min_cost_per_tflops': min(cost_tflops) if cost_tflops else None,
            'avg_cost_per_tflops': statistics.mean(cost_tflops) if cost_tflops else None,
            'min_cost_per_gb_vram': min(cost_vram) if cost_vram else None,
            'region_distribution': dict(regions),
        }

    def _classify_region(self, geolocation: str) -> str:
        """Classifica geolocalização em região."""
        if not geolocation:
            return "OTHER"
        geo_upper = geolocation.upper()
        if any(x in geo_upper for x in ["US", "UNITED STATES", "CA", "CANADA"]):
            return "US"
        if any(x in geo_upper for x in ["DE", "FR", "NL", "GB", "UK", "ES", "IT", "PL",
                                         "GERMANY", "FRANCE", "SPAIN", "EUROPE", "SWEDEN",
                                         "NORWAY", "FINLAND", "BELGIUM", "AUSTRIA"]):
            return "EU"
        if any(x in geo_upper for x in ["JP", "KR", "SG", "TW", "JAPAN", "KOREA", "ASIA",
                                         "SINGAPORE", "TAIWAN", "CHINA", "HK", "HONG KONG"]):
            return "ASIA"
        return "OTHER"

    def _update_provider_data(self, all_offers: Dict[str, List[GpuOffer]]):
        """Atualiza dados de confiabilidade de provedores."""
        db = SessionLocal()
        try:
            # Agrupar ofertas por machine_id
            providers = defaultdict(list)
            for offers in all_offers.values():
                for offer in offers:
                    if offer.machine_id:
                        providers[offer.machine_id].append(offer)

            providers_updated = 0
            for machine_id, machine_offers in providers.items():
                # Buscar ou criar registro
                provider = db.query(ProviderReliability).filter(
                    ProviderReliability.machine_id == machine_id
                ).first()

                if not provider:
                    provider = ProviderReliability(
                        machine_id=machine_id,
                        first_seen=datetime.utcnow()
                    )
                    db.add(provider)

                # Atualizar com dados mais recentes
                latest = machine_offers[0]
                provider.hostname = latest.hostname
                provider.geolocation = latest.geolocation
                provider.verified = latest.verified
                provider.gpu_name = latest.gpu_name
                provider.last_seen = datetime.utcnow()
                provider.last_updated = datetime.utcnow()

                # Incrementar contadores
                provider.total_observations = (provider.total_observations or 0) + 1
                provider.times_available = (provider.times_available or 0) + 1

                # Atualizar preços
                prices = [o.dph_total for o in machine_offers if o.dph_total > 0]
                if prices:
                    min_price = min(prices)
                    max_price = max(prices)
                    avg_price = statistics.mean(prices)

                    if provider.min_price_seen is None or min_price < provider.min_price_seen:
                        provider.min_price_seen = min_price
                    if provider.max_price_seen is None or max_price > provider.max_price_seen:
                        provider.max_price_seen = max_price

                    # Média móvel exponencial
                    if provider.avg_price:
                        provider.avg_price = provider.avg_price * 0.9 + avg_price * 0.1
                    else:
                        provider.avg_price = avg_price

                # Performance
                flops = [o.total_flops for o in machine_offers if o.total_flops]
                if flops:
                    provider.avg_total_flops = statistics.mean(flops)

                dlperfs = [o.dlperf for o in machine_offers if o.dlperf]
                if dlperfs:
                    provider.avg_dlperf = statistics.mean(dlperfs)

                # Calcular scores
                self._calculate_provider_scores(provider)
                providers_updated += 1

            db.commit()
            logger.info(f"Atualizados {providers_updated} provedores")

        except Exception as e:
            logger.error(f"Erro ao atualizar provedores: {e}")
            db.rollback()
        finally:
            db.close()

    def _calculate_provider_scores(self, provider: ProviderReliability):
        """Calcula scores de confiabilidade do provedor."""
        # Availability score (% de vezes disponível)
        if provider.total_observations and provider.total_observations > 0:
            provider.availability_score = (
                (provider.times_available or 0) / provider.total_observations
            )

        # Price stability score (menor variação = melhor)
        if provider.min_price_seen and provider.max_price_seen and provider.avg_price:
            price_range = provider.max_price_seen - provider.min_price_seen
            if provider.avg_price > 0:
                stability = 1 - min(price_range / provider.avg_price, 1)
                provider.price_stability_score = max(0, stability)

        # Reliability score composto
        reliability_factors = []

        # Availability weight: 40%
        if provider.availability_score:
            reliability_factors.append(provider.availability_score * 0.4)

        # Price stability weight: 30%
        if provider.price_stability_score:
            reliability_factors.append(provider.price_stability_score * 0.3)

        # Verified bonus: 20%
        if provider.verified:
            reliability_factors.append(0.2)

        # History bonus: 10% (mais observações = mais confiável)
        if provider.total_observations and provider.total_observations > 100:
            reliability_factors.append(0.1)
        elif provider.total_observations and provider.total_observations > 50:
            reliability_factors.append(0.05)

        provider.reliability_score = sum(reliability_factors)

    def _calculate_efficiency_rankings(self, all_offers: Dict[str, List[GpuOffer]]):
        """Calcula e salva rankings de custo-benefício."""
        db = SessionLocal()
        try:
            timestamp = datetime.utcnow()
            all_ranked = []

            for key, offers in all_offers.items():
                gpu_name, machine_type = key.split(":")

                for offer in offers:
                    # Pular ofertas sem dados de performance
                    if not offer.total_flops or offer.total_flops <= 0:
                        continue
                    if not offer.dph_total or offer.dph_total <= 0:
                        continue

                    # Calcular efficiency score (0-100)
                    score = self._calculate_efficiency_score(offer)

                    ranking = CostEfficiencyRanking(
                        timestamp=timestamp,
                        offer_id=offer.id,
                        gpu_name=gpu_name,
                        machine_type=machine_type,
                        dph_total=offer.dph_total,
                        total_flops=offer.total_flops,
                        gpu_ram=offer.gpu_ram,
                        dlperf=offer.dlperf,
                        gpu_mem_bw=offer.gpu_mem_bw,
                        cost_per_tflops=offer.cost_per_tflops,
                        cost_per_gb_vram=offer.cost_per_gb_vram,
                        cost_per_dlperf=(offer.dph_total / offer.dlperf
                                         if offer.dlperf and offer.dlperf > 0 else None),
                        efficiency_score=score,
                        reliability=offer.reliability,
                        verified=offer.verified,
                        geolocation=offer.geolocation,
                        machine_id=offer.machine_id,
                    )
                    all_ranked.append(ranking)

            # Ordenar por score e atribuir ranks
            all_ranked.sort(key=lambda x: x.efficiency_score, reverse=True)
            for i, ranking in enumerate(all_ranked):
                ranking.rank_overall = i + 1

            # Rank por classe de GPU
            gpu_ranks = defaultdict(list)
            for r in all_ranked:
                gpu_ranks[r.gpu_name].append(r)

            for gpu_name, rankings in gpu_ranks.items():
                for i, r in enumerate(rankings):
                    r.rank_in_gpu_class = i + 1

            # Salvar top 1000 (para não sobrecarregar o banco)
            for ranking in all_ranked[:1000]:
                db.add(ranking)

            db.commit()
            logger.info(f"Salvos {min(len(all_ranked), 1000)} rankings de eficiência")

        except Exception as e:
            logger.error(f"Erro ao calcular rankings: {e}")
            db.rollback()
        finally:
            db.close()

    def _calculate_efficiency_score(self, offer: GpuOffer) -> float:
        """
        Calcula score de eficiência (0-100).

        Combina múltiplos fatores com pesos:
        - Custo/TFLOPS: 40%
        - Custo/GB VRAM: 20%
        - Reliability: 25%
        - Verified: 10%
        - DLPerf: 5%
        """
        score = 0.0

        # Custo por TFLOPS (peso 40%)
        # Normalizar: $0.01/TFLOPS = 100 pontos, $0.10/TFLOPS = 10 pontos
        if offer.cost_per_tflops and offer.cost_per_tflops > 0:
            tflops_score = min(100, 1.0 / offer.cost_per_tflops)
            score += tflops_score * 0.4

        # Custo por GB VRAM (peso 20%)
        # Normalizar: $0.01/GB = 50 pontos
        if offer.cost_per_gb_vram and offer.cost_per_gb_vram > 0:
            vram_score = min(100, 0.5 / offer.cost_per_gb_vram)
            score += vram_score * 0.2

        # Reliability (peso 25%)
        if offer.reliability and offer.reliability > 0:
            score += offer.reliability * 100 * 0.25

        # Verified bonus (peso 10%)
        if offer.verified:
            score += 10

        # DLPerf bonus (peso 5%)
        if offer.dlperf and offer.dlperf > 0:
            dlperf_norm = min(100, offer.dlperf / 100)
            score += dlperf_norm * 0.05

        return min(100, max(0, score))

    def get_stats(self) -> Dict:
        """Retorna estatísticas do agente."""
        return {
            'name': self.name,
            'running': self.is_running(),
            'interval_minutes': self.interval_seconds / 60,
            'gpus_monitored': self.gpus_to_monitor,
            'machine_types': self.machine_types,
            'last_snapshots': self.last_snapshots,
        }
