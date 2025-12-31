"""
Servico para geracao de imagens de relatorios compartilhaveis.
Utiliza Puppeteer (Node.js) via subprocess para captura de screenshots.
"""

import os
import subprocess
import tempfile
import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime


class ReportFormat(Enum):
    """Formatos suportados para imagens de relatorios."""
    TWITTER = "twitter"      # 1200x675px
    LINKEDIN = "linkedin"    # 1200x627px
    GENERIC = "generic"      # 1200x630px


@dataclass
class FormatDimensions:
    """Dimensoes de viewport para cada formato."""
    width: int
    height: int


# Mapeamento de formato para dimensoes
FORMAT_DIMENSIONS: Dict[ReportFormat, FormatDimensions] = {
    ReportFormat.TWITTER: FormatDimensions(width=1200, height=675),
    ReportFormat.LINKEDIN: FormatDimensions(width=1200, height=627),
    ReportFormat.GENERIC: FormatDimensions(width=1200, height=630),
}


# Chrome args para compatibilidade com Docker/ambientes headless
# Seguindo padrao de capture-interfaces.js
PUPPETEER_CHROME_ARGS = [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-dev-shm-usage',
]


@dataclass
class GenerationResult:
    """Resultado da geracao de imagem."""
    success: bool
    image_path: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None


