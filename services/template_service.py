"""
Service para gerenciamento de templates de workloads ML
"""
import json
import os
from typing import Optional, List, Dict, Any
from pathlib import Path

from src.modules.marketplace.models import Template, TemplateCategory


class TemplateService:
    """Service para gerenciar templates de workloads ML"""

    def __init__(self, seed_file: Optional[str] = None):
        """
        Inicializa o TemplateService.

        Args:
            seed_file: Caminho para o arquivo JSON de seed de templates.
                       Se nao especificado, usa o arquivo padrao.
        """
        self._templates: Dict[str, Template] = {}
        self._seed_file = seed_file or self._get_default_seed_file()
        self._load_templates()

    def _get_default_seed_file(self) -> str:
        """Retorna o caminho padrao do arquivo de seed"""
        # Determinar o diretorio base do projeto
        current_dir = Path(__file__).parent.parent
        return str(current_dir / "src" / "modules" / "marketplace" / "templates_seed.json")

    def _load_templates(self) -> None:
        """Carrega templates do arquivo JSON de seed"""
        try:
            with open(self._seed_file, "r", encoding="utf-8") as f:
                templates_data = json.load(f)

            for template_data in templates_data:
                template = Template.from_dict(template_data)
                self._templates[template.slug] = template

        except FileNotFoundError:
            raise RuntimeError(f"Arquivo de templates nao encontrado: {self._seed_file}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Erro ao parsear arquivo de templates: {e}")

    def get_all_templates(self) -> List[Template]:
        """
        Retorna todos os templates ativos.

        Returns:
            Lista de todos os templates ativos
        """
        return [t for t in self._templates.values() if t.is_active]

    def get_template_by_slug(self, slug: str) -> Optional[Template]:
        """
        Busca um template pelo slug.

        Args:
            slug: Slug do template (ex: 'jupyter-lab')

        Returns:
            Template encontrado ou None se nao existir
        """
        return self._templates.get(slug)

    def get_template_by_id(self, template_id: int) -> Optional[Template]:
        """
        Busca um template pelo ID.

        Args:
            template_id: ID do template

        Returns:
            Template encontrado ou None se nao existir
        """
        for template in self._templates.values():
            if template.id == template_id:
                return template
        return None

    def filter_by_vram(self, max_vram: int) -> List[Template]:
        """
        Filtra templates pelo requisito minimo de VRAM.

        Args:
            max_vram: VRAM disponivel (em GB)

        Returns:
            Lista de templates que requerem <= max_vram GB
        """
        return [
            t for t in self._templates.values()
            if t.is_active and t.gpu_min_vram <= max_vram
        ]

    def filter_by_category(self, category: TemplateCategory) -> List[Template]:
        """
        Filtra templates por categoria.

        Args:
            category: Categoria do template

        Returns:
            Lista de templates da categoria especificada
        """
        return [
            t for t in self._templates.values()
            if t.is_active and t.category == category
        ]

    def get_verified_templates(self) -> List[Template]:
        """
        Retorna apenas templates verificados.

        Returns:
            Lista de templates verificados
        """
        return [
            t for t in self._templates.values()
            if t.is_active and t.is_verified
        ]

    def get_templates_as_dict(self) -> List[Dict[str, Any]]:
        """
        Retorna todos os templates ativos como dicionarios.

        Returns:
            Lista de templates serializados como dicionarios
        """
        return [t.to_dict() for t in self.get_all_templates()]

    def reload_templates(self) -> None:
        """Recarrega templates do arquivo de seed"""
        self._templates.clear()
        self._load_templates()

    def get_template_count(self) -> int:
        """
        Retorna o numero de templates ativos.

        Returns:
            Numero de templates ativos
        """
        return len(self.get_all_templates())
