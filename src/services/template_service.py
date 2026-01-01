"""
Template Service with Jinja2 i18n Support

This module provides a Jinja2 Environment configured with the i18n extension
for rendering templates with internationalization support.

Usage:
    from src.services.template_service import get_template_environment, render_template

    # Render template with translations
    html = render_template("marketing_doc.html", locale="es", context={})

    # Get environment for direct use
    env = get_template_environment(locale="en")
    template = env.get_template("finetune_task.yaml.j2")
"""
import gettext
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

# Template directory (relative to this file: src/services -> src/templates)
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"

# Translations directory (CLI translations that are shared with backend)
# Path: cli/translations/
TRANSLATIONS_DIR = Path(__file__).parent.parent.parent / "cli" / "translations"

# Supported locales
SUPPORTED_LOCALES = ["en", "es"]
DEFAULT_LOCALE = "en"


def get_translations(locale: str) -> gettext.GNUTranslations:
    """
    Load gettext translations for the specified locale.

    Args:
        locale: Language code (e.g., 'en', 'es')

    Returns:
        GNUTranslations object or NullTranslations as fallback
    """
    # Normalize locale code
    if "_" in locale:
        locale = locale.split("_")[0]

    # Ensure locale is supported
    if locale not in SUPPORTED_LOCALES:
        logger.warning(f"Unsupported locale '{locale}', falling back to '{DEFAULT_LOCALE}'")
        locale = DEFAULT_LOCALE

    try:
        return gettext.translation(
            "messages",
            localedir=str(TRANSLATIONS_DIR),
            languages=[locale],
            fallback=True
        )
    except Exception as e:
        logger.warning(f"Failed to load translations for locale '{locale}': {e}")
        # Return NullTranslations as fallback
        return gettext.NullTranslations()


def get_template_environment(locale: str = DEFAULT_LOCALE) -> Environment:
    """
    Create a Jinja2 Environment with i18n extension enabled.

    Args:
        locale: Language code for translations (e.g., 'en', 'es')

    Returns:
        Configured Jinja2 Environment with i18n support
    """
    # Create environment with file loader
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "htm", "xml"]),
    )

    # Add i18n extension
    env.add_extension("jinja2.ext.i18n")

    # Load and install translations
    translations = get_translations(locale)
    env.install_gettext_translations(translations)

    logger.debug(f"Created Jinja2 environment with locale '{locale}'")
    return env


def render_template(
    template_name: str,
    context: Optional[Dict[str, Any]] = None,
    locale: str = DEFAULT_LOCALE
) -> str:
    """
    Render a template with i18n support.

    Args:
        template_name: Name of the template file (e.g., "marketing_doc.html")
        context: Dictionary of variables to pass to the template
        locale: Language code for translations (e.g., 'en', 'es')

    Returns:
        Rendered template string
    """
    env = get_template_environment(locale)
    template = env.get_template(template_name)
    return template.render(**(context or {}))


def render_template_string(
    template_string: str,
    context: Optional[Dict[str, Any]] = None,
    locale: str = DEFAULT_LOCALE
) -> str:
    """
    Render a template string with i18n support.

    Args:
        template_string: Jinja2 template as a string
        context: Dictionary of variables to pass to the template
        locale: Language code for translations (e.g., 'en', 'es')

    Returns:
        Rendered string
    """
    env = get_template_environment(locale)
    template = env.from_string(template_string)
    return template.render(**(context or {}))


# Cache for environments by locale (avoids recreating for each request)
_environment_cache: Dict[str, Environment] = {}


def get_cached_environment(locale: str = DEFAULT_LOCALE) -> Environment:
    """
    Get a cached Jinja2 Environment for the specified locale.

    This is more efficient for repeated template rendering with the same locale.

    Args:
        locale: Language code for translations (e.g., 'en', 'es')

    Returns:
        Cached Jinja2 Environment
    """
    # Normalize locale
    if "_" in locale:
        locale = locale.split("_")[0]
    if locale not in SUPPORTED_LOCALES:
        locale = DEFAULT_LOCALE

    if locale not in _environment_cache:
        _environment_cache[locale] = get_template_environment(locale)

    return _environment_cache[locale]


def clear_environment_cache():
    """Clear the environment cache (useful for testing or hot-reloading)."""
    global _environment_cache
    _environment_cache.clear()
    logger.debug("Cleared Jinja2 environment cache")
