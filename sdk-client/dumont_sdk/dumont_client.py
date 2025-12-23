"""
Cliente principal do Dumont SDK.

Une todos os módulos em uma interface unificada.
"""
import logging
from typing import Optional, Dict, Any

from .base import BaseClient
from .instances import InstancesClient
from .snapshots import SnapshotsClient
from .wizard import WizardClient
from .models import ModelsClient
from .standby import StandbyClient
from .failover import FailoverClient
from .metrics import MetricsClient
from .settings import SettingsClient
from .client import DumontLLM
from .config import DumontConfig, GPUConfig, FallbackModel

logger = logging.getLogger(__name__)


class DumontClient(BaseClient):
    """
    Cliente principal do Dumont Cloud SDK.

    Une todos os módulos:
    - instances: Gerenciamento de instâncias GPU
    - snapshots: Backup e restore
    - wizard: Deploy multi-start
    - models: Instalação de modelos LLM
    - standby: CPU Standby e failover
    - failover: Failover Orchestrator
    - metrics: Market Metrics e analytics
    - settings: Configurações e balance
    - llm: Inferência com failover automático

    Exemplo:
        async with DumontClient(api_key="dumont_sk_...") as client:
            # Listar instâncias
            instances = await client.instances.list()

            # Deploy rápido
            result = await client.wizard.deploy(gpu_name="RTX 4090")

            # Instalar modelo
            await client.models.install(result.instance_id, "llama3.2")

            # Inferência com failover
            response = await client.llm.complete("Olá!")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.dumontcloud.com",
        timeout: float = 30.0,
        openrouter_api_key: Optional[str] = None,
        auto_fetch_config: bool = True,
    ):
        """
        Inicializa o cliente Dumont.

        Args:
            api_key: API key do Dumont Cloud (formato: dumont_sk_...)
            base_url: URL base da API
            timeout: Timeout padrão para requests
            openrouter_api_key: API key do OpenRouter (para LLM failover) - se não fornecido, busca do servidor
            auto_fetch_config: Se True, busca config do servidor automaticamente
        """
        super().__init__(base_url=base_url, api_key=api_key, timeout=timeout)

        # Inicializa módulos
        self._instances = InstancesClient(self)
        self._snapshots = SnapshotsClient(self)
        self._wizard = WizardClient(self)
        self._models = ModelsClient(self)
        self._standby = StandbyClient(self)
        self._failover = FailoverClient(self)
        self._metrics = MetricsClient(self)
        self._settings = SettingsClient(self)

        # LLM client com failover
        self._llm: Optional[DumontLLM] = None
        self._openrouter_api_key = openrouter_api_key

        # Server config
        self._server_config: Optional[Dict[str, Any]] = None
        self._auto_fetch_config = auto_fetch_config
        self._config_fetched = False

    @property
    def instances(self) -> InstancesClient:
        """Módulo de gerenciamento de instâncias."""
        return self._instances

    @property
    def snapshots(self) -> SnapshotsClient:
        """Módulo de snapshots."""
        return self._snapshots

    @property
    def wizard(self) -> WizardClient:
        """Módulo de wizard deploy."""
        return self._wizard

    @property
    def models(self) -> ModelsClient:
        """Módulo de gerenciamento de modelos."""
        return self._models

    @property
    def standby(self) -> StandbyClient:
        """Módulo de CPU Standby e failover."""
        return self._standby

    @property
    def failover(self) -> FailoverClient:
        """Módulo de Failover Orchestrator."""
        return self._failover

    @property
    def metrics(self) -> MetricsClient:
        """Módulo de Market Metrics."""
        return self._metrics

    @property
    def settings(self) -> SettingsClient:
        """Módulo de Settings e configurações."""
        return self._settings

    @property
    def llm(self) -> DumontLLM:
        """
        Cliente LLM com failover automático.

        Tenta GPU primeiro, depois OpenRouter.

        Nota: Use await client.ensure_config() antes para garantir
        que a config do servidor foi carregada (incluindo OpenRouter key).
        """
        if self._llm is None:
            # Use OpenRouter key from server config if not provided locally
            openrouter_key = self._openrouter_api_key
            if not openrouter_key and self._server_config:
                openrouter_key = self._server_config.get("openrouter_api_key", "")

            config = DumontConfig(
                dumont_server=self.base_url,
                api_key=self.api_key or "",
                openrouter_api_key=openrouter_key or "",
            )
            self._llm = DumontLLM(config=config)
        return self._llm

    async def fetch_sdk_config(self, force: bool = False) -> Dict[str, Any]:
        """
        Busca configuração do servidor Dumont.

        Retorna configurações incluindo:
        - openrouter_api_key: API key do OpenRouter (para LLM failover)
        - vast_api_key: API key do Vast.ai
        - base_url: URL base da API
        - features: Features habilitadas

        Args:
            force: Se True, ignora cache e busca novamente

        Returns:
            Configuração do servidor
        """
        if not force and self._server_config:
            return self._server_config

        if not self.api_key:
            logger.warning("API key não configurada, não é possível buscar config do servidor")
            return {}

        try:
            response = await self.get("/api/v1/auth/sdk/config")
            self._server_config = response
            self._config_fetched = True

            # Update OpenRouter key if provided by server and not set locally
            if not self._openrouter_api_key:
                self._openrouter_api_key = response.get("openrouter_api_key")

            logger.info("SDK config carregada do servidor")
            return response

        except Exception as e:
            logger.warning(f"Falha ao buscar config do servidor: {e}")
            return {}

    async def ensure_config(self):
        """
        Garante que a config do servidor foi carregada.

        Chame este método antes de usar features que dependem
        de configurações do servidor (como LLM com OpenRouter).
        """
        if not self._config_fetched and self._auto_fetch_config:
            await self.fetch_sdk_config()

    @property
    def server_config(self) -> Optional[Dict[str, Any]]:
        """Retorna a config do servidor (se já carregada)."""
        return self._server_config

    async def __aenter__(self):
        """Inicializa o cliente e busca config do servidor."""
        if self._auto_fetch_config and self.api_key:
            await self.fetch_sdk_config()
        return self

    async def close(self):
        """Fecha todos os clientes."""
        await super().close()
        if self._llm:
            await self._llm.close()

    # =========================================================================
    # Convenience methods
    # =========================================================================

    async def quick_deploy(
        self,
        gpu_name: Optional[str] = None,
        max_price: float = 1.0,
        install_model: Optional[str] = None,
    ):
        """
        Deploy rápido com configuração mínima.

        Args:
            gpu_name: Modelo da GPU (opcional)
            max_price: Preço máximo por hora
            install_model: Modelo para instalar (opcional)

        Returns:
            Resultado do deploy com instância pronta
        """
        # Deploy
        result = await self.wizard.quick_deploy(
            gpu_name=gpu_name,
            max_price=max_price,
        )

        if not result.success:
            return result

        # Instalar modelo se especificado
        if install_model and result.instance_id:
            logger.info(f"Instalando modelo {install_model}...")
            model_result = await self.models.install(
                instance_id=result.instance_id,
                model=install_model,
            )
            if model_result.success:
                logger.info(f"Modelo instalado: {model_result.ollama_url}")

        return result

    async def get_status(self):
        """
        Obtém status geral da conta.

        Returns:
            Resumo de instâncias, uso, etc.
        """
        instances = await self.instances.list()

        running = [i for i in instances if i.is_running]
        stopped = [i for i in instances if not i.is_running]

        total_cost_per_hour = sum(i.dph_total for i in running)

        return {
            "total_instances": len(instances),
            "running": len(running),
            "stopped": len(stopped),
            "total_cost_per_hour": round(total_cost_per_hour, 4),
            "instances": [
                {
                    "id": i.id,
                    "gpu": i.gpu_name,
                    "status": i.status,
                    "price": i.dph_total,
                }
                for i in instances
            ],
        }


# Alias para compatibilidade
Dumont = DumontClient
