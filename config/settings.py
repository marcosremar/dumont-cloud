"""
Configuracoes centralizadas do Dumont Cloud.
Carrega variaveis de ambiente e define defaults.
"""
import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class R2Config:
    """Configuracoes do Cloudflare R2"""
    access_key: str = field(default_factory=lambda: os.getenv("R2_ACCESS_KEY", ""))
    secret_key: str = field(default_factory=lambda: os.getenv("R2_SECRET_KEY", ""))
    endpoint: str = field(default_factory=lambda: os.getenv("R2_ENDPOINT", ""))
    bucket: str = field(default_factory=lambda: os.getenv("R2_BUCKET", "musetalk"))

    @property
    def restic_repo(self) -> str:
        return f"s3:{self.endpoint}/{self.bucket}/restic"


@dataclass
class ResticConfig:
    """Configuracoes do Restic"""
    password: str = field(default_factory=lambda: os.getenv("RESTIC_PASSWORD", ""))
    connections: int = 32


@dataclass
class VastConfig:
    """Configuracoes da API vast.ai"""
    api_url: str = "https://console.vast.ai/api/v0"

    # Timeouts
    stage_timeout: int = 30  # Timeout por etapa de inicializacao
    ssh_ready_timeout: int = 60  # Timeout para SSH ficar pronto

    # Defaults para filtros
    default_region: str = "EU"
    min_reliability: float = 0.95
    min_cuda: str = "12.0"


@dataclass
class DumontAgentConfig:
    """Configuracoes do DumontAgent (agente nas maquinas GPU)"""
    server_url: str = field(default_factory=lambda: os.getenv("DUMONT_SERVER", "https://dumontcloud.com"))
    sync_interval: int = 30  # segundos entre sincronizacoes
    sync_dirs: str = "/workspace"
    keep_last: int = 10  # quantidade de snapshots a manter


@dataclass
class SnapshotConfig:
    """Configuracoes do agendador de snapshots periodicos"""
    default_interval_minutes: int = field(
        default_factory=lambda: int(os.getenv("SNAPSHOT_DEFAULT_INTERVAL_MINUTES", "15"))
    )
    enabled: bool = field(
        default_factory=lambda: os.getenv("SNAPSHOT_ENABLED", "true").lower() == "true"
    )
    max_concurrent: int = field(
        default_factory=lambda: int(os.getenv("SNAPSHOT_MAX_CONCURRENT", "1"))
    )


@dataclass
class AppConfig:
    """Configuracoes gerais da aplicacao"""
    secret_key: str = field(default_factory=lambda: os.getenv("SECRET_KEY", "dumont-cloud-secret-key-2024"))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    host: str = "0.0.0.0"
    port: int = 8766  # Nginx frontend on 8765, Flask backend on 8766

    # Path do arquivo de configuracao de usuarios
    config_file: str = "config.json"


@dataclass
class Settings:
    """Container principal de configuracoes"""
    app: AppConfig = field(default_factory=AppConfig)
    r2: R2Config = field(default_factory=R2Config)
    restic: ResticConfig = field(default_factory=ResticConfig)
    vast: VastConfig = field(default_factory=VastConfig)
    agent: DumontAgentConfig = field(default_factory=DumontAgentConfig)
    snapshot: SnapshotConfig = field(default_factory=SnapshotConfig)


# Singleton das configuracoes
settings = Settings()
