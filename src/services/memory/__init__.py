# Memory service for AI agents
from .base import MemoryProvider, MemoryConfig, Memory, MemoryType
from .manager import MemoryManager

# Import providers to register them
from . import mock_provider  # Always available for testing

# Try to import GCP provider (may fail if dependencies missing)
try:
    from . import gcp_provider
except ImportError:
    pass  # GCP dependencies not installed

__all__ = ['MemoryProvider', 'MemoryConfig', 'Memory', 'MemoryType', 'MemoryManager']
