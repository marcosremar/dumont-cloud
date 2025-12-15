"""
Configuracoes centralizadas do SnapGPU.
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
class AppConfig:
    """Configuracoes gerais da aplicacao"""
    secret_key: str = field(default_factory=lambda: os.getenv("SECRET_KEY", "snapgpu-secret-key-2024"))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    host: str = "0.0.0.0"
    port: int = 8765

    # Path do arquivo de configuracao de usuarios
    config_file: str = "config.json"


@dataclass
class Settings:
    """Container principal de configuracoes"""
    app: AppConfig = field(default_factory=AppConfig)
    r2: R2Config = field(default_factory=R2Config)
    restic: ResticConfig = field(default_factory=ResticConfig)
    vast: VastConfig = field(default_factory=VastConfig)


# Singleton das configuracoes
settings = Settings()