class ReportGenerationService:
    """
    Servico para geracao de imagens de relatorios de economia.

    Utiliza Puppeteer via subprocess para capturar screenshots
    de paginas de relatorio renderizadas.
    """

    def __init__(
        self,
        storage_path: Optional[str] = None,
        node_script_path: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        """
        Inicializa o servico de geracao de relatorios.

        Args:
            storage_path: Diretorio para armazenar imagens geradas.
                         Default: ./uploads/reports/
            node_script_path: Caminho para o script Node.js de geracao.
                             Default: ./scripts/generate-report-image.js
            base_url: URL base para renderizar relatorios.
                     Default: http://localhost:8000
        """
        self.storage_path = Path(storage_path or os.getenv(
            'REPORT_IMAGE_STORAGE_PATH',
            './uploads/reports/'
        ))
        self.node_script_path = Path(node_script_path or os.getenv(
            'REPORT_GENERATION_SCRIPT',
            './scripts/generate-report-image.js'
        ))
        self.base_url = base_url or os.getenv(
            'PUBLIC_URL',
            'http://localhost:8000'
        )

        # Garantir que diretorio de storage existe
        self._ensure_storage_directory()

    def _ensure_storage_directory(self) -> None:
        """Cria diretorio de storage se nao existir."""
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def get_format_dimensions(self, format_type: ReportFormat) -> FormatDimensions:
        """
        Retorna dimensoes para um formato especifico.

        Args:
            format_type: Tipo de formato (twitter, linkedin, generic)

        Returns:
            FormatDimensions com width e height
        """
        return FORMAT_DIMENSIONS.get(format_type, FORMAT_DIMENSIONS[ReportFormat.GENERIC])

    def get_report_url(self, shareable_id: str) -> str:
        """
        Gera URL completa para um relatorio compartilhavel.

        Args:
            shareable_id: ID unico do relatorio

        Returns:
            URL completa para o relatorio
        """
        return f"{self.base_url}/reports/{shareable_id}"

    def get_image_filename(self, shareable_id: str, format_type: ReportFormat) -> str:
        """
        Gera nome de arquivo para imagem do relatorio.

        Args:
            shareable_id: ID unico do relatorio
            format_type: Tipo de formato

        Returns:
            Nome do arquivo PNG
        """
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        return f"{shareable_id}_{format_type.value}_{timestamp}.png"

    def get_image_path(self, shareable_id: str, format_type: ReportFormat) -> Path:
        """
        Retorna caminho completo para salvar imagem.

        Args:
            shareable_id: ID unico do relatorio
            format_type: Tipo de formato

        Returns:
            Path completo para o arquivo
        """
        filename = self.get_image_filename(shareable_id, format_type)
        return self.storage_path / filename

    def generate_image(
        self,
        shareable_id: str,
        format_type: ReportFormat = ReportFormat.GENERIC,
        timeout_seconds: int = 30
    ) -> GenerationResult:
        """
        Gera imagem do relatorio usando Puppeteer.

        Chama script Node.js via subprocess para capturar screenshot
        da pagina de relatorio renderizada.

        Args:
            shareable_id: ID unico do relatorio
            format_type: Formato da imagem (twitter/linkedin/generic)
            timeout_seconds: Timeout maximo para geracao

        Returns:
            GenerationResult com status e caminho da imagem
        """
        start_time = datetime.utcnow()

        # Verificar se script existe
        if not self.node_script_path.exists():
            return GenerationResult(
                success=False,
                error_message=f"Script not found: {self.node_script_path}"
            )

        # Obter dimensoes e paths
        dimensions = self.get_format_dimensions(format_type)
        report_url = self.get_report_url(shareable_id)
        output_path = self.get_image_path(shareable_id, format_type)

        try:
            # Executar script Node.js com Puppeteer
            result = subprocess.run(
                [
                    'node',
                    str(self.node_script_path),
                    f'--url={report_url}',
                    f'--format={format_type.value}',
                    f'--width={dimensions.width}',
                    f'--height={dimensions.height}',
                    f'--output={output_path}',
                ],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                cwd=str(self.node_script_path.parent.parent)  # Root do projeto
            )

            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            if result.returncode != 0:
                return GenerationResult(
                    success=False,
                    error_message=f"Script error: {result.stderr or result.stdout}",
                    duration_ms=duration
                )

            # Verificar se arquivo foi criado
            if not output_path.exists():
                return GenerationResult(
                    success=False,
                    error_message="Image file not created",
                    duration_ms=duration
                )

            return GenerationResult(
                success=True,
                image_path=str(output_path),
                duration_ms=duration
            )

        except subprocess.TimeoutExpired:
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            return GenerationResult(
                success=False,
                error_message=f"Generation timeout after {timeout_seconds}s",
                duration_ms=duration
            )
        except FileNotFoundError:
            return GenerationResult(
                success=False,
                error_message="Node.js not found. Please install Node.js."
            )
        except Exception as e:
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            return GenerationResult(
                success=False,
                error_message=f"Unexpected error: {str(e)}",
                duration_ms=duration
            )

    def generate_all_formats(
        self,
        shareable_id: str,
        timeout_seconds: int = 30
    ) -> Dict[ReportFormat, GenerationResult]:
        """
        Gera imagens em todos os formatos suportados.

        Args:
            shareable_id: ID unico do relatorio
            timeout_seconds: Timeout por imagem

        Returns:
            Dict mapeando formato para resultado
        """
        results = {}
        for format_type in ReportFormat:
            results[format_type] = self.generate_image(
                shareable_id,
                format_type,
                timeout_seconds
            )
        return results

    def get_image_url(self, image_path: str) -> str:
        """
        Converte caminho local para URL publica.

        Args:
            image_path: Caminho local do arquivo

        Returns:
            URL publica para a imagem
        """
        # Extrair apenas o nome do arquivo
        filename = Path(image_path).name
        return f"{self.base_url}/uploads/reports/{filename}"

    def cleanup_old_images(self, max_age_days: int = 30) -> int:
        """
        Remove imagens mais antigas que max_age_days.

        Args:
            max_age_days: Idade maxima em dias

        Returns:
            Numero de arquivos removidos
        """
        if not self.storage_path.exists():
            return 0

        removed = 0
        cutoff = datetime.utcnow().timestamp() - (max_age_days * 24 * 60 * 60)

        for file_path in self.storage_path.glob('*.png'):
            if file_path.stat().st_mtime < cutoff:
                try:
                    file_path.unlink()
                    removed += 1
                except OSError:
                    pass

        return removed


def generate_shareable_id(length: int = 10) -> str:
    """
    Gera um ID unico, URL-safe para relatorios compartilhaveis.

    Utiliza secrets.token_urlsafe para gerar IDs seguros,
    nao-sequenciais e nao-adivinhaveis.

    Args:
        length: Comprimento desejado do ID (10-12 recomendado)

    Returns:
        String URL-safe de tamanho especificado
    """
    import secrets
    # token_urlsafe retorna ~1.3x o numero de bytes, entao ajustamos
    return secrets.token_urlsafe(length)[:length]
