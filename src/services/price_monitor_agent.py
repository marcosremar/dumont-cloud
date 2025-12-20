"""
Agente de monitoramento de preços de GPUs.

Monitora preços de GPUs específicas (RTX 4090, RTX 4050) a cada 30 minutos,
salvando estatísticas no banco de dados e detectando mudanças significativas.
"""

import time
import logging
import json
import statistics
from datetime import datetime
from typing import List, Dict, Optional

from src.services.agent_manager import Agent
from src.services.gpu.vast import VastService
from src.config.database import SessionLocal
from src.models.price_history import PriceHistory, PriceAlert

logger = logging.getLogger(__name__)


class PriceMonitorAgent(Agent):
    """Agente que monitora preços de GPUs na Vast.ai."""

    def __init__(self, vast_api_key: str, interval_minutes: int = 30, gpus_to_monitor: List[str] = None):
        """
        Inicializa o agente de monitoramento de preços.

        Args:
            vast_api_key: API key da Vast.ai
            interval_minutes: Intervalo de monitoramento em minutos (padrão: 30)
            gpus_to_monitor: Lista de GPUs para monitorar (padrão: ['RTX 4090', 'RTX 4080'])
        """
        super().__init__(name="PriceMonitor")
        self.vast_service = VastService(api_key=vast_api_key)
        self.interval_seconds = interval_minutes * 60
        self.gpus_to_monitor = gpus_to_monitor or ['RTX 4090', 'RTX 4080']
        self.last_prices: Dict[str, float] = {}  # Cache dos últimos preços médios

    def run(self):
        """Loop principal do agente."""
        logger.info(f"Iniciando monitoramento de preços para: {', '.join(self.gpus_to_monitor)}")
        logger.info(f"Intervalo de monitoramento: {self.interval_seconds/60} minutos")

        while self.running:
            try:
                self._monitor_cycle()
            except Exception as e:
                logger.error(f"Erro no ciclo de monitoramento: {e}", exc_info=True)

            # Aguardar próximo ciclo (sleep interrompível)
            if self.running:
                logger.info(f"Próximo monitoramento em {self.interval_seconds/60} minutos...")
                self.sleep(self.interval_seconds)

    def _monitor_cycle(self):
        """Executa um ciclo completo de monitoramento."""
        logger.info("=" * 60)
        logger.info(f"Iniciando ciclo de monitoramento - {datetime.utcnow()}")
        logger.info("=" * 60)

        for gpu_name in self.gpus_to_monitor:
            try:
                self._monitor_gpu(gpu_name)
            except Exception as e:
                logger.error(f"Erro ao monitorar {gpu_name}: {e}", exc_info=True)

        logger.info("Ciclo de monitoramento concluído")

    def _monitor_gpu(self, gpu_name: str):
        """
        Monitora preços de uma GPU específica.

        Args:
            gpu_name: Nome da GPU (ex: 'RTX 4090')
        """
        logger.info(f"Buscando ofertas para {gpu_name}...")

        # Buscar ofertas na Vast.ai
        offers = self._fetch_offers(gpu_name)

        if not offers:
            logger.warning(f"Nenhuma oferta encontrada para {gpu_name}")
            return

        logger.info(f"Encontradas {len(offers)} ofertas para {gpu_name}")

        # Calcular estatísticas
        stats = self._calculate_stats(offers)

        # Salvar no banco de dados
        self._save_to_database(gpu_name, stats, offers)

        # Detectar mudanças significativas
        self._detect_price_changes(gpu_name, stats)

        # Atualizar cache
        self.last_prices[gpu_name] = stats['avg_price']

        logger.info(f"✓ {gpu_name}: min=${stats['min_price']:.4f}/h, "
                   f"avg=${stats['avg_price']:.4f}/h, "
                   f"max=${stats['max_price']:.4f}/h, "
                   f"ofertas={stats['total_offers']}")

    def _fetch_offers(self, gpu_name: str) -> List[Dict]:
        """
        Busca ofertas para uma GPU específica.

        Args:
            gpu_name: Nome da GPU

        Returns:
            Lista de ofertas
        """
        try:
            # Buscar com limite alto para ter boa amostra
            offers = self.vast_service.search_offers(
                gpu_name=gpu_name,
                limit=100
            )
            return offers
        except Exception as e:
            logger.error(f"Erro ao buscar ofertas para {gpu_name}: {e}")
            return []

    def _calculate_stats(self, offers: List[Dict]) -> Dict:
        """
        Calcula estatísticas de preço das ofertas.

        Args:
            offers: Lista de ofertas

        Returns:
            Dicionário com estatísticas
        """
        prices = [offer['dph_total'] for offer in offers if offer.get('dph_total')]

        if not prices:
            return {
                'min_price': 0,
                'max_price': 0,
                'avg_price': 0,
                'median_price': 0,
                'total_offers': 0,
                'available_gpus': 0,
            }

        # Calcular estatísticas de preço
        min_price = min(prices)
        max_price = max(prices)
        avg_price = statistics.mean(prices)
        median_price = statistics.median(prices)

        # Contar GPUs disponíveis
        total_gpus = sum(offer.get('num_gpus', 1) for offer in offers)

        # Estatísticas por região (opcional)
        region_stats = self._calculate_region_stats(offers)

        return {
            'min_price': min_price,
            'max_price': max_price,
            'avg_price': avg_price,
            'median_price': median_price,
            'total_offers': len(offers),
            'available_gpus': total_gpus,
            'region_stats': json.dumps(region_stats),
        }

    def _calculate_region_stats(self, offers: List[Dict]) -> Dict:
        """
        Calcula estatísticas por região.

        Args:
            offers: Lista de ofertas

        Returns:
            Dicionário com estatísticas por região
        """
        regions = {}

        for offer in offers:
            # Tentar obter região (geolocation ou country)
            region = offer.get('geolocation', offer.get('country', 'unknown'))

            if region not in regions:
                regions[region] = {'prices': [], 'count': 0}

            price = offer.get('dph_total')
            if price:
                regions[region]['prices'].append(price)
                regions[region]['count'] += 1

        # Calcular médias por região
        region_stats = {}
        for region, data in regions.items():
            if data['prices']:
                region_stats[region] = {
                    'avg_price': statistics.mean(data['prices']),
                    'min_price': min(data['prices']),
                    'count': data['count']
                }

        return region_stats

    def _save_to_database(self, gpu_name: str, stats: Dict, offers: List[Dict]):
        """
        Salva estatísticas no banco de dados.

        Args:
            gpu_name: Nome da GPU
            stats: Estatísticas calculadas
            offers: Lista de ofertas originais
        """
        db = SessionLocal()
        try:
            price_record = PriceHistory(
                gpu_name=gpu_name,
                timestamp=datetime.utcnow(),
                min_price=stats['min_price'],
                max_price=stats['max_price'],
                avg_price=stats['avg_price'],
                median_price=stats['median_price'],
                total_offers=stats['total_offers'],
                available_gpus=stats['available_gpus'],
                region_stats=stats.get('region_stats'),
            )

            db.add(price_record)
            db.commit()
            logger.debug(f"Estatísticas salvas no banco para {gpu_name}")

        except Exception as e:
            logger.error(f"Erro ao salvar no banco de dados: {e}")
            db.rollback()
        finally:
            db.close()

    def _detect_price_changes(self, gpu_name: str, stats: Dict):
        """
        Detecta mudanças significativas de preço e cria alertas.

        Args:
            gpu_name: Nome da GPU
            stats: Estatísticas atuais
        """
        if gpu_name not in self.last_prices:
            # Primeira execução, sem histórico para comparar
            return

        last_avg = self.last_prices[gpu_name]
        current_avg = stats['avg_price']

        # Calcular variação percentual
        if last_avg > 0:
            change_percent = ((current_avg - last_avg) / last_avg) * 100
        else:
            change_percent = 0

        # Detectar mudanças significativas (>= 10%)
        if abs(change_percent) >= 10:
            alert_type = 'price_drop' if change_percent < 0 else 'price_spike'
            message = f"{gpu_name}: Preço {'caiu' if change_percent < 0 else 'subiu'} {abs(change_percent):.1f}% (${last_avg:.4f} -> ${current_avg:.4f})"

            logger.warning(f"⚠️ ALERTA: {message}")

            # Salvar alerta no banco
            self._save_alert(
                gpu_name=gpu_name,
                alert_type=alert_type,
                previous_value=last_avg,
                current_value=current_avg,
                change_percent=change_percent,
                message=message
            )

        # Detectar alta disponibilidade (muitas ofertas)
        if stats['total_offers'] >= 50:
            logger.info(f"📈 Alta disponibilidade para {gpu_name}: {stats['total_offers']} ofertas")

    def _save_alert(self, gpu_name: str, alert_type: str, previous_value: float,
                    current_value: float, change_percent: float, message: str):
        """
        Salva um alerta no banco de dados.

        Args:
            gpu_name: Nome da GPU
            alert_type: Tipo de alerta
            previous_value: Valor anterior
            current_value: Valor atual
            change_percent: Variação percentual
            message: Mensagem do alerta
        """
        db = SessionLocal()
        try:
            alert = PriceAlert(
                gpu_name=gpu_name,
                timestamp=datetime.utcnow(),
                alert_type=alert_type,
                previous_value=previous_value,
                current_value=current_value,
                change_percent=change_percent,
                message=message
            )

            db.add(alert)
            db.commit()
            logger.debug(f"Alerta salvo no banco: {message}")

        except Exception as e:
            logger.error(f"Erro ao salvar alerta: {e}")
            db.rollback()
        finally:
            db.close()

    def get_stats(self) -> Dict:
        """Retorna estatísticas do agente."""
        return {
            'name': self.name,
            'running': self.is_running(),
            'interval_minutes': self.interval_seconds / 60,
            'gpus_monitored': self.gpus_to_monitor,
            'last_prices': self.last_prices,
        }
