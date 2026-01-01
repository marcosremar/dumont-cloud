"""
Shared i18n module for CLI internationalization.

This module provides the _() translation function that can be imported
by all CLI modules. It handles gettext initialization with:
1. Pre-parsing of --language flag from sys.argv
2. LANGUAGE environment variable fallback
3. English default fallback

Usage:
    from ..i18n import _  # or from cli.i18n import _
    print(_("Hello, World!"))
"""
import gettext
import sys
import os
from pathlib import Path

# Get language from environment variable or default to English
# This will be overridden by --language flag if provided
_cli_language = os.getenv('LANGUAGE', 'en').split(':')[0]

# Pre-parse for --language flag to initialize translations before any output
# This allows translated text when user specifies --language
for i, arg in enumerate(sys.argv):
    if arg == '--language' and i + 1 < len(sys.argv):
        _cli_language = sys.argv[i + 1]
        break
    elif arg.startswith('--language='):
        _cli_language = arg.split('=', 1)[1]
        break
    elif arg == '-l' and i + 1 < len(sys.argv):
        _cli_language = sys.argv[i + 1]
        break

# Normalize language code (handle 'es_ES' -> 'es', etc.)
if '_' in _cli_language:
    _cli_language = _cli_language.split('_')[0]

# Initialize gettext translations
_translations_dir = Path(__file__).parent / 'translations'
try:
    _translation = gettext.translation(
        'messages',
        localedir=str(_translations_dir),
        languages=[_cli_language],
        fallback=True
    )
    _ = _translation.gettext
except Exception:
    # Fallback to NullTranslations if translation files not found
    _ = gettext.gettext


def get_current_language() -> str:
    """Return the current CLI language code."""
    return _cli_language
