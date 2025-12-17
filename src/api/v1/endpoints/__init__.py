"""
API endpoints
"""
from . import auth
from . import instances
from . import snapshots
from . import settings
from . import metrics

__all__ = ['auth', 'instances', 'snapshots', 'settings', 'metrics']
